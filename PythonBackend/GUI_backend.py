from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import cv2
import time
from porthandler import barcode_scanner_listener
import globals
from pypylon import pylon
from cameracontrol import (apply_camera_settings, 
                           validate_and_set_camera_param, get_camera_properties)
import porthandler
import os
import sys
import pyodbc
import csv
from datetime import datetime
import subprocess
import json


from image_processing import imageprocessing_main

import threading
from settings_manager import load_settings, save_settings, get_settings
import numpy as np
from statistics_processor import calculate_statistics, save_annotated_image, save_dot_results_to_csv

from logger_config import setup_logger, CameraError, SerialError  # Import custom exceptions if defined in logger_config.py
setup_logger()  # This sets up the root logger with our desired configuration.
from error_codes import ErrorCode, ERROR_MESSAGES
import tkinter as tk
from tkinter import filedialog
from multiprocessing import Process, Queue
import multiprocessing

app = Flask(__name__)
app.secret_key = 'Zoltek'
CORS(app)
app.debug = True


# Might need to be removed
camera_properties = {'main': None, 'side': None}

MAIN_CAMERA_ID = '40569959'
SIDE_CAMERA_ID = '40569958'

CAMERA_IDS = {
    'main': MAIN_CAMERA_ID,
    'side': SIDE_CAMERA_ID
}

latest_frames = {
    'main': None,
    'side': None
}

backend_ready = False

if not hasattr(globals, 'measurement_data'):
    globals.measurement_data = []  # This will store all the dot_contours arrays.
if not hasattr(globals, 'result_counts'):
    globals.result_counts = [0, 0, 0]  # One counter per result class.

### Error handling and logging ###
@app.errorhandler(Exception)
def handle_global_exception(error):
    error_message = str(error)
    app.logger.exception(f"Unhandled exception: {error_message}")
    
    return jsonify({
        "error": "An unexpected error occurred.",
        "details": error_message,
        "popup": True
    }), 500

def retry_operation(operation, max_retries=3, wait=1, exceptions=(Exception,)):
    """
    Attempts to run 'operation' up to 'max_retries' times.
    Waits 'wait' seconds between attempts.
    Raises an exception after all attempts fail.
    """
    for attempt in range(max_retries):
        try:
            return operation()
        except exceptions as e:
            app.logger.warning("Attempt %d/%d failed: %s", attempt + 1, max_retries, e)
            time.sleep(wait)
    raise Exception("Operation failed after %d attempts" % max_retries)


### Serial Device Functions ###
# Connect/Disconnect Serial devices
@app.route('/api/connect-to-turntable', methods=['POST'])
def connect_turntable():
    try:
        app.logger.info("Attempting to connect to Turntable")
        if porthandler.turntable and porthandler.turntable.is_open:
            app.logger.info("Turntable already connected.")
            return jsonify({'message': 'Turntable already connected'}), 200

        device = porthandler.connect_to_turntable()
        if device:
            porthandler.turntable = device
            app.logger.info("Successfully connected to Turntable")
            return jsonify({'message': 'Turntable connected', 'port': device.port}), 200
        else:
            app.logger.error("Failed to connect to Turntable: No response or incorrect ID")
            return jsonify({
                'error': ERROR_MESSAGES[ErrorCode.TURNTABLE_DISCONNECTED],
                'code': ErrorCode.TURNTABLE_DISCONNECTED,
                'popup': True
            }), 404
    except Exception as e:
        app.logger.exception("Exception occurred while connecting to Turntable")
        return jsonify({
            'error': ERROR_MESSAGES[ErrorCode.TURNTABLE_DISCONNECTED],
            'code': ErrorCode.TURNTABLE_DISCONNECTED,
            'popup': True
        }), 500

@app.route('/api/connect-to-barcode', methods=['POST'])
def connect_barcode_scanner():
    try:
        app.logger.info("Attempting to connect to Barcode Scanner")
        # Always attempt a fresh connection.
        device = porthandler.connect_to_barcode_scanner()
        if device:
            app.logger.info("Successfully connected to Barcode Scanner")
            return jsonify({'message': 'Barcode Scanner connected', 'port': device.port}), 200
        else:
            app.logger.error("Failed to connect Barcode Scanner: Device not found")
            return jsonify({
                'error': ERROR_MESSAGES[ErrorCode.BARCODE_DISCONNECTED],
                'code': ErrorCode.BARCODE_DISCONNECTED,
                'popup': True
            }), 404
    except Exception as e:
        app.logger.exception("Exception occurred while connecting to Barcode Scanner")
        return jsonify({
            'error': ERROR_MESSAGES[ErrorCode.BARCODE_DISCONNECTED],
            'code': ErrorCode.BARCODE_DISCONNECTED,
            'popup': True
        }), 500

