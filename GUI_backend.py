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
import shutil
import cv2
import logging
from logging.handlers import RotatingFileHandler
from flask_debugtoolbar import DebugToolbarExtension


# Enable camera emulation
import os
import serial
import cv2
import numpy as np
import sys
from typing import Optional
from queue import Queue
from vmbpy import *
from cameracontrol import parse_args, get_camera, setup_camera, Handler
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

opencv_display_format = PixelFormat.Bgr8
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
folder_selected=[]
handler = Handler(folder_selected)
printer=[]
lamp=[]
psu=[]

SETTINGS_PATH = os.path.join(os.path.dirname(__file__), 'Angular', 'src', 'assets', 'settings.json')
with open(SETTINGS_PATH) as f:
    settings = json.load(f)

camera_params = settings['camera_params']


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
@app.route('/api/select-folder', methods=['GET'])
def select_folder():
    global printer, handler, lamp, psu, folder_selected
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)  # Ensure the window stays on top
    folder_selected = filedialog.askdirectory()  # Open file explorer to select a folder
    root.destroy()
    if folder_selected:
        handler = Handler(folder_selected)
        return jsonify({'folder': folder_selected})
    else:
        return jsonify({'error': 'No folder selected'})

@app.route('/video-stream')
def live_start():
    global handler, camera, streaming

    def generate_frames():
        global handler, camera, streaming
        try:
            with VmbSystem.get_instance() as vimba:
                camera_id = parse_args()
                with get_camera(camera_id) as cam:
                    setup_camera(cam, camera_params)
                    handler = Handler([])
                    cam.start_streaming(handler=handler, buffer_count=10)
                    camera = cam  # Assign the camera to the global variable
                    streaming = True
                    while True:
                        if handler:
                            display = handler.get_image()
                            if display is not None:
                                resized_frame = cv2.resize(display, (640, 480))
                                _, frame = cv2.imencode('.jpg', resized_frame)
                                yield (b'--frame\r\n'
                                       b'Content-Type: image/jpeg\r\n\r\n' + frame.tobytes() + b'\r\n')
                        else:
                            break
        except VmbSystemError as e:
            app.logger.exception("Failed to start VmbSystem")
            return

    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/connect-camera', methods=['POST'])
def connect_camera():
    global camera, handler, vimba_system_instance
    try:
        if camera is None:  # Check if camera is already connected
            # Initialize Vimba API system instance
            vimba_system_instance = VmbSystem.get_instance()
            vimba_system_instance.__enter__()  # Ensure Vimba system context is opened

            camera_id = parse_args()
            camera = get_camera(camera_id)
            camera.__enter__()  # Open the camera context using __enter__
            handler = Handler(folder_selected)
            setup_camera(camera, camera_params)
            app.logger.info("Camera connected successfully")
            return jsonify({"message": "Camera connected successfully"}), 200
        else:
            app.logger.warning("Camera is already connected")
            return jsonify({"message": "Camera is already connected"}), 200
    except Exception as e:
        app.logger.exception("Failed to connect camera")
        return jsonify({"error": str(e)}), 500

@app.route('/disconnect-camera', methods=['POST'])
def disconnect_camera():
    global camera, streaming, vimba_system_instance
    try:
        if camera is not None:
            if streaming:
                camera.stop_streaming()
                streaming = False
            camera.__exit__(None, None, None)  # Properly exit the camera context
            camera = None

            # Close the Vimba API system context if it was opened
            if vimba_system_instance:
                vimba_system_instance.__exit__(None, None, None)
                vimba_system_instance = None

            app.logger.info("Camera disconnected successfully")
            return jsonify({"message": "Camera disconnected successfully"}), 200
        else:
            app.logger.warning("No camera to disconnect")
            return jsonify({"error": "No camera to disconnect"}), 400
    except Exception as e:
        app.logger.exception("Failed to disconnect camera")
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/status/camera', methods=['GET'])
def check_camera_status():
    global camera
    try:
        if camera is not None:
            return jsonify({"connected": True}), 200
        else:
            return jsonify({"connected": False}), 200
    except Exception as e:
        app.logger.exception("Failed to check camera status")
        return jsonify({"error": str(e)}), 500

