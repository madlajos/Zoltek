from flask import Flask, jsonify, request, send_from_directory, Response
from flask import Flask, render_template, send_file
from flask_cors import CORS
from flask import session, request
from glob import glob
from flask_socketio import SocketIO, emit
from PIL import Image
import io
import base64
import subprocess
import tkinter as tk
from tkinter import filedialog, Tk
import argparse
import glob
import os
import json
import datetime
import binascii
import shutil
import cv2
import logging
from logging.handlers import RotatingFileHandler
from flask_debugtoolbar import DebugToolbarExtension
import datetime


# Enable camera emulation
import os
import serial
import cv2
import numpy as np
import sys
from typing import Optional
from queue import Queue
from pypylon import pylon
from cameracontrol import set_centered_offset, validate_and_set_camera_param, get_camera_properties, parse_args, get_camera, setup_camera, Handler
import porthandler
import time
import printercontrols
import lampcontrols

app = Flask(__name__)
app.secret_key = 'TabletScanner'
logging.basicConfig(level=logging.DEBUG)
CORS(app)
app.debug = True
toolbar = DebugToolbarExtension(app)

opencv_display_format = 'BGR8'

file_path = ''
common_filenames=[]
image=[]
display=[]

CORS(app)
# Global variable to store the current frame being displayed
display = None
camera = None
streaming = False
was_streaming = False
main_camera = None
side_camera = None
camera_properties = {'main': None, 'side': None}
properties = {} # Camera properties. to be renamed
folder_selected=[]
handler = Handler('default_directory_path')
printer=[]
lamp=[]
psu=[]

SETTINGS_PATH = os.path.join(os.path.dirname(__file__), 'Angular', 'src', 'assets', 'settings.json')
with open(SETTINGS_PATH) as f:
    settings = json.load(f)

camera_params = settings['camera_params']


MAIN_CAMERA_ID = '40569959'
SIDE_CAMERA_ID = '40569958'


cameras = {
    'main': None,
    'side': None
}

CAMERA_IDS = {
    'main': MAIN_CAMERA_ID,
    'side': SIDE_CAMERA_ID
}