@app.route('/api/disconnect-<device_name>', methods=['POST'])
def disconnect_serial_device(device_name):
    try:
        app.logger.info(f"Attempting to disconnect from {device_name}")
        porthandler.disconnect_serial_device(device_name)
        app.logger.info(f"Successfully disconnected from {device_name}")
        return jsonify('ok')
    except Exception as e:
        app.logger.exception(f"Exception occurred while disconnecting from {device_name}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/status/serial/<device_name>', methods=['GET'])
def get_serial_device_status(device_name):
    app.logger.debug(f"Received status request for device: {device_name}")
    device = None
    if device_name.lower() == 'turntable':
        device = porthandler.turntable
    elif device_name.lower() in ['barcode', 'barcodescanner']:
        device = porthandler.barcode_scanner
    else:
        app.logger.error("Invalid device name")
        return jsonify({'error': 'Invalid device name', 'popup': True}), 400

    if device and device.is_open:
        if device_name.lower() == 'turntable':
            if not porthandler.turntable_waiting_for_done:
                try:
                    device.write(b'IDN?\n')
                    response = device.read(10).decode(errors='ignore').strip()
                    if response:
                        app.logger.debug(f"{device_name} is responsive on port {device.port}")
                        return jsonify({'connected': True, 'port': device.port})
                except Exception as e:
                    app.logger.warning(f"{device_name} is unresponsive, disconnecting. Error: {str(e)}")
                    porthandler.disconnect_serial_device(device_name)
                    return jsonify({
                        'connected': False,
                        'error': f"{device_name.capitalize()} unresponsive",
                        'code': ErrorCode.TURNTABLE_DISCONNECTED,
                        'popup': True
                    }), 400
        elif device_name.lower() in ['barcode', 'barcodescanner']:
            from serial.tools import list_ports
            available_ports = [port.device for port in list_ports.comports()]
            if device.port in available_ports:
                app.logger.debug(f"{device_name} is connected on port {device.port}")
                return jsonify({'connected': True, 'port': device.port})
            else:
                app.logger.warning(f"{device_name} appears to be disconnected (port not found).")
                return jsonify({
                    'connected': False,
                    'error': "Barcode Scanner disconnected",
                    'code': ErrorCode.BARCODE_DISCONNECTED,
                    'popup': True
                }), 400

        app.logger.debug(f"{device_name} is connected on port {device.port}")
        return jsonify({'connected': True, 'port': device.port})

    app.logger.warning(f"{device_name} appears to be disconnected.")
    # For turntable, return error with code.
    if device_name.lower() == 'turntable':
        return jsonify({
            'connected': False,
            'error': f"{device_name.capitalize()} appears to be disconnected",
            'code': ErrorCode.TURNTABLE_DISCONNECTED,
            'popup': True
        }), 400
    else:
        return jsonify({
            'connected': False,
            'error': f"{device_name.capitalize()} appears to be disconnected",
            'code': ErrorCode.BARCODE_DISCONNECTED,
            'popup': True
        }), 400


# Turntable Functions
@app.route('/api/home_turntable_with_image', methods=['POST'])
def home_turntable():
    try:
        app.logger.info("Homing process initiated.")

        # Step 1: Grab the image quickly and release the camera
        with globals.grab_locks['main']:
            camera = globals.cameras.get('main')
            if camera is None or not camera.IsOpen():
                app.logger.error("Camera not connected or not open during homing.")
                return jsonify({
                    'error': ERROR_MESSAGES[ErrorCode.MAIN_CAMERA_DISCONNECTED],
                    'code': ErrorCode.MAIN_CAMERA_DISCONNECTED,
                    "popup": True
                }), 500

            try:
                grab_result = retry_operation(
                    lambda: attempt_frame_grab(camera, 'main'),
                    max_retries=10,
                    wait=1
                )
            except Exception as grab_err:
                app.logger.exception("Exception during image grab: " + str(grab_err))
                return jsonify({
                    'error': ERROR_MESSAGES[ErrorCode.MAIN_CAMERA_DISCONNECTED],
                    'code': ErrorCode.MAIN_CAMERA_DISCONNECTED,
                    "popup": True
                }), 500

            if grab_result is None:
                app.logger.error("Grab result is None during homing.")
                return jsonify({
                    'error': ERROR_MESSAGES[ErrorCode.MAIN_CAMERA_DISCONNECTED],
                    'code': ErrorCode.MAIN_CAMERA_DISCONNECTED,
                    "popup": True
                }), 500

            try:
                if not grab_result.GrabSucceeded():
                    app.logger.error("Grab result was unsuccessful during homing.")
                    return jsonify({
                        'error': ERROR_MESSAGES[ErrorCode.MAIN_CAMERA_DISCONNECTED],
                        'code': ErrorCode.MAIN_CAMERA_DISCONNECTED,
                        "popup": True
                    }), 500
            except Exception as e:
                app.logger.exception("Exception while checking GrabSucceeded: " + str(e))
                return jsonify({
                    'error': ERROR_MESSAGES[ErrorCode.MAIN_CAMERA_DISCONNECTED],
                    'code': ErrorCode.MAIN_CAMERA_DISCONNECTED,
                    "popup": True
                }), 500

            app.logger.info("Image grabbed successfully.")
            image = grab_result.Array
            grab_result.Release()

        # Step 2: Process the image and calculate rotation
        rotation_needed, error_msg = imageprocessing_main.home_turntable_with_image(image)
        if rotation_needed is None:
            app.logger.error(f"Image processing failed in home_turntable_with_image: {error_msg}")
            return jsonify({
                'error': "image_analysis_error",
                'code': error_msg,
                'popup': True
            }), 500

        command = f"{abs(rotation_needed)},{1 if rotation_needed > 0 else 0}"
        app.logger.info(f"Image processing complete. Rotation needed: {rotation_needed}")

        # Step 3: Send rotation command & retry confirmation
        try:
            movement_success = retry_operation(
                lambda: porthandler.write_turntable(command),
                max_retries=3,
                wait=2
            )
        except Exception as move_err:
            app.logger.exception("Exception while sending rotation command: " + str(move_err))
            return jsonify({
                'error': ERROR_MESSAGES[ErrorCode.TURNTABLE_DISCONNECTED],
                'code': ErrorCode.TURNTABLE_DISCONNECTED,
                'popup': True
            }), 500

        if not movement_success:
            app.logger.error("Rotation command not confirmed after retries.")
            return jsonify({
                'error': ERROR_MESSAGES[ErrorCode.TURNTABLE_DISCONNECTED],
                'code': ErrorCode.TURNTABLE_DISCONNECTED,
                'popup': True
            }), 500

        app.logger.info("Rotation completed successfully.")
        
        time.sleep(0.5)
        
        # Step 4: Grab side image quickly and release the camera
        with globals.grab_locks['side']:
            camera = globals.cameras.get('side')
            if camera is None or not camera.IsOpen():
                app.logger.error("Camera not connected or not open during homing.")
                return jsonify({
                    'error': ERROR_MESSAGES[ErrorCode.SIDE_CAMERA_DISCONNECTED],
                    'code': ErrorCode.SIDE_CAMERA_DISCONNECTED,
                    "popup": True
                }), 500

            try:
                grab_result = retry_operation(
                    lambda: attempt_frame_grab(camera, 'side'),
                    max_retries=10,
                    wait=1
                )
            except Exception as grab_err:
                app.logger.exception("Exception during image grab: " + str(grab_err))
                return jsonify({
                    'error': ERROR_MESSAGES[ErrorCode.SIDE_CAMERA_DISCONNECTED],
                    'code': ErrorCode.SIDE_CAMERA_DISCONNECTED,
                    "popup": True
                }), 500

            if grab_result is None:
                app.logger.error("Grab result is None during homing.")
                return jsonify({
                    'error': ERROR_MESSAGES[ErrorCode.SIDE_CAMERA_DISCONNECTED],
                    'code': ErrorCode.SIDE_CAMERA_DISCONNECTED,
                    "popup": True
                }), 500

            try:
                if not grab_result.GrabSucceeded():
                    app.logger.error("Grab result was unsuccessful during homing.")
                    return jsonify({
                        'error': ERROR_MESSAGES[ErrorCode.SIDE_CAMERA_DISCONNECTED],
                        'code': ErrorCode.SIDE_CAMERA_DISCONNECTED,
                        "popup": True
                    }), 500
            except Exception as e:
                app.logger.exception("Exception while checking GrabSucceeded: " + str(e))
                return jsonify({
                    'error': ERROR_MESSAGES[ErrorCode.SIDE_CAMERA_DISCONNECTED],
                    'code': ErrorCode.SIDE_CAMERA_DISCONNECTED,
                    "popup": True
                }), 500

            app.logger.info("Image grabbed successfully.")
            image = grab_result.Array
            grab_result.Release()

        # Step 5: Process the image and calculate rotation
        rotation_needed, error_msg = imageprocessing_main.home_check(image)
        if rotation_needed is None:
            app.logger.error(f"Image processing failed in home_turntable_with_image: {error_msg}")
            return jsonify({
                'error': "image_analysis_error",
                'code': error_msg,
                'popup': True
            }), 500

        command = f"{abs(rotation_needed)},{1 if rotation_needed > 0 else 0}"
        app.logger.info(f"Image processing complete. Rotation needed: {rotation_needed}")

        # Step 6: Send rotation command & retry confirmation
        try:
            movement_success = retry_operation(
                lambda: porthandler.write_turntable(command),
                max_retries=3,
                wait=2
            )
        except Exception as move_err:
            app.logger.exception("Exception while sending rotation command: " + str(move_err))
            return jsonify({
                'error': ERROR_MESSAGES[ErrorCode.TURNTABLE_DISCONNECTED],
                'code': ErrorCode.TURNTABLE_DISCONNECTED,
                'popup': True
            }), 500

        if not movement_success:
            app.logger.error("Rotation command not confirmed after retries.")
            return jsonify({
                'error': ERROR_MESSAGES[ErrorCode.TURNTABLE_DISCONNECTED],
                'code': ErrorCode.TURNTABLE_DISCONNECTED,
                'popup': True
            }), 500

        app.logger.info("Rotation completed successfully.")


        # Step 7: Update global position after homing
        globals.turntable_position = 0
        globals.turntable_homed = True
        app.logger.info("Homing completed successfully. Position set to 0.")

        # Step 8: Return success response
        return jsonify({
            "message": "Homing successful",
            "rotation": rotation_needed,
            "current_position": globals.turntable_position
        }), 200

    except Exception as e:
        # Mark the camera as disconnected on any unhandled exception.
        globals.cameras['main'] = None
        globals.stream_running['main'] = False
        app.logger.exception(f"Error during homing: {e}")
        return jsonify({"error": str(e), "popup": True}), 500


@app.route('/api/move_turntable_relative', methods=['POST'])
def move_turntable_relative():
    try:
        data = request.get_json()
        move_by = data.get('degrees')

        # (Inputs are assumed valid on the frontend.)

        direction = 'CW' if move_by > 0 else 'CCW'
        command = f"{abs(move_by)},{1 if move_by > 0 else 0}"
        app.logger.info(f"Sending command to turntable: {command}")

        # Send the command to the turntable.
        try:
            porthandler.write_turntable(command, expect_response=False)
        except Exception as write_err:
            app.logger.exception("Failed to write turntable command: " + str(write_err))
            return jsonify({
                'error': "Turntable disconnected",
                'code': ErrorCode.TURNTABLE_DISCONNECTED,
                'popup': True
            }), 500

        # Update position only if the turntable is homed.
        if globals.turntable_homed:
            app.logger.info(f"Updating position (before): {globals.turntable_position}")
            globals.turntable_position = (globals.turntable_position - move_by) % 360
            app.logger.info(f"Updated position (after): {globals.turntable_position}")
        else:
            app.logger.info("Turntable is not homed. Position remains '?'.")

        return jsonify({
            'message': f'Turntable moved {move_by} degrees {direction}',
            'current_position': globals.turntable_position if globals.turntable_homed else '?'
        }), 200
    except Exception as e:
        app.logger.exception(f"Error in move_turntable_relative: {e}")
        # Include extra details (you may want to include these only in development)
        return jsonify({
            'error': ERROR_MESSAGES[ErrorCode.TURNTABLE_DISCONNECTED],
            'code': ErrorCode.TURNTABLE_DISCONNECTED,
            'popup': True
        }), 500


@app.route('/api/get-relay', methods=['GET'])
def get_relay_state():
    try:
        command = "RELAY?"
        app.logger.info(f"Sending relay query command: {command}")
        try:
            # Here we assume that porthandler.query_turntable is available.
            # It should send the command and return the response (e.g. "1" or "0")
            response = porthandler.query_turntable(command, timeout=2000)
        except Exception as query_err:
            app.logger.exception("Failed to query relay state: " + str(query_err))
            return jsonify({
                'error': "Turntable disconnected",
                'code': ErrorCode.TURNTABLE_DISCONNECTED,
                'popup': True
            }), 500

        # Process the response.
        # Default to off ("0") if response is empty.
        state_str = response.strip() if response else "0"
        # Convert to integer (1 or 0)
        state = 1 if state_str == "1" else 0

        return jsonify({"state": state}), 200

    except Exception as e:
        app.logger.exception("Error in getting relay state: " + str(e))
        return jsonify({
            'error': ERROR_MESSAGES.get(ErrorCode.TURNTABLE_DISCONNECTED),
            'code': ErrorCode.TURNTABLE_DISCONNECTED,
            'popup': True
        }), 500

@app.route('/api/toggle-relay', methods=['POST'])
def toggle_relay():
    try:
        data = request.get_json()
        state = data.get('state')  # Expect 1 (ON) or 0 (OFF)

        if state not in [0, 1]:
            app.logger.error("Invalid state value provided for relay toggle.")
            return jsonify({
                'error': ERROR_MESSAGES.get(ErrorCode.TURNTABLE_DISCONNECTED, "Invalid state value provided for relay toggle."),
                'code': ErrorCode.TURNTABLE_DISCONNECTED,
                'popup': True
            }), 400

        command = f"RELAY,{state}"
        app.logger.info(f"Sending command to turntable: {command}")

        # Send the command to the Arduino.
        try:
            porthandler.write_turntable(command, expect_response=False)
        except Exception as write_err:
            app.logger.exception("Failed to write turntable command: " + str(write_err))
            return jsonify({
                'error': "Turntable disconnected",
                'code': ErrorCode.TURNTABLE_DISCONNECTED,
                'popup': True
            }), 500
        return jsonify({"message": f"Relay {'ON' if state else 'OFF'}"}), 200
    except Exception as e:
        app.logger.exception("Error in toggling relay")
        return jsonify({
            'error': ERROR_MESSAGES.get(ErrorCode.TURNTABLE_DISCONNECTED),
            'code': ErrorCode.TURNTABLE_DISCONNECTED,
            'popup': True
        }), 500


# Barcode Scanner Functions
@app.route('/api/get-barcode', methods=['GET'])
def get_barcode():
    return jsonify({'barcode': globals.latest_barcode})

@app.route('/api/clear-barcode', methods=['POST'])
def clear_barcode():
    globals.latest_barcode = ""
    app.logger.info("Barcode cleared via API.")
    return jsonify({'message': 'Barcode cleared'}), 200
    
### Camera-related functions ###
def stop_camera_stream(camera_type):
    if camera_type not in globals.cameras:
        raise ValueError(f"Invalid camera type: {camera_type}")

    camera = globals.cameras.get(camera_type)

    with globals.grab_locks[camera_type]:
        if not globals.stream_running.get(camera_type, False):
            return "Stream already stopped."

        try:
            globals.stream_running[camera_type] = False
            if camera and camera.IsGrabbing():
                camera.StopGrabbing()
                app.logger.info(f"{camera_type.capitalize()} camera stream stopped.")

            if globals.stream_threads.get(camera_type) and globals.stream_threads[camera_type].is_alive():
                globals.stream_threads[camera_type].join(timeout=2)
                app.logger.info(f"{camera_type.capitalize()} stream thread stopped.")

            globals.stream_threads[camera_type] = None
            return f"{camera_type.capitalize()} stream stopped."
        except Exception as e:
            raise RuntimeError(f"Failed to stop {camera_type} stream: {str(e)}")

@app.route('/api/connect-camera', methods=['POST'])
def connect_camera():
    camera_type = request.args.get('type')
    if camera_type not in CAMERA_IDS:
        return jsonify({
            "error": ERROR_MESSAGES.get(ErrorCode.GENERIC, "Invalid camera type specified."),
            "code": ErrorCode.GENERIC,
            "popup": True
        }), 400

    result = connect_camera_internal(camera_type)
    if "error" in result:
        error_code = result.get("code", ErrorCode.GENERIC)
        result["popup"] = True
        result["error"] = ERROR_MESSAGES.get(error_code, result["error"])
        return jsonify(result), 404
    return jsonify(result), 200



@app.route('/api/disconnect-camera', methods=['POST'])
def disconnect_camera():
    camera_type = request.args.get('type')

    if camera_type not in globals.cameras or globals.cameras[camera_type] is None:
        app.logger.warning(f"{camera_type.capitalize()} camera is already disconnected or not initialized")
        return jsonify({"status": "already disconnected"}), 200

    try:
        stop_camera_stream(camera_type)
        app.logger.info(f"{camera_type.capitalize()} stream stopped before disconnecting.")
    except ValueError:
        app.logger.warning(f"Failed to stop {camera_type} stream: Invalid camera type.")
        # Decide how you want to handle this. If invalid camera type is fatal, return here:
        return jsonify({"error": "Invalid camera type"}), 400
    except RuntimeError as re:
        app.logger.warning(f"Error stopping {camera_type} stream: {str(re)}")
        # Maybe we continue to shut down the camera anyway
    except Exception as e:
        app.logger.error(f"Failed to disconnect {camera_type} camera: {e}")
        return jsonify({"error": str(e)}), 500

    camera = globals.cameras.get(camera_type, None)
    if camera and camera.IsGrabbing():
        camera.StopGrabbing()
        app.logger.info(f"{camera_type.capitalize()} camera grabbing stopped.")

    if camera and camera.IsOpen():
        camera.Close()
        app.logger.info(f"{camera_type.capitalize()} camera closed.")

    # Clean up references
    globals.cameras[camera_type] = None
    camera_properties[camera_type] = None  # Make sure camera_properties is in scope
    app.logger.info(f"{camera_type.capitalize()} camera disconnected successfully.")

    return jsonify({"status": "disconnected"}), 200

@app.route('/api/camera-name', methods=['GET'])
def get_camera_name():
    try:
        camera_type = request.args.get('type', 'main')
        camera = globals.cameras.get(camera_type)
        if camera is None or not camera.IsOpen():
            msg = f"{camera_type.capitalize()} camera is not connected."
            app.logger.warning(msg)
            return jsonify({"error": msg, "popup": True}), 400
        return jsonify({'name': camera.GetDeviceInfo().GetModelName()}), 200
    except Exception as e:
        app.logger.exception("Failed to get camera name")
        return jsonify({"error": "Failed to retrieve camera name", "details": str(e), "popup": True}), 500

@app.route('/api/status/camera', methods=['GET'])
def get_camera_status():
    camera_type = request.args.get('type')
    if camera_type not in globals.cameras:
        app.logger.error(f"Invalid camera type: {camera_type}")
        return jsonify({
            "error": ERROR_MESSAGES.get(ErrorCode.GENERIC, "Invalid camera type specified."),
            "code": ErrorCode.GENERIC,
            "popup": True
        }), 400

    camera = globals.cameras.get(camera_type)
    is_connected = camera is not None and camera.IsOpen()
    is_streaming = globals.stream_running.get(camera_type, False)

    factory = pylon.TlFactory.GetInstance()
    devices = factory.EnumerateDevices()
    found_serials = [dev.GetSerialNumber() for dev in devices]
    expected_serial = CAMERA_IDS.get(camera_type)

    if expected_serial not in found_serials:
        app.logger.warning(
            f"Camera {camera_type} with serial {expected_serial} not enumerated. Assuming physically disconnected."
        )
        if camera and camera.IsOpen():
            try:
                camera.StopGrabbing()
                camera.Close()
            except Exception as e:
                app.logger.error(f"Error closing camera {camera_type} after removal: {e}")
        globals.cameras[camera_type] = None
        globals.stream_running[camera_type] = False
        is_connected = False
        is_streaming = False

        error_code = (ErrorCode.MAIN_CAMERA_DISCONNECTED 
                      if camera_type.lower() == 'main' 
                      else ErrorCode.SIDE_CAMERA_DISCONNECTED)
        
        return jsonify({
            "connected": is_connected,
            "streaming": is_streaming,
            "error": ERROR_MESSAGES.get(error_code, "Unknown camera error"),
            "code": error_code,
            "popup": True
        }), 404

    return jsonify({
        "connected": is_connected,
        "streaming": is_streaming
    }), 200


    
@app.route('/api/get-camera-settings', methods=['GET'])
def get_camera_settings():
    camera_type = request.args.get('type')
    app.logger.info(f"API Call: /api/get-camera-settings for {camera_type}")

    if camera_type not in ['main', 'side']:
        return jsonify({"error": "Invalid camera type"}), 400

    settings_data = get_settings()
    camera_settings = settings_data.get('camera_params', {}).get(camera_type, {})

    if not camera_settings:
        app.logger.warning(f"No settings found for {camera_type} camera.")
        return jsonify({"error": "No settings found"}), 404

    app.logger.info(f"Sending {camera_type} camera settings to frontend: {camera_settings}")
    return jsonify(camera_settings), 200
    
@app.route('/api/update-camera-settings', methods=['POST'])
def update_camera_settings():
    try:
        data = request.json
        camera_type = data.get('camera_type')
        setting_name = data.get('setting_name')
        setting_value = data.get('setting_value')

        app.logger.info(f"Updating {camera_type} camera setting: {setting_name} = {setting_value}")

        # Apply the setting to the camera
        updated_value = validate_and_set_camera_param(
            globals.cameras[camera_type],
            setting_name,
            setting_value,
            camera_properties[camera_type],
            camera_type
        )

        settings_data = get_settings()
        settings_data['camera_params'][camera_type][setting_name] = updated_value
        save_settings()

        app.logger.info(f"{camera_type.capitalize()} camera setting {setting_name} updated and saved to settings.json")

        return jsonify({
            "message": f"{camera_type.capitalize()} camera {setting_name} updated and saved.",
            "updated_value": updated_value
        }), 200

    except Exception as e:
        app.logger.exception("Failed to update camera settings")
        return jsonify({"error": str(e)}), 500


### Video streaming Function ###
@app.route('/api/start-video-stream', methods=['GET'])
def start_video_stream():
    """
    Returns a live MJPEG response from generate_frames(camera_type).
    This is the *only* place we call generate_frames, to avoid double-streaming.
    """
    try:
        camera_type = request.args.get('type')
        scale_factor = float(request.args.get('scale', 0.1))

        if not camera_type or camera_type not in globals.cameras:
            app.logger.error(f"Invalid or missing camera type: {camera_type}")
            return jsonify({"error": "Invalid or missing camera type"}), 400

         # Ensure the camera is connected
        res = connect_camera_internal(camera_type)
        if "error" in res:
            app.logger.error(f"Camera connection failed: {res['error']}")
            return jsonify(res), 400

        with globals.grab_locks[camera_type]:
            if not globals.stream_running.get(camera_type, False):
                globals.stream_running[camera_type] = True
                app.logger.info(f"stream_running[{camera_type}] set to True in start_video_stream")

        app.logger.info(f"Starting video stream for {camera_type}")
        return Response(
            generate_frames(camera_type, scale_factor),
            mimetype='multipart/x-mixed-replace; boundary=frame'
        )

    except ValueError as ve:
        app.logger.error(f"Invalid input: {ve}")
        return jsonify({"error": "Invalid input parameters"}), 400

    except Exception as e:
        app.logger.exception("Unexpected error in start-video-stream")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/api/stop-video-stream', methods=['POST'])
def stop_video_stream():
    camera_type = request.args.get('type')
    app.logger.info(f"Received stop request for {camera_type}")

    try:
        message = stop_camera_stream(camera_type)
        return jsonify({"message": message}), 200
    except ValueError as ve:
        # E.g., invalid camera type
        app.logger.error(str(ve))
        return jsonify({"error": str(ve)}), 400
    except RuntimeError as re:
        app.logger.error(str(re))
        return jsonify({"error": str(re)}), 500
    except Exception as e:
        app.logger.exception(f"Unexpected exception while stopping {camera_type} stream.")
        return jsonify({"error": str(e)}), 500

def generate_frames(camera_type, scale_factor=0.1):
    app.logger.info(f"Generating frames for {camera_type} with scale factor {scale_factor}")
    camera = globals.cameras.get(camera_type)
    if not camera:
        app.logger.error(f"{camera_type.capitalize()} camera is not connected.")
        return
    if not camera.IsGrabbing():
        app.logger.info(f"{camera_type.capitalize()} camera starting grabbing.")
        camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

    try:
        while globals.stream_running[camera_type]:
            with globals.grab_locks[camera_type]:
                grab_result = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
                if grab_result.GrabSucceeded():
                    image = grab_result.Array
                    if scale_factor != 1.0:
                        width = int(image.shape[1] * scale_factor)
                        height = int(image.shape[0] * scale_factor)
                        image = cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)
                    success, frame = cv2.imencode('.jpg', image)
                    if success:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + frame.tobytes() + b'\r\n')
                grab_result.Release()
    except Exception as e:
        app.logger.error(f"Error in {camera_type} video stream: {e}")
        if "Device has been removed" in str(e):
            globals.stream_running[camera_type] = False
            if camera and camera.IsOpen():
                try:
                    camera.StopGrabbing()
                    camera.Close()
                except Exception as close_err:
                    app.logger.error(f"Failed to close {camera_type} after unplug: {close_err}")
            globals.cameras[camera_type] = None
    finally:
        app.logger.info(f"{camera_type.capitalize()} camera streaming thread stopped.")


