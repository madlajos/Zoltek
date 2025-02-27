from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from tkinter import filedialog, Tk
import os
import cv2
import time
from porthandler import barcode_scanner_listener
import logging
from logging.handlers import RotatingFileHandler
import globals
from pypylon import pylon
from cameracontrol import (apply_camera_settings, set_centered_offset, 
                           validate_and_set_camera_param, get_camera_properties, Handler)
import porthandler
import imageprocessing
import threading
from settings_manager import load_settings, save_settings, get_settings
import numpy as np
from statistics_processor import calculate_statistics, save_annotated_image

app = Flask(__name__)
app.secret_key = 'Zoltek'
logging.basicConfig(level=logging.DEBUG)
CORS(app)
app.debug = True

file_handler = RotatingFileHandler('flask.log', maxBytes=10240, backupCount=10)
app.logger.addHandler(file_handler)
console_handler = logging.StreamHandler()
app.logger.addHandler(console_handler)
app.logger.setLevel(logging.DEBUG)

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

if not hasattr(globals, 'measurement_data'):
    globals.measurement_data = []  # This will store all the dot_contours arrays.
if not hasattr(globals, 'result_counts'):
    globals.result_counts = [0, 0, 0]  # One counter per result class.



### Serial Device Functions ###
# Define the route for checking device status
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
            return jsonify({'error': 'Failed to connect to Turntable'}), 404
    except Exception as e:
        app.logger.exception("Exception occurred while connecting to Turntable")
        return jsonify({'error': str(e)}), 500

@app.route('/api/connect-to-barcode', methods=['POST'])
def connect_barcode_scanner():
    try:
        app.logger.info("Attempting to connect to Barcode Scanner")
        if porthandler.barcode_scanner and porthandler.barcode_scanner.is_open:
            app.logger.info("Barcode Scanner already connected.")
            return jsonify({'message': 'Barcode Scanner already connected'}), 200

        device = porthandler.connect_to_barcode_scanner()
        if device:
            app.logger.info("Successfully connected to Barcode Scanner")
            return jsonify({'message': 'Barcode Scanner connected', 'port': device.port}), 200
        else:
            app.logger.error("Failed to connect Barcode Scanner: Device not found")
            return jsonify({'error': 'Failed to connect Barcode Scanner'}), 404
    except Exception as e:
        app.logger.exception("Exception occurred while connecting to Barcode Scanner")
        return jsonify({'error': str(e)}), 500

@app.route('/api/disconnect-to-<device_name>', methods=['POST'])
def disconnect_serial_device(device_name):
    try:
        app.logger.info(f"Attempting to disconnect from {device_name}")
        porthandler.disconnect_serial_device(device_name)
        app.logger.info(f"Successfully disconnected from {device_name}")
        return jsonify('ok')
    except Exception as e:
        logging.exception(f"Exception occurred while disconnecting from {device_name}")
        return jsonify({'error': str(e)}), 500


    

### Turntable Functions ###
@app.route('/home_turntable_with_image', methods=['POST'])
def home_turntable_with_image():
    try:
        app.logger.info("Homing process initiated.")
        camera_type = 'main'

        # Step 1: Grab the image QUICKLY and RELEASE the camera
        with globals.grab_locks[camera_type]:
            camera = globals.cameras.get(camera_type)

            if camera is None or not camera.IsOpen():
                app.logger.error("Main camera is not connected or open.")
                return jsonify({"error": "Main camera is not connected or open."}), 400

            grab_result = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)

            if not grab_result.GrabSucceeded():
                grab_result.Release()
                app.logger.error("Failed to grab image from camera.")
                return jsonify({"error": "Failed to grab image from camera."}), 500

            app.logger.info("Image grabbed successfully.")
            image = grab_result.Array
            grab_result.Release()  # Release camera lock immediately

        # Step 2: Process the image and calculate rotation
        rotation_needed = imageprocessing.home_turntable_with_image(image)
        command = f"{abs(rotation_needed)},{1 if rotation_needed > 0 else 0}"
        app.logger.info(f"Image processing complete. Rotation needed: {rotation_needed}")

        # Step 3: Send rotation command & **wait for DONE**
        movement_success = porthandler.write_turntable(command)

        if not movement_success:
            return jsonify({"error": "Turntable did not confirm movement completion"}), 500

        app.logger.info("Rotation completed successfully.")

        # Step 4: Update global position after homing
        globals.turntable_position = 0
        globals.turntable_homed = True
        app.logger.info("Homing completed successfully. Position set to 0.")

        # Step 5: Return success response (AFTER turntable confirms "DONE")
        return jsonify({
            "message": "Homing successful",
            "rotation": rotation_needed,
            "current_position": globals.turntable_position
        })

    except Exception as e:
        app.logger.exception(f"Error during homing: {e}")
        return jsonify({"error": str(e)}), 500