# Configure logging
if not app.debug:
    # Set up logging to file
    file_handler = RotatingFileHandler('flask.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)

    # Set up logging to console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    console_handler.setLevel(logging.DEBUG)
    app.logger.addHandler(console_handler)

app.logger.setLevel(logging.DEBUG)


### Serial Device Functions ###
# Define the route for checking device status
@app.route('/api/status/<device_name>', methods=['GET'])
def get_status(device_name):
    logging.debug(f"Received status request for device: {device_name}")
    device = None
    if device_name == 'psu':
        device = porthandler.psu
    elif device_name == 'lampcontroller':
        device = porthandler.lampcontroller
    elif device_name == 'printer':
        device = porthandler.printer
    else:
        logging.error("Invalid device name")
        return jsonify({'error': 'Invalid device name'}), 400

    if device is not None:
        logging.debug(f"{device_name} is connected on port {device.port}")
        return jsonify({'connected': True, 'port': device.port})
    else:
        logging.debug(f"{device_name} is not connected")
        return jsonify({'connected': False})

@app.route('/api/connect-to-<device_name>', methods=['POST'])
def connect_device(device_name):
    try:
        app.logger.info(f"Attempting to connect to {device_name}")
        device = None
        if device_name == 'psu':
            device = porthandler.connect_to_psu()
            app.logger.debug(f"PSU connection attempt result: {device}")
        elif device_name == 'lampcontroller':
            device = porthandler.connect_to_lampcontroller()
            app.logger.debug(f"Lampcontroller connection attempt result: {device}")
        elif device_name == 'printer':
            device = porthandler.connect_to_printer()
            app.logger.debug(f"Printer connection attempt result: {device}")
        else:
            app.logger.error(f"Invalid device name: {device_name}")
            return jsonify({'error': 'Invalid device name'}), 400

        if device is not None:
            # Update global state
            if device_name == 'psu':
                porthandler.psu = device
            elif device_name == 'lampcontroller':
                porthandler.lampcontroller = device
            elif device_name == 'printer':
                porthandler.printer = device

            app.logger.info(f"Successfully connected to {device_name}")
            return jsonify('ok')
        else:
            app.logger.error(f"Failed to connect to {device_name}: No COM ports or matching device not found")
            return jsonify({'error': f'Failed to connect to {device_name}. No COM ports available or matching device not found'}), 404
    except Exception as e:
        app.logger.exception(f"Exception occurred while connecting to {device_name}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/disconnect-to-<device_name>', methods=['POST'])
def disconnect_device(device_name):
    try:
        logging.info(f"Attempting to disconnect from {device_name}")
        porthandler.disconnect_device(device_name)
        logging.info(f"Successfully disconnected from {device_name}")
        return jsonify('ok')
    except Exception as e:
        logging.exception(f"Exception occurred while disconnecting from {device_name}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/check-connections', methods=['GET'])
def check_connections():
    lamp_controller_connected = porthandler.lampcontroller is not None
    psu_connected = porthandler.psu is not None
    return jsonify({
        'lampControllerConnected': lamp_controller_connected,
        'psuConnected': psu_connected
    })

### Printer Functions ###
# Function to home all axis of the printer
@app.route('/home_printer', methods=['POST'])
def home_printer():
    data = request.get_json()
    axes = data.get('axes', []) 

    printer = porthandler.get_printer()
    if printer is not None:
        try:
            printercontrols.home_axes(printer, *axes)
            return jsonify(f'Printer axes {axes if axes else ["X", "Y", "Z"]} homed successfully!')
        except Exception as e:
            return jsonify(f'An error occurred: {str(e)}'), 500
    else:
        return jsonify('Error: Printer not connected'), 500

@app.route('/get_printer_position', methods=['GET'])
def get_printer_position():
    global printer
    printer = porthandler.get_printer()

    if printer is not None:
        try:
            position = printercontrols.get_printer_position(printer)
            if position:
                return jsonify(position), 200
            else:
                return jsonify({'status': 'error', 'message': 'Failed to get printer position'}), 500
        except Exception as e:
            print(f"An error occurred: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
    else:
        print("Printer not connected")
        return jsonify({'status': 'error', 'message': 'Printer not connected'}), 404


@app.route('/disable_stepper', methods=['POST'])
def disable_stepper():
    data = request.get_json()
    axes = data.get('axes', [])

    # Check if the printer is connected without reconnecting
    printer = porthandler.get_printer()
    
    if printer is not None:
        try:
            printercontrols.disable_steppers(printer, *axes)
            return jsonify({'status': 'success', 'message': 'Printer motors disabled successfully!'}), 200
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500
    else:
        return jsonify({'status': 'error', 'message': 'Printer not connected'}), 500
    
# Function to move the printer by a given amount (relative movement)
@app.route('/move_printer_relative', methods=['POST'])
def move_printer_relative():
    data = request.get_json()
    axis = data.get('axis')
    value = data.get('value')
    
    if axis not in ['x', 'y', 'z']:
        return jsonify({'status': 'error', 'message': 'Invalid axis'}), 400

    try:
        # Check if the printer is connected without reconnecting
        printer = porthandler.get_printer()

        if printer is not None:
            # Dynamically call move_relative with the axis and value
            move_args = {axis: value}
            printercontrols.move_relative(printer, **move_args)
            return jsonify({'status': 'success'}), 200
        else:
            return jsonify({'status': 'error', 'message': 'Printer not connected'}), 404
    except Exception as e:
        return jsonify({'statuWs': 'error', 'message': str(e)}), 500
    
# Function to move the printer to a given coordinate (absolute movement)
@app.route('/move_printer_absolute', methods=['POST'])
def move_printer_absolute():
    try:
        data = request.get_json()
        logging.debug(f"Received data: {data}")
        x_pos = data.get('x')
        y_pos = data.get('y')
        z_pos = data.get('z')
        
        # Load default coordinates from the JSON file if not provided in the request
        if x_pos is None or y_pos or z_pos is None:
            logging.debug("Loading default coordinates from settings.json")
            with open(SETTINGS_PATH, 'r') as f:
                settings = json.load(f)
            x_pos = x_pos if x_pos is not None else settings['firstTabletPosition']['x']
            y_pos = y_pos if y_pos is not None else settings['firstTabletPosition']['y']
        
        logging.debug(f"Coordinates to move to: X={x_pos}, Y={y_pos}, z={z_pos}")
        
        # Check if the printer is connected without reconnecting
        printer = porthandler.get_printer()
        if printer is not None:
            logging.debug(f"Printer found: {printer}")
            # Move the printer to the specified position
            printercontrols.move_to_position(printer, x_pos, y_pos, z_pos)
            return jsonify({'status': 'success', 'message': 'Printer moved to the specified position successfully!'}), 200
        else:
            logging.error("Printer not connected")
            return jsonify({'status': 'error', 'message': 'Printer not connected'}), 404
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

### Lamp Functions ###
# Function to turn on channels of the lamp
@app.route('/api/toggle-psu', methods=['POST'])
def api_toggle_psu():
    try:
        data = request.get_json()
        state = data.get('state')
        if state is None:
            return jsonify({'error': 'State is required'}), 400
        lampcontrols.toggle_psu(state)
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/get-psu-state', methods=['GET'])
def api_get_psu_state():
    try:
        state = lampcontrols.get_psu_state()
        return jsonify({'state': state}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@app.route('/api/get-psu-readings', methods=['GET'])
def get_psu_readings():
    if porthandler.psu is not None:
        try:
            porthandler.write(porthandler.psu, "VOLTage?")
            voltage = porthandler.psu.readline().decode().strip()
            porthandler.write(porthandler.psu, "CURRent?")
            current = porthandler.psu.readline().decode().strip()
            return jsonify({'voltage': voltage, 'current': current})
        except Exception as e:
            logging.exception("Failed to get PSU readings")
            return jsonify({'voltage': '-', 'current': '-'}), 500
    else:
        return jsonify({'voltage': '-', 'current': '-'}), 200

@app.route('/api/toggle-lamp', methods=['POST'])
def toggle_lamp():
    try:
        data = request.get_json()
        channel = data.get('channel')
        on_time_ms = data.get('on_time_ms')

        if channel is None or on_time_ms is None:
            return jsonify({'error': 'Channel and on_time_ms are required'}), 400

        if not (1 <= channel <= 6):
            return jsonify({'error': 'Invalid channel number'}), 400

        lampcontrols.turn_on_channel(channel, on_time_ms)
        return jsonify({'status': 'success'}), 200

    except Exception as e:
        logging.exception(f"Exception occurred while turning on lamp channel {channel}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/get-lamp-state', methods=['GET'])
def get_lamp_state():
    if porthandler.lampcontroller is not None:
        try:
            porthandler.write(porthandler.lampcontroller, "LS?")
            state = porthandler.lampcontroller.readline().decode().strip()
            return jsonify(int(state))  # Returns -1 if no channel is active, otherwise returns the active channel number
        except Exception as e:
            logging.exception("Failed to get lamp state")
            return jsonify(-1), 500
    else:
        return jsonify(-1), 200

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
    from pypylon import pylon
    camera_type = request.args.get('type')

    if camera_type not in cameras:
        app.logger.error(f"Invalid camera type: {camera_type}")
        return jsonify({"error": "Invalid camera type specified"}), 400

    camera = cameras.get(camera_type)

    if camera is not None:
        try:
            if not camera.IsOpen():
                camera.Open()
                app.logger.info(f"{camera_type.capitalize()} camera opened.")

            if not camera.IsGrabbing():
                camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
                app.logger.info(f"{camera_type.capitalize()} camera stream started successfully.")

            return Response(generate_frames(camera_type), mimetype='multipart/x-mixed-replace; boundary=frame')

        except Exception as e:
            app.logger.error(f"Failed to start stream for {camera_type} camera: {e}")
            return jsonify({'error': f'Failed to start stream: {str(e)}'}), 500
    else:
        app.logger.error(f"{camera_type.capitalize()} camera is not connected")
        return jsonify({'error': f'{camera_type.capitalize()} camera not connected'}), 500



@app.route('/stop-video-stream', methods=['POST'])
def stop_video_stream():
    camera_type = request.args.get('type')

    if camera_type not in cameras:
        app.logger.error(f"Invalid camera type: {camera_type}")
        return jsonify({"error": "Invalid camera type specified"}), 400

    camera = cameras.get(camera_type)

    if camera and camera.IsGrabbing():
        try:
            camera.StopGrabbing()
            app.logger.info(f"{camera_type.capitalize()} camera stream stopped successfully")
            return jsonify({"message": f"{camera_type.capitalize()} camera stream stopped successfully"}), 200
        except Exception as e:
            app.logger.error(f"Failed to stop {camera_type} camera stream: {e}")
            return jsonify({"error": f"Failed to stop {camera_type} camera stream"}), 500
    else:
        app.logger.warning(f"{camera_type.capitalize()} camera is not streaming")
        return jsonify({"message": f"{camera_type.capitalize()} camera is not streaming"}), 200



def generate_frames(camera_type):
    camera = cameras.get(camera_type)

    if not camera:
        app.logger.error(f"{camera_type.capitalize()} camera is not connected")
        return

    if not camera.IsGrabbing():
        camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

    try:
        while camera.IsGrabbing():
            grab_result = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
            if grab_result.GrabSucceeded():
                image = grab_result.Array
                _, frame = cv2.imencode('.jpg', image)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame.tobytes() + b'\r\n')
            grab_result.Release()
    except Exception as e:
        app.logger.error(f"Error in {camera_type} video stream: {e}")


@app.route('/connect-camera', methods=['POST'])
def connect_camera():
    camera_type = request.args.get('type')

    if camera_type not in ['main', 'side']:
        app.logger.error(f"Invalid camera type: {camera_type}")
        return jsonify({"error": "Invalid camera type specified"}), 400

    try:
        factory = pylon.TlFactory.GetInstance()
        devices = factory.EnumerateDevices()

        if not devices:
            app.logger.error("No cameras detected.")
            return jsonify({"error": "No cameras connected"}), 400

        # Select the correct camera based on serial number
        target_serial = MAIN_CAMERA_ID if camera_type == 'main' else SIDE_CAMERA_ID
        selected_device = next((device for device in devices if device.GetSerialNumber() == target_serial), None)

        if not selected_device:
            app.logger.error(f"{camera_type.capitalize()} camera with serial {target_serial} not found.")
            return jsonify({"error": f"{camera_type.capitalize()} camera not connected"}), 400

        # Avoid reconnecting if the camera is already connected
        if cameras.get(camera_type) and cameras[camera_type].IsOpen():
            app.logger.info(f"{camera_type.capitalize()} camera is already connected.")
            return jsonify({
                "connected": True,
                "name": selected_device.GetModelName(),
                "serial": selected_device.GetSerialNumber()
            }), 200

        # Connect the selected device
        cameras[camera_type] = pylon.InstantCamera(factory.CreateDevice(selected_device))
        cameras[camera_type].Open()

        if not cameras[camera_type].IsOpen():
            app.logger.error(f"Failed to open {camera_type} camera after connection.")
            return jsonify({"error": f"{camera_type.capitalize()} camera failed to open"}), 500

        # Initialize camera properties
        camera_properties[camera_type] = get_camera_properties(cameras[camera_type])

        app.logger.info(f"{camera_type.capitalize()} camera connected successfully.")
        return jsonify({
            "connected": True,
            "name": selected_device.GetModelName(),
            "serial": selected_device.GetSerialNumber()
        }), 200

    except Exception as e:
        app.logger.error(f"Failed to connect {camera_type} camera: {e}")
        return jsonify({"error": str(e)}), 500








@app.route('/disconnect-camera', methods=['POST'])
def disconnect_camera():
    camera_type = request.args.get('type')

    if camera_type not in cameras or cameras[camera_type] is None:
        app.logger.warning(f"{camera_type.capitalize()} camera is already disconnected or not initialized")
        return jsonify({"status": "already disconnected"}), 200

    try:
        camera = cameras[camera_type]

        if camera.IsGrabbing():
            camera.StopGrabbing()

        camera.Close()
        cameras[camera_type] = None
        camera_properties[camera_type] = None

        app.logger.info(f"{camera_type.capitalize()} camera disconnected successfully")
        return jsonify({"status": "disconnected"}), 200

    except Exception as e:
        app.logger.error(f"Failed to disconnect {camera_type} camera: {e}")
        return jsonify({"error": str(e)}), 500


    
@app.route('/api/status/camera', methods=['GET'])
def check_camera_status():
    camera_type = request.args.get('type')

    if camera_type not in cameras:
        app.logger.error(f"Invalid camera type: {camera_type}")
        return jsonify({"error": "Invalid camera type specified"}), 400

    camera = cameras.get(camera_type)

    # ✅ Check if the camera is initialized and open
    if camera is not None and camera.IsOpen():
        return jsonify({"connected": True}), 200
    else:
        return jsonify({"connected": False}), 200



@app.route('/api/update-camera-settings', methods=['POST'])
def update_camera_settings():
    global cameras, camera_properties
    try:
        data = request.json
        camera_type = data.get('camera_type')
        setting_name = data.get('setting_name')
        setting_value = data.get('setting_value')

        app.logger.info(f"Received settings update: {data}")

        # Validate camera type
        if camera_type not in cameras or cameras[camera_type] is None or not cameras[camera_type].IsOpen():
            app.logger.error(f"{camera_type.capitalize()} camera is not connected or not open.")
            return jsonify({"error": f"{camera_type.capitalize()} camera is not connected"}), 400

        # Validate properties
        if camera_type not in camera_properties or not camera_properties[camera_type]:
            app.logger.error(f"{camera_type.capitalize()} camera properties not initialized.")
            return jsonify({"error": f"{camera_type.capitalize()} camera properties not found"}), 400

        # ✅ Corrected: Pass the 'properties' argument
        updated_value = validate_and_set_camera_param(
            cameras[camera_type],
            setting_name,
            setting_value,
            camera_properties[camera_type],
            camera_type  # ✅ Add this argument
        )

        app.logger.info(f"{camera_type.capitalize()} camera {setting_name} set to {updated_value}")

        return jsonify({
            "message": f"{camera_type.capitalize()} camera {setting_name} updated successfully",
            "updated_value": updated_value
        }), 200

    except Exception as e:
        app.logger.exception("Failed to update camera settings")
        return jsonify({"error": str(e)}), 500




@app.route('/api/get-camera-settings', methods=['GET'])
def get_camera_settings():
    try:
        return jsonify(camera_params)
    except Exception as e:
        app.logger.exception("Failed to get camera settings")
        return jsonify({'error': str(e)}), 500

@app.route('/video-stream', methods=['GET'])
def video_stream():
    camera_type = request.args.get('type')

    if camera_type not in cameras:
        app.logger.error(f"Invalid camera type: {camera_type}")
        return jsonify({"error": "Invalid camera type specified"}), 400

    app.logger.info(f"{camera_type.capitalize()} camera stream started successfully")
    return Response(generate_frames(camera_type), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/api/save-camera-settings', methods=['POST'])
def save_camera_settings():
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)  # Ensure the window stays on top
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        root.destroy()

        if file_path:
            settings = request.json
            with open(file_path, 'w') as f:
                json.dump(settings, f)
            return jsonify({'message': 'Settings saved successfully'}), 200
        else:
            return jsonify({'error': 'No file selected'}), 400
    except Exception as e:
        app.logger.exception("Failed to save camera settings")
        return jsonify({'error': str(e)}), 500


@app.route('/api/load-camera-settings', methods=['GET'])
def load_camera_settings():
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)  # Ensure the window stays on top
        file_path = filedialog.askopenfilename(defaultextension=".json", filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        root.destroy()

        if file_path:
            with open(file_path, 'r') as f:
                settings = json.load(f)
            settings['fileName'] = os.path.basename(file_path).replace('.json', '')
            return jsonify(settings), 200
        else:
            return jsonify({'error': 'No file selected'}), 400
    except Exception as e:
        app.logger.exception("Failed to load camera settings")
        return jsonify({'error': str(e)}), 500

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

@app.route('/images/<path:filename>')
def serve_image(filename):
    try:
        directory = handler.folder_selected
        return send_from_directory(directory, filename)
    except Exception as e:
        app.logger.exception("Failed to serve image")
        return jsonify({'error': str(e)}), 500


@app.route('/capture-image', methods=['POST'])
def connect_cap():
    global printer, handler, lamp, psu, folder_selected

    try:
        factory = pylon.TlFactory.GetInstance()
        devices = factory.EnumerateDevices()

        if not devices:
            return jsonify({'error': 'No camera detected'}), 500

        camera_id = parse_args()
        camera = get_camera(camera_id)

        handler.set_save_next_frame()  # Call set_save_next_frame method to set the flag

        return jsonify('ok')  # Return JSON response

    except Exception as e:
        logging.error(f"Failed to connect to camera: {e}")
        return jsonify({'error': 'Failed to connect to camera'}), 500


@app.route('/capture-and-send-expo', methods=['POST'])
def capture_and_send():
    global printer, handler, lamp, psu, folder_selected
    number = request.json.get('number')  # Get the exposure time from the request
    print("Exposure time received:", number)

    try:
        number = int(number)  # Convert to integer (assuming it's in microseconds)
    except (TypeError, ValueError):
        return jsonify({'error': 'Exposure time must be an integer'}), 400

    try:
        # Initialize the Basler camera system
        factory = pylon.TlFactory.GetInstance()
        devices = factory.EnumerateDevices()

        if not devices:
            return jsonify({'error': 'No Basler cameras detected'}), 500

        camera_id = parse_args()
        camera = get_camera(camera_id)
        camera.Open()

        setup_camera(camera, camera_params)
        camera.ExposureTime.SetValue(number)  # Set exposure time

        camera.Close()

        return jsonify({'success': True}), 200

    except Exception as e:
        logging.error(f"Error setting exposure time: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/get-images')
def get_images():
    global printer, handler, lamp, psu, folder_selected

    if not folder_selected:
        return jsonify({'error': 'No folder path provided'}), 400

    if not os.path.exists(folder_selected):
        return jsonify({'error': 'Folder does not exist'}), 404

    # Get all image files in the folder
    image_files = sorted(glob.glob(os.path.join(folder_selected, '*.jpg')), key=os.path.getmtime, reverse=True)
    image_files = [path.replace('\\', '/') for path in image_files]

    # Get the latest three image filenames
    out_files = image_files[0]

    return send_file(out_files, mimetype='image/jpg')

IMAGE_DIRECTORY = os.path.join(os.getcwd(), 'static')


if __name__ == '__main__':
    app.run()