def grab_camera_image(camera_type):
    """
    Attempts to grab an image from the specified camera.
    Returns a tuple: (image, error_response, status_code).
      - If successful, image is the grabbed image and error_response and status_code are None.
      - On error, image is None and error_response is a Flask response (JSON) with a status code.
    """
    try:
        with globals.grab_locks[camera_type]:
            camera = globals.cameras.get(camera_type)
            if camera is None or not camera.IsOpen():
                error_code = (ErrorCode.MAIN_CAMERA_DISCONNECTED 
                              if camera_type.lower() == 'main'
                              else ErrorCode.SIDE_CAMERA_DISCONNECTED)
                app.logger.error(f"{camera_type.capitalize()} camera is not connected or open.")
                return None, jsonify({
                    "error": ERROR_MESSAGES.get(error_code),
                    "code": error_code,
                    "popup": True
                }), 400

            # Retry grabbing the image up to 10 times.
            grab_result = retry_operation(
                lambda: attempt_frame_grab(camera, camera_type),
                max_retries=10,
                wait=1
            )

            if grab_result is None:
                app.logger.error("Grab result is None for camera " + camera_type)
                return None, jsonify({
                    "error": ERROR_MESSAGES.get(ErrorCode.MAIN_CAMERA_DISCONNECTED),
                    "code": ErrorCode.MAIN_CAMERA_DISCONNECTED,
                    "popup": True
                }), 400

            try:
                if not grab_result.GrabSucceeded():
                    app.logger.error("Grab result unsuccessful for camera " + camera_type)
                    return None, jsonify({
                        "error": ERROR_MESSAGES.get(
                            ErrorCode.MAIN_CAMERA_DISCONNECTED if camera_type.lower() == 'main'
                            else ErrorCode.SIDE_CAMERA_DISCONNECTED
                        ),
                        "code": ErrorCode.MAIN_CAMERA_DISCONNECTED if camera_type.lower() == 'main'
                                else ErrorCode.SIDE_CAMERA_DISCONNECTED,
                        "popup": True
                    }), 400
            except Exception as e:
                app.logger.exception("Exception while checking GrabSucceeded for camera " + camera_type + ": " + str(e))
                return None, jsonify({
                    "error": ERROR_MESSAGES.get(
                        ErrorCode.MAIN_CAMERA_DISCONNECTED if camera_type.lower() == 'main'
                        else ErrorCode.SIDE_CAMERA_DISCONNECTED
                    ),
                    "code": ErrorCode.MAIN_CAMERA_DISCONNECTED if camera_type.lower() == 'main'
                            else ErrorCode.SIDE_CAMERA_DISCONNECTED,
                    "popup": True
                }), 400

            app.logger.info("Image grabbed successfully for camera " + camera_type)
            image = grab_result.Array
            globals.latest_image = image.copy()
            grab_result.Release()
            
            return image, None, None

    except Exception as e:
        app.logger.exception("Error grabbing image for camera " + camera_type + ": " + str(e))
        return None, jsonify({
            "error": "Generic error during image grabbing",
            "code": ErrorCode.GENERIC,
            "popup": True
        }), 500