### Image Analysis Function ###
def analyze_slice(process_func, camera_type, label):
    """
    Helper to reduce boilerplate in each route:
      - process_func: function that processes the raw image (e.g. process_center, process_inner_slice, etc.)
      - camera_type: 'main' or 'side'
      - label: string key like 'center_circle', 'center_slice', 'outer_slice'
    """
    try:
        with globals.grab_locks[camera_type]:
            camera = globals.cameras.get(camera_type)
            if camera is None or not camera.IsOpen():
                msg = f"{camera_type.capitalize()} camera is not connected or open."
                app.logger.error(msg)
                return jsonify({"error": msg}), 400

            # Retry grabbing the image up to 10 times
            max_retries = 10
            for attempt in range(max_retries):
                grab_result = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)

                if grab_result.GrabSucceeded():
                    image = grab_result.Array
                    grab_result.Release()
                    globals.latest_image = image.copy()
                    break  # Exit the loop if successful

                grab_result.Release()
                app.logger.warning(f"Attempt {attempt + 1}/{max_retries}: Failed to grab image from {camera_type} camera.")
                time.sleep(0.1)  # Wait 100ms before retrying

            else:
                # If we exhaust retries, return an error
                msg = f"Failed to grab image from {camera_type} camera after {max_retries} attempts."
                app.logger.error(msg)
                return jsonify({"error": msg}), 500


        # 1) Detect new contours
        new_dot_contours = process_func(image)
        if isinstance(new_dot_contours, np.ndarray):
            new_dot_contours = new_dot_contours.tolist()

        # Convert np.int32 → Python int
        new_dot_contours = [
            [int(x) if isinstance(x, (np.int32, np.int64)) else x for x in dot]
            for dot in new_dot_contours
        ]

        # 2) Append new dots with stable IDs
        #    e.g. new_dot_contours = [[x,y,col,area], ...]
        old_counter = globals.dot_id_counter
        for dot in new_dot_contours:
            x, y, col, area = dot
            dot_id = globals.dot_id_counter
            globals.dot_id_counter += 1
            globals.measurement_data.append([dot_id, x, y, col, area])

        # Record how many new dots for this label
        globals.last_blob_counts[label] = len(new_dot_contours)

        # 3) Classify entire dataset
        result = calculate_statistics(globals.measurement_data)
        if "error" in result:
            app.logger.error(f"Calculation error in {label}: {result['error']}")
            return jsonify({"error": result["error"]}), 500

        # This classification returns classified dots as (dot_id, x, y, col, area, class)
        classified_dots = result["classified_dots"]
        final_counts = result["result_counts"]

        # 4) Identify the newly added dot IDs
        newly_added_ids = set(range(old_counter, globals.dot_id_counter))

        # Extract only the newly classified dots (by ID)
        latest_classified_dots = [
            d for d in classified_dots
            if d[0] in newly_added_ids
        ]

        # Convert (dot_id, x, y, col, area, cls) → (x, y, col, area, cls) for annotation
        latest_for_annotation = [
            (x, y, col, area, cls) for (dot_id, x, y, col, area, cls) in latest_classified_dots
        ]

        # 5) Annotate
        save_path = save_annotated_image(globals.latest_image, latest_for_annotation, label)

        # 6) Logging & Return
        app.logger.info(f"{label} analysis complete. {len(new_dot_contours)} new dots detected.")
        app.logger.info(f"Saved annotated image: {save_path}")

        return jsonify({
            "message": f"{label} analysis successful",
            "dot_contours": latest_for_annotation,
            "image_path": save_path,
            "result_counts": final_counts
        })

    except Exception as e:
        app.logger.exception(f"Error during {label} analysis: {e}")
        return jsonify({"error": str(e)}), 500
    
    
@app.route('/analyze_center_circle', methods=['POST'])
def analyze_center_circle():
    app.logger.info("Center circle analysis started.")
    return analyze_slice(
        process_func=imageprocessing.process_center,
        camera_type='main',
        label='center_circle',
    )