@app.route('/api/update-camera-settings', methods=['POST'])
def update_camera_settings():
    global camera, handler, streaming, vimba_system_instance, was_streaming
    try:
        setting = request.json
        app.logger.info(f"Received setting: {setting}")
        if camera:
            # Temporarily stop the streaming if it's running
            if streaming:
                camera.stop_streaming()
                streaming = False
                was_streaming = True

            try:
                # Ensure the camera context is opened if not already
                if not camera:
                    camera.__enter__()

                for key, value in setting.items():
                    if hasattr(camera, key):
                        feature = getattr(camera, key)
                        feature.set(value)
                        app.logger.info(f"Set {key} to {value}")

                # Only close the camera context if it was opened here
                if not camera:
                    camera.__exit__(None, None, None)

            except VmbError as e:
                app.logger.exception("Failed to open camera context or set feature")
                return jsonify({"error": str(e)}), 500

            # Restart the streaming if it was previously running
            if handler and was_streaming:
                camera.start_streaming(handler=handler, buffer_count=10)
                streaming = True

            return jsonify({"message": "Camera setting updated successfully"}), 200
        else:
            return jsonify({"error": "Camera not connected"}), 400
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

@app.route('/stop-video-stream', methods=['POST'])
def stop_video_stream():
    global handler, camera, streaming, was_streaming
    try:
        if camera and streaming:
            camera.stop_streaming()
            handler = None
            streaming = False
            was_streaming = False
            return jsonify({'status': 'success', 'message': 'Video stream stopped successfully!'})
        else:
            return jsonify({'status': 'error', 'message': 'No active stream to stop'}), 400
    except Exception as e:
        app.logger.exception("Failed to stop video stream")
        return jsonify({'status': 'error', 'message': str(e)}), 500

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

@app.route('/api/save-image', methods=['POST'])
def save_image():
    global save_directory
    try:
        data = request.get_json()
        save_directory = data.get('save_directory', os.path.expanduser('~\\Pictures'))
        # Logic to save the image to the specified directory
        # For demonstration purposes, we assume that the image data is in the request as base64 string
        image_data = data.get('image_data')
        if image_data:
            image_path = os.path.join(save_directory, 'captured_image.jpg')
            with open(image_path, 'wb') as f:
                f.write(base64.b64decode(image_data))
            return jsonify({'message': 'Image saved successfully', 'path': image_path}), 200
        else:
            return jsonify({'error': 'No image data provided'}), 400
    except Exception as e:
        app.logger.exception("Failed to save image")
        return jsonify({'error': str(e)}), 500


@app.route('/capture-image', methods=['POST'])
def connect_cap():
    global printer, handler, lamp, psu, folder_selected

    with VmbSystem.get_instance() as vimba:
        camera_id = parse_args()
        with get_camera(camera_id) as cam:
            handler.set_save_next_frame()  # Call set_save_next_frame method to set the flag
        return jsonify('ok')  # Return JSON response

@app.route('/capture-and-send-expo', methods=['POST'])
def capture_and_send():
    global printer, handler, lamp, psu, folder_selected
    number = request.json.get('number')  # Get the exposure time from the request
    print("Exposure time received:", number)
    try:
        number = int(number)  # Convert to integer (assuming it's in microseconds)
    except (TypeError, ValueError):
        return jsonify({'error': 'Exposure time must be an integer'})

    with VmbSystem.get_instance() as vimba:
        camera_id = parse_args()
        with get_camera(camera_id) as cam:
            setup_camera(cam)
            cam.ExposureTime.set(number)  # Set exposure time

            return jsonify({'success': True})

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

# Route to serve images
@app.route('/images/<path:last_three_images>')
def serve_image(filename):
    global printer, handler, lamp, psu, folder_selected, last_three_images

    return send_from_directory(IMAGE_DIRECTORY, filename)


if __name__ == '__main__':
    app.run()