### Image Analysis Function ###
def analyze_slice(process_func, camera_type, label):
    try:
        # Grab image using the helper function.
        image, error_response, status_code = grab_camera_image(camera_type)
        if image is None:
            return error_response, status_code

        # Run the specified image processing function on the image.
        new_dot_contours, error_msg = process_func(image)
        if new_dot_contours is None:
            app.logger.error(f"Image processing failed during {label} analysis: {error_msg}")
            return jsonify({
                "error": "Image analysis error",
                "code": error_msg,
                "popup": True
            }), 500

        # Convert new_dot_contours to a list if needed.
        if isinstance(new_dot_contours, np.ndarray):
            new_dot_contours = new_dot_contours.tolist()

        new_dot_contours = [
            [int(x) if isinstance(x, (np.int32, np.int64)) else x for x in dot]
            for dot in new_dot_contours
        ]

        # Append new dots with stable IDs to global measurement data.
        for dot in new_dot_contours:
            x, y, col, area = dot
            dot_id = globals.dot_id_counter
            globals.dot_id_counter += 1
            globals.measurement_data.append([dot_id, x, y, col, area])
        
        # Update the count for this segment.
        globals.last_blob_counts[label] = len(new_dot_contours)

        app.logger.info(f"{label} analysis complete. {len(new_dot_contours)} new dots detected.")
        return jsonify({
            "message": f"{label} analysis successful",
            "new_dots": len(new_dot_contours)
        })

    except Exception as e:
        app.logger.exception(f"Error during {label} analysis: {e}")
        return jsonify({
            "error": "Generic error during image analysis",
            "code": ErrorCode.GENERIC,
            "popup": True
        }), 500   
    