@app.route('/analyze_center_slice', methods=['POST'])
def analyze_center_slice():
    app.logger.info("Center slice analysis started.")
    return analyze_slice(
        process_func=imageprocessing.process_inner_slice,
        camera_type='main',
        label='center_slice',
    )

@app.route('/analyze_outer_slice', methods=['POST'])
def analyze_outer_slice():
    app.logger.info("Outer slice analysis started.")
    return analyze_slice(
        process_func=imageprocessing.start_side_slice,
        camera_type='side',
        label='outer_slice',
    )

@app.route('/update_results', methods=['POST'])
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


@app.route('/reset_results', methods=['POST'])
def reset_results():
    try:
        # Reset global measurement results
        globals.result_counts = [0, 0, 0]
        globals.measurement_data.clear()
        globals.last_blob_counts = {"center_circle": 0, "center_slice": 0, "outer_slice": 0}

        app.logger.info("Results reset successfully.")
        return jsonify({
            "message": "Results reset successfully",
            "result_counts": globals.result_counts
        })
    except Exception as e:
        app.logger.exception(f"Error resetting results: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/move_turntable_relative', methods=['POST'])
def move_turntable_relative():
    try:
        data = request.get_json()
        move_by = data.get('degrees')

        if move_by is None or not isinstance(move_by, (int, float)):
            app.logger.error("Invalid input: 'degrees' must be a number.")
            return jsonify({'error': 'Invalid input, provide degrees as a number'}), 400

        direction = 'CW' if move_by > 0 else 'CCW'
        command = f"{abs(move_by)},{1 if move_by > 0 else 0}"
        app.logger.info(f"Sending command to turntable: {command}")

        # Send the command to the turntable
        porthandler.write_turntable(command, expect_response=False)

        # Update position only if the turntable is homed
        if globals.turntable_homed:
            app.logger.info(f"Updating position (before): {globals.turntable_position}")
            globals.turntable_position = (globals.turntable_position - move_by) % 360
            app.logger.info(f"Updated position (after): {globals.turntable_position}")
        else:
            app.logger.info("Turntable is not homed. Position remains '?'.")

        return jsonify({
            'message': f'Turntable moved {move_by} degrees {direction}',
            'current_position': globals.turntable_position if globals.turntable_homed else '?'
        })
    except Exception as e:
        app.logger.exception(f"Error in move_turntable_relative: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/toggle-relay', methods=['POST'])
def toggle_relay():
    try:
        data = request.get_json()
        state = data.get('state')  # Expect 1 (ON) or 0 (OFF)

        if state not in [0, 1]:
            return jsonify({"error": "Invalid state value"}), 400

        command = f"RELAY,{state}"
        app.logger.info(f"Sending command to turntable: {command}")

        # Send the command to the Arduino
        porthandler.write_turntable(command, expect_response=False)

        return jsonify({"message": f"Relay {'ON' if state else 'OFF'}"}), 200

    except Exception as e:
        app.logger.exception("Error in toggling relay")
        return jsonify({"error": str(e)}), 500

# Define the route for starting the video stream
@app.route('/select-folder', methods=['GET'])
def select_folder():
    try:
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        folder_selected = filedialog.askdirectory()
        root.destroy()
        if folder_selected:
            return jsonify({'folder': folder_selected}), 200
        else:
            return jsonify({'error': 'No folder selected'}), 400
    except Exception as e:
        app.logger.exception("Failed to select folder")
        return jsonify({'error': str(e)}), 500

@app.route('/start-video-stream', methods=['GET'])
def start_video_stream():
    """
    Returns a live MJPEG response from generate_frames(camera_type).
    This is the *only* place we call generate_frames, to avoid double-streaming.
    """
    try:
        camera_type = request.args.get('type')
        scale_factor = float(request.args.get('scale', 0.25))

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


@app.route('/stop-video-stream', methods=['POST'])
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

def generate_frames(camera_type, scale_factor=0.25):
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

                    _, frame = cv2.imencode('.jpg', image)
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
            globals.cameras[camera_type] = None  # Now future status checks see `None => not connected`
    
    finally:
        # stream_running[camera_type] = False
        app.logger.info(f"{camera_type.capitalize()} camera streaming thread stopped.")


@app.route('/connect-camera', methods=['POST'])
def connect_camera():
    camera_type = request.args.get('type')
    if camera_type not in CAMERA_IDS:
        return jsonify({"error": "Invalid camera type specified"}), 400

    result = connect_camera_internal(camera_type)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result), 200

@app.route('/disconnect-camera', methods=['POST'])
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

    
@app.route('/api/status/camera', methods=['GET'])
def get_camera_status():
    camera_type = request.args.get('type')

    if camera_type not in globals.cameras:
        app.logger.error(f"Invalid camera type: {camera_type}")
        return jsonify({"error": "Invalid camera type specified"}), 400

    camera = globals.cameras.get(camera_type)
    is_connected = camera is not None and camera.IsOpen()
    is_streaming = globals.stream_running.get(camera_type, False)

    # 1) Double-check if device is truly present in the enumerated device list.
    factory = pylon.TlFactory.GetInstance()
    devices = factory.EnumerateDevices()
    found_serials = [dev.GetSerialNumber() for dev in devices]

    # Suppose you store the camera's serial in some global map, e.g. CAMERA_IDS[camera_type].
    expected_serial = CAMERA_IDS.get(camera_type)

    # If expected serial is NOT in the enumerated list, the device is physically missing
    if expected_serial not in found_serials:
        app.logger.warning(
           f"Camera {camera_type} with serial {expected_serial} not enumerated. " 
           "Assuming physically disconnected."
        )
        # Mark as disconnected in memory
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

    return jsonify({
        "connected": is_connected,
        "streaming": is_streaming
    }), 200
    
@app.route('/api/status/serial/<device_name>', methods=['GET'])
def get_serial_device_status(device_name):
    logging.debug(f"Received status request for device: {device_name}")
    device = None
    if device_name.lower() == 'turntable':
        device = porthandler.turntable
    elif device_name.lower() in ['barcode', 'barcodescanner']:
        device = porthandler.barcode_scanner
    else:
        logging.error("Invalid device name")
        return jsonify({'error': 'Invalid device name'}), 400

    if device and device.is_open:
        if device_name.lower() == 'turntable':
            # Only send "IDN?" if we're not already waiting for another response
            if not porthandler.turntable_waiting_for_done:
                try:
                    device.write(b'IDN?\n')
                    response = device.read(10).decode(errors='ignore').strip()
                    if response:
                        logging.debug(f"{device_name} is responsive on port {device.port}")
                        return jsonify({'connected': True, 'port': device.port})
                except Exception as e:
                    logging.warning(f"{device_name} is unresponsive, disconnecting. Error: {str(e)}")
                    porthandler.disconnect_serial_device(device_name)  # Force disconnect
                    return jsonify({'connected': False})

        logging.debug(f"{device_name} is connected on port {device.port}")
        return jsonify({'connected': True, 'port': device.port})

    logging.warning(f"{device_name} appears to be disconnected.")



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
    
@app.route('/api/update-other-settings', methods=['POST'])
def update_other_settings():
    try:
        data = request.json
        category = data.get('category')           # e.g. 'size_limits'
        setting_name = data.get('setting_name')   # e.g. 'class1'
        setting_value = data.get('setting_value') # e.g. 123

        app.logger.info(f"Updating {category}.{setting_name} = {setting_value}")

        # Grab the in-memory settings
        settings_data = get_settings()

        # If the category (e.g., size_limits) doesn’t exist, initialize it
        if category not in settings_data:
            settings_data[category] = {}

        # Update the chosen setting with the new value
        settings_data[category][setting_name] = setting_value

        # Optionally, you could do validation or type-casting here,
        # e.g. ensuring it's an integer or within certain bounds

        # Save to disk
        save_settings()

        app.logger.info(f"{category}.{setting_name} updated and saved to settings.json")

        # Return the updated (or validated) value to the frontend
        return jsonify({
            "message": f"{category}.{setting_name} updated and saved.",
            "updated_value": setting_value
        }), 200

    except Exception as e:
        app.logger.exception("Failed to update other settings")
        return jsonify({"error": str(e)}), 500

@app.route('/video-stream', methods=['GET'])
def video_stream():
    camera_type = request.args.get('type')

    if camera_type not in globals.cameras:
        app.logger.error(f"Invalid camera type: {camera_type}")
        return jsonify({"error": "Invalid camera type specified"}), 400

    app.logger.info(f"{camera_type.capitalize()} camera stream started successfully")
    return Response(generate_frames(camera_type), mimetype='multipart/x-mixed-replace; boundary=frame')

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

@app.route('/api/set-centered-offset', methods=['POST'])
def set_centered_offset_route():
    global camera
    if camera:
        centered_offsets = set_centered_offset(camera)
        return jsonify(centered_offsets), 200
    else:
        return jsonify({"error": "Camera not connected"}), 400
    
@app.route('/api/camera-name', methods=['GET'])
def get_camera_name():
    try:
        if camera:
            return jsonify({'name': camera.GetDeviceInfo().GetModelName()}), 200
        else:
            return jsonify({'name': 'No camera connected'}), 200
    except Exception as e:
        app.logger.exception("Failed to get camera name")
        return jsonify({'error': str(e)}), 500

@app.route('/api/save-image', methods=['POST'])
def save_image():
    global handler
    try:
        data = request.get_json()
        save_directory = data.get('save_directory', '').strip()

        app.logger.info(f"Received save directory: {save_directory}")

        if not save_directory:
            raise ValueError("Save directory is empty")

        if not os.path.exists(save_directory):
            app.logger.info(f"Creating directory: {save_directory}")
            os.makedirs(save_directory)

        handler.folder_selected = save_directory
        handler.set_save_next_frame()
        app.logger.info("Triggered handler to save the next frame")

        # Wait for the image to be saved
        while not handler.saved_image_path:
            pass
        
        saved_image_path = os.path.join(save_directory, handler.get_latest_image_name())

        return jsonify({'message': 'Image saved', 'filename': os.path.basename(saved_image_path)}), 200
    except Exception as e:
        app.logger.exception("Failed to save image")
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/get-barcode', methods=['GET'])
def get_barcode():
    return jsonify({'barcode': globals.latest_barcode})

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
        
def connect_camera_internal(camera_type):
    target_serial = CAMERA_IDS.get(camera_type)
    factory = pylon.TlFactory.GetInstance()
    devices = factory.EnumerateDevices()

    if not devices:
        return {"error": "No cameras connected"}

    selected_device = next((device for device in devices if device.GetSerialNumber() == target_serial), None)

    if not selected_device:
        return {"error": f"Camera {camera_type} with serial {target_serial} not found"}

    if globals.cameras.get(camera_type) and globals.cameras[camera_type].IsOpen():
        return {
            "connected": True,
            "name": selected_device.GetModelName(),
            "serial": selected_device.GetSerialNumber()
        }

    globals.cameras[camera_type] = pylon.InstantCamera(factory.CreateDevice(selected_device))
    globals.cameras[camera_type].Open()

    if not globals.cameras[camera_type].IsOpen():
        return {"error": f"Camera {camera_type} failed to open"}

    camera_properties[camera_type] = get_camera_properties(globals.cameras[camera_type])
    settings_data = get_settings()
    apply_camera_settings(camera_type, globals.cameras, camera_properties, settings_data)

    return {
        "connected": True,
        "name": selected_device.GetModelName(),
        "serial": selected_device.GetSerialNumber()
    }

def start_camera_stream_internal(camera_type, scale_factor=0.25):
    app.logger.info(f"Starting {camera_type} camera stream internally with scale factor {scale_factor}")

    if camera_type not in globals.cameras or globals.cameras[camera_type] is None or not globals.cameras[camera_type].IsOpen():
        app.logger.error(f"{camera_type.capitalize()} camera is not connected or open.")
        return {"error": f"{camera_type.capitalize()} camera not connected"}

    with globals.grab_locks[camera_type]:
        if globals.stream_running.get(camera_type, False):
            app.logger.info(f"{camera_type.capitalize()} stream is already running.")
            return {"message": "Stream already running"}

        if not globals.cameras[camera_type].IsGrabbing():
            app.logger.info(f"{camera_type.capitalize()} camera starting grabbing.")
            globals.cameras[camera_type].StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

        if not globals.stream_threads.get(camera_type) or not globals.stream_threads[camera_type].is_alive():
            app.logger.info(f"Starting new thread for {camera_type}")
            globals.stream_running[camera_type] = True
        else:
            app.logger.info(f"{camera_type.capitalize()} stream thread already running.")

    return {"message": f"{camera_type.capitalize()} video stream started successfully."}
        
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
    load_settings()
    initialize_cameras()
    initialize_serial_devices()
    app.run(debug=True, use_reloader=False)