@app.route('/api/analyze_center_circle', methods=['POST'])
def analyze_center_circle():
    app.logger.info("Center circle analysis started.")
    return analyze_slice(
        process_func = imageprocessing_main.process_center,
        camera_type='main',
        label='center_circle',
    )

@app.route('/api/analyze_center_slice', methods=['POST'])
def analyze_center_slice():
    app.logger.info("Center slice analysis started.")
    return analyze_slice(
        process_func = imageprocessing_main.process_inner_slice,
        camera_type='main',
        label='center_slice',
    )

@app.route('/api/analyze_outer_slice', methods=['POST'])
def analyze_outer_slice():
    app.logger.info("Outer slice analysis started.")
    return analyze_slice(
        process_func = imageprocessing_main.start_side_slice,
        camera_type='side',
        label='outer_slice',
    )
    
    
@app.route('/api/save_raw_image', methods=['POST'])
def save_raw_image_endpoint():
    try:
        # Use the new function that runs in its own process.
        folder = select_folder_external()

        if not folder:
            app.logger.info("User cancelled folder selection. Aborting raw image save operation.")
            # Return a 200 response indicating cancellation, so no error pops up.
            return jsonify({"message": "Folder selection cancelled. No images saved."}), 200

        target_folder = folder
        if not os.path.exists(target_folder):
            os.makedirs(target_folder)

        # Generate a timestamp string.
        now = datetime.now().strftime("%Y%m%d%H%M%S")

        # Grab main camera image.
        main_image, error_response, status_code = grab_camera_image('main')
        if main_image is None:
            app.logger.error("Grab result is None for camera main")
            return jsonify({
                "error": ERROR_MESSAGES.get(ErrorCode.MAIN_CAMERA_DISCONNECTED, "Main camera disconnected"),
                "code": ErrorCode.MAIN_CAMERA_DISCONNECTED,
                "popup": True
            }), 400

        # Grab side camera image.
        side_image, error_response_side, status_code_side = grab_camera_image('side')
        if side_image is None:
            app.logger.error("Grab result is None for camera side")
            return jsonify({
                "error": ERROR_MESSAGES.get(ErrorCode.SIDE_CAMERA_DISCONNECTED, "Side camera disconnected"),
                "code": ErrorCode.SIDE_CAMERA_DISCONNECTED,
                "popup": True
            }), 400

        center_filename = os.path.join(target_folder, f"{now}_center.jpg")
        side_filename = os.path.join(target_folder, f"{now}_side.jpg")

        cv2.imwrite(center_filename, main_image)
        cv2.imwrite(side_filename, side_image)

        app.logger.info("Raw images saved successfully: %s, %s", center_filename, side_filename)
        return jsonify({
            "message": "Raw images saved successfully",
            "center_filename": center_filename,
            "side_filename": side_filename
        }), 200

    except Exception as e:
        app.logger.exception("Error saving raw image: " + str(e))
        return jsonify({
            "error": ERROR_MESSAGES.get(ErrorCode.GENERIC),
            "code": ErrorCode.GENERIC,
            "popup": True
        }), 500

@app.route('/api/calculate-statistics', methods=['GET', 'POST'])
def calculate_statistics_endpoint():
    mode = request.args.get('mode', 'full')  # Mode can be "full", "slices", "center_circle", etc.
    try:
        result = calculate_statistics(globals.measurement_data, expected_counts=mode)
        if "error" in result:
            app.logger.error("Calculation error: " + result["error"])
            return jsonify({
                "error": "Image analysis failed",
                "code": ErrorCode.IMAGE_ANALYSIS_FAILED,
                "popup": True
            }), 500
        return jsonify(result), 200
    except Exception as e:
        app.logger.exception("Error calculating statistics: " + str(e))
        return jsonify({
            "error": "Generic error during statistics calculation",
            "code": ErrorCode.GENERIC,
            "popup": True
        }), 500
        
@app.route('/api/save-annotated-image', methods=['POST'])
def save_annotated_image_endpoint():
    try:
        data = request.get_json()
        label = data.get('label', 'annotated_images')
        
        if not hasattr(globals, 'last_saved_count'):
            globals.last_saved_count = 0

        # Get only the new dots added since the last annotated image was saved.
        new_dots = globals.dot_results[globals.last_saved_count:]
        
        # Update the counter for the next call.
        globals.last_saved_count = len(globals.dot_results)
        
        save_path = save_annotated_image(
            globals.latest_image,
            new_dots,
            os.path.join(get_base_path(), label)
        )
        return jsonify({"message": "Annotated image saved", "image_path": save_path}), 200
    except Exception as e:
        app.logger.exception("Error saving annotated image: " + str(e))
        return jsonify({
            "error": "Failed to save annotated image",
            "code": ErrorCode.GENERIC,
            "popup": True
        }), 500
        
@app.route('/api/save_results_to_csv', methods=['POST'])
def save_results_to_csv_endpoint():
    try:
        data = request.get_json() or {}
        spinneret_id = data.get("spinneret_id", "unknown")
        
        # Call your new function
        filename = save_dot_results_to_csv(globals.dot_results, spinneret_id)
        
        if filename is None:
            raise Exception("CSV saving returned None")

        app.logger.info(f"Measurement results saved to CSV: {filename}")
        return jsonify({"message": "CSV saved successfully", "filename": filename}), 200

    except Exception as e:
        app.logger.exception("Error saving measurement results to CSV: " + str(e))
        return jsonify({
            "error": ERROR_MESSAGES.get(ErrorCode.GENERIC, "Failed to save CSV"),
            "code": ErrorCode.GENERIC,
            "popup": True
        }), 500


### Statistics-related functions ###
@app.route('/api/update_results', methods=['POST'])
def update_results():
    try:
        mode = request.json.get("mode")
        if not mode:
            return jsonify({"error": "Missing 'mode' in request"}), 400

        expected_counts_map = {
            "full": {"center_circle": 360, "center_slice": 510, "outer_slice": 2248},
            "center_circle": {"center_circle": 360, "center_slice": 0, "outer_slice": 0},
            "center_slice": {"center_circle": 0, "center_slice": 510, "outer_slice": 0},
            "outer_slice": {"center_circle": 0, "center_slice": 0, "outer_slice": 2248},
            "slices": {"center_circle": 0, "center_slice": 510, "outer_slice": 2248},
        }

        if mode not in expected_counts_map:
            return jsonify({"error": f"Invalid mode '{mode}'"}), 400

        expected_counts = expected_counts_map[mode]
        
        if not globals.measurement_data:
            return jsonify({"error": "No measurement data available."}), 400

        # new_blob_counts from the last route calls
        new_blob_counts = {
            "center_circle": globals.last_blob_counts.get("center_circle", 0),
            "center_slice": globals.last_blob_counts.get("center_slice", 0),
            "outer_slice": globals.last_blob_counts.get("outer_slice", 0),
        }
        
        app.logger.info(new_blob_counts)

        # Calculate shortfall
        missing_blobs = 0
        for label, needed in expected_counts.items():
            found = new_blob_counts[label]
            shortfall = max(0, needed - found)
            missing_blobs += shortfall

        # Add shortfall directly to locked_class1_count
        globals.locked_class1_count += missing_blobs

        # Re-run classification
        result = calculate_statistics(globals.measurement_data, expected_counts)
        if "error" in result:
            return jsonify({"error": result["error"]}), 500

        # Save final counts
        globals.result_counts = result["result_counts"]
        return jsonify({
            "message": f"Results updated for mode: {mode}",
            "result_counts": globals.result_counts
        })

    except Exception as e:
        app.logger.exception(f"Exception in update_results: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/reset_results', methods=['POST'])
def reset_results():
    try:
        # Reset global measurement results
        globals.result_counts = [0, 0, 0]
        globals.measurement_data.clear()
        globals.locked_class1_count = 0
        globals.last_blob_counts = {"center_circle": 0, "center_slice": 0, "outer_slice": 0}

        app.logger.info("Results reset successfully.")
        return jsonify({
            "message": "Results reset successfully",
            "result_counts": globals.result_counts
        })
    except Exception as e:
        app.logger.exception(f"Error resetting results: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/get-other-settings', methods=['GET'])
def get_other_settings():
    category = request.args.get('category')
    if not category:
        return jsonify({"error": "Category parameter is required."}), 400

    settings_data = get_settings()
    if category not in settings_data:
        return jsonify({"error": f"Category '{category}' not found."}), 404

    return jsonify({category: settings_data[category]}), 200

@app.route('/api/update-other-settings', methods=['POST'])
def update_other_settings():
    try:
        data = request.json
        category = data.get('category')           # e.g. 'size_limits'
        setting_name = data.get('setting_name')     # e.g. 'ng_limit'
        setting_value = data.get('setting_value')   # e.g. 123

        app.logger.info(f"Updating {category}.{setting_name} = {setting_value}")

        # Retrieve the in-memory settings
        settings_data = get_settings()
        if category not in settings_data:
            settings_data[category] = {}

        # For consistency, you could add validation or conversion here if needed.
        # For now, we'll just pass the new value as is.
        updated_value = setting_value

        # Update the setting in the in-memory dict
        settings_data[category][setting_name] = updated_value

        # Save the updated settings to disk
        save_settings()

        app.logger.info(f"{category}.{setting_name} updated and saved to settings.json")

        return jsonify({
            "message": f"{category}.{setting_name} updated and saved.",
            "updated_value": updated_value
        }), 200

    except Exception as e:
        app.logger.exception("Failed to update other settings")
        return jsonify({"error": str(e)}), 500

@app.route('/api/connect_sql_database', methods=['GET'])
def connect_sql_database():
    try:
        settings_data = get_settings()
        sql_config = settings_data.get("sql_server")
        if not sql_config:
            return jsonify({
                "error": "SQL Server configuration not found.",
                "code": ErrorCode.SQL_DB_ERROR,
                "popup": True
            }), 400

        server = sql_config.get("server")
        database = sql_config.get("db_name")
        username = sql_config.get("username")
        password = sql_config.get("password")

        connection_string = (
            'DRIVER={ODBC Driver 17 for SQL Server};'
            'SERVER=tcp:' + server + ',1433;'
            'DATABASE=' + database + ';'
            'UID=' + username + ';'
            'PWD=' + password +';'
            'Pooling=False;'
        )
        
        # Attempt to connect with a short timeout.
        conn = pyodbc.connect(connection_string, timeout=15)
        conn.close()
        return jsonify({"message": "Connected to the database successfully!"}), 200

    except Exception as e:
        app.logger.exception("Failed to connect to the database.")
        return jsonify({
            "error": ERROR_MESSAGES[ErrorCode.SQL_DB_ERROR],
            "code": ErrorCode.SQL_DB_ERROR,
            "popup": True
        }), 500


@app.route('/api/disconnect_sql_database', methods=['POST'])
def disconnect_sql_database():
    # If using a persistent connection, close it here.
    app.logger.info("SQL database disconnected (if connection was persistent).")
    return jsonify({"message": "SQL database disconnected successfully."}), 200

@app.route('/api/save-measurement-result', methods=['POST'])
def save_measurement_result():
    try:
        data = request.get_json()
        # Retrieve measurement record fields from the JSON payload
        measurement_date = data.get('date')
        measurement_time = data.get('time')
        spinneret_id = data.get('id')         # previously MeasurementID
        spinneret_barcode = data.get('barcode')  # previously Barcode
        operator = data.get('operator')
        clogged = data.get('clogged')
        partially_clogged = data.get('partiallyClogged')
        clean = data.get('clean')
        result = data.get('result')
        
        # Retrieve additional settings from settings.json.
        settings_data = get_settings()
        size_limits = settings_data.get("size_limits", {})
        class1_limit = size_limits.get("class1", 0)
        class2_limit = size_limits.get("class2", 0)
        ng_limit = size_limits.get("ng_limit", 0)
        
        conn = get_db_connection()  # Reads dynamic settings; Pooling is disabled.
        cursor = conn.cursor()
        
        insert_sql = """
            INSERT INTO MeasurementResults 
                (MeasurementDate, MeasurementTime, SpinneretID, SpinneretBarcode, Operator, 
                 Clogged, PartiallyClogged, Clean, Result, Class1Limit, Class2Limit, NgLimit)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        cursor.execute(insert_sql, measurement_date, measurement_time, spinneret_id, spinneret_barcode, operator,
                         clogged, partially_clogged, clean, result, class1_limit, class2_limit, ng_limit)
        conn.commit()
        conn.close()
        
        app.logger.info("Measurement result saved to database.")
        return jsonify({"message": "Measurement result saved successfully."}), 200
        
    except Exception as e:
        app.logger.exception("Error saving measurement result to database: " + str(e))
        return jsonify({
            "error": ERROR_MESSAGES[ErrorCode.SQL_DB_ERROR],
            "code": ErrorCode.SQL_DB_ERROR,
            "popup": True
        }), 500
        
@app.route('/api/check-db-connection', methods=['GET'])
def check_db_connection():
    try:
        conn = get_db_connection()  # This now reads dynamic settings, with Pooling=False.
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        conn.close()
        if result is not None:
            return jsonify({"message": "Connected to the database successfully!"}), 200
        else:
            return jsonify({
                "error": ERROR_MESSAGES[ErrorCode.SQL_DB_ERROR],
                "code": ErrorCode.SQL_DB_ERROR,
                "popup": True
            }), 500
    except Exception as e:
        app.logger.exception("Failed to check database connection.")
        return jsonify({
            "error": ERROR_MESSAGES[ErrorCode.SQL_DB_ERROR],
            "code": ErrorCode.SQL_DB_ERROR,
            "popup": True
        }), 500
        
        
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"ready": True}), 200
    
### Internal Helper Functions ### 
def get_base_path():
    """
    Ensures all output folders like 'Results/csv_results' and 'Results/annotated_images'
    are saved next to the main NozzleScanner.exe (not inside the resources folder).
    """
    if getattr(sys, 'frozen', False):
        # If frozen, sys.executable points to .../resources/GUI_backend.exe
        return os.path.join(os.path.dirname(os.path.dirname(sys.executable)), 'Results')
    else:
        # In dev mode, simulate the same directory structure
        return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Results'))


def select_folder_external() -> str:
    try:
        result = subprocess.run(
            ['python', 'select_folder_dialog.py'], 
            capture_output=True, 
            text=True,
            timeout=15  # seconds
        )
        output = json.loads(result.stdout.strip())
        return output['folder']
    except Exception as e:
        print("Folder selection failed:", e)
        return ""
    
def attempt_frame_grab(camera, camera_type):
    # Attempt to retrieve the image result.
    grab_result = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
    # Check if the frame grab was successful.
    if not grab_result.GrabSucceeded():
        grab_result.Release()
        raise Exception(f"Grab result unsuccessful for camera {camera_type}")
    return grab_result

def get_db_connection():
    from settings_manager import get_settings
    settings_data = get_settings()
    sql_config = settings_data.get("sql_server")
    if not sql_config:
        raise Exception("SQL Server configuration not found in settings.")

    server = sql_config.get("server")
    database = sql_config.get("db_name")
    username = sql_config.get("username")
    password = sql_config.get("password")

    connection_string = (
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=tcp:' + server + ',1433;'
        'DATABASE=' + database + ';'
        'UID=' + username + ';'
        'PWD=' + password +';'
        'Pooling=False;'
    )

    try:
        # Attempt to connect with a short timeout.
        conn = pyodbc.connect(connection_string, timeout=15)
        return conn
    except Exception as e:
        # Log error and re-raise if needed.
        raise Exception("Failed to connect to SQL Server: " + str(e))

def connect_camera_internal(camera_type):
    target_serial = CAMERA_IDS.get(camera_type)
    factory = pylon.TlFactory.GetInstance()
    devices = factory.EnumerateDevices()

    selected_device = next((device for device in devices if device.GetSerialNumber() == target_serial), None)
    if not selected_device:
        error_code = ErrorCode.MAIN_CAMERA_DISCONNECTED if camera_type == 'main' else ErrorCode.SIDE_CAMERA_DISCONNECTED
        return {
            "error": f"Camera {camera_type} with serial {target_serial} not found",
            "code": error_code,
            "popup": True
        }

    # If already connected, return info.
    if globals.cameras.get(camera_type) and globals.cameras[camera_type].IsOpen():
        return {
            "connected": True,
            "name": selected_device.GetModelName(),
            "serial": selected_device.GetSerialNumber()
        }

    try:
        globals.cameras[camera_type] = pylon.InstantCamera(factory.CreateDevice(selected_device))
        globals.cameras[camera_type].Open()
    except Exception as e:
        # Use GetPortName() if available; otherwise, fallback.
        port_name = selected_device.GetPortName() if hasattr(selected_device, "GetPortName") else "unknown"
        app.logger.exception(f"Failed to connect to camera {camera_type} on port {port_name}: {e}")
        error_code = ErrorCode.MAIN_CAMERA_DISCONNECTED if camera_type == 'main' else ErrorCode.SIDE_CAMERA_DISCONNECTED
        return {
            "error": ERROR_MESSAGES.get(error_code, "Camera not connected."),
            "code": error_code,
            "popup": True
        }

    if not globals.cameras[camera_type].IsOpen():
        app.logger.error(f"Camera {camera_type} failed to open after connection attempt.")
        return {"error": f"Camera {camera_type} failed to open", "popup": True}

    # Retrieve camera properties and apply settings.
    camera_properties[camera_type] = get_camera_properties(globals.cameras[camera_type])
    settings_data = get_settings()
    apply_camera_settings(camera_type, globals.cameras, camera_properties, settings_data)

    return {
        "connected": True,
        "name": selected_device.GetModelName(),
        "serial": selected_device.GetSerialNumber()
    }



def start_camera_stream_internal(camera_type, scale_factor=0.1):
    app.logger.info(f"Starting {camera_type} camera stream internally with scale factor {scale_factor}")
    try:
        if camera_type not in globals.cameras or globals.cameras[camera_type] is None or not globals.cameras[camera_type].IsOpen():
            error_msg = f"{camera_type.capitalize()} camera is not connected or open."
            app.logger.error(error_msg)
            return {"error": error_msg, "popup": True}

        with globals.grab_locks[camera_type]:
            if globals.stream_running.get(camera_type, False):
                app.logger.info(f"{camera_type.capitalize()} stream is already running.")
                return {"message": "Stream already running"}
            if not globals.cameras[camera_type].IsGrabbing():
                app.logger.info(f"{camera_type.capitalize()} camera starting grabbing.")
                globals.cameras[camera_type].StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
            if not globals.stream_threads.get(camera_type) or not globals.stream_threads[camera_type].is_alive():
                globals.stream_running[camera_type] = True
            else:
                app.logger.info(f"{camera_type.capitalize()} stream thread already running.")
        return {"message": f"{camera_type.capitalize()} video stream started successfully."}
    except Exception as e:
        app.logger.exception(f"Error starting {camera_type} stream: {e}")
        return {"error": str(e), "popup": True}

        
def initialize_cameras():
    app.logger.info("Initializing cameras...")
    for camera_type in CAMERA_IDS.keys():
        if globals.cameras.get(camera_type) and globals.cameras[camera_type].IsOpen():
            app.logger.info(f"{camera_type.capitalize()} camera is already connected. Skipping initialization.")
            continue
        
        try:
            result = connect_camera_internal(camera_type)
            if result.get('connected'):
                app.logger.info(f"Successfully connected {camera_type} camera.")
                start_camera_stream_internal(camera_type)
            else:
                app.logger.error(f"Failed to connect {camera_type} camera: {result.get('error')}")
        except Exception as e:
            app.logger.error(f"Error during {camera_type} camera initialization: {e}")
            
def initialize_serial_devices():
    """Initialize serial devices at startup."""
    app.logger.info("Initializing serial devices...")

    try:
        # Connect turntable as before.
        device = porthandler.connect_to_turntable()
        if device:
            porthandler.turntable = device
            app.logger.info("Turntable connected automatically on startup.")
        else:
            app.logger.error("Failed to auto-connect turntable on startup.")
    except Exception as e:
        app.logger.error(f"Error initializing turntable: {e}")

    try:
        # Connect barcode scanner similarly.
        device = porthandler.connect_to_barcode_scanner()
        if device:
            app.logger.info("Barcode scanner connected automatically on startup.")
        else:
            app.logger.error("Failed to auto-connect barcode scanner on startup.")
    except Exception as e:
        app.logger.error(f"Error initializing barcode scanner: {e}")

    # Start barcode scanner listener thread (if not already running)
    if not any(t.name == "BarcodeListener" for t in threading.enumerate()):
        threading.Thread(target=barcode_scanner_listener, name="BarcodeListener", daemon=True).start()

        
if __name__ == '__main__':
    multiprocessing.freeze_support()
    
    load_settings()
    initialize_cameras()
    initialize_serial_devices()
    
    

    app.run(debug=False, use_reloader=False)