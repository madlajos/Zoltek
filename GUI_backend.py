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
from cameracontrol import parse_args
from cameracontrol import get_camera
from cameracontrol import setup_camera, Handler
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
folder_selected=[]
handler = Handler(folder_selected)
printer=[]
lamp=[]
psu=[]


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


### Printer Functions ###
# Function to home all axis of the printer
@app.route('/home_printer', methods=['POST'])
def home_printer():
    global printer, handler, lamp, psu, folder_selected
    print(str(printer))  # Print the serial object
    time.sleep(1)
    if printer is not None:
        printercontrols.home_axes(printer)
        return jsonify('Printer axes homed successfully!')
    else:
        return jsonify('Error')

# Function to move the printer by a given amount (relative movement)
@app.route('/move_printer', methods=['POST'])
def move_printer():
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
        return jsonify({'status': 'error', 'message': str(e)}), 500





# Define the route for starting the video stream
@app.route('/select-folder', methods=['GET'])
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
    global printer, handler, lamp, psu, folder_selected

    def generate_frames():
        global printer, handler, lamp, psu, folder_selected

        with VmbSystem.get_instance() as vimba:
            camera_id = parse_args()
            with get_camera(camera_id) as cam:
                setup_camera(cam)
                handler = handler   # Use the current handler if available
                cam.start_streaming(handler=handler, buffer_count=10)
                while True:
                    # Retrieve the current frame from the handler
                    display = handler.get_image()
                    resized_frame = cv2.resize(display, (640, 640))
                    _, frame = cv2.imencode('.jpg', resized_frame)
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame.tobytes() + b'\r\n')

    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


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



@app.route('/turn-on-lamp', methods=['POST'])
def illu_on():
    global printer, handler, lamp, psu, folder_selected

    channel = request.json.get('channel')  # Get the channel number from the request

    if psu and lamp is not None:
        lampcontrols.turn_on_channel(psu,lamp, 1, 10000)
        time.sleep(3)
        return 'Printer axes homed successfully!'
    else:
        return 'Failed to connect to printer'


@app.route('/turn-on-lampUV1', methods=['POST'])
def illu_on1():
    global printer, handler, lamp, psu, folder_selected
    channel = request.json.get('channel')  # Get the channel number from the request
    if psu and lamp is not None:
        lampcontrols.turn_on_channel(psu,lamp, 2, 5000)
        time.sleep(3)
        return 'Lamp turned on successfully!'

    else:
        return 'Failed to connect to printer'

@app.route('/turn-on-lampUV2', methods=['POST'])
def illu_on2():
    global printer, handler, lamp, psu, folder_selected
    channel = request.json.get('channel')  # Get the channel number from the request
    if psu and lamp is not None:
        lampcontrols.turn_on_channel(psu,lamp, 3, 1000)
        time.sleep(3)
        return 'Lamp turned on successfully!'

    else:
        return 'Failed to connect to printer'

@app.route('/turn-on-lampUV3', methods=['POST'])
def illu_on3():
    global printer, handler, lamp, psu, folder_selected
    channel = request.json.get('channel')  # Get the channel number from the request
    if psu and lamp is not None:
        lampcontrols.turn_on_channel(psu,lamp, 4, 1000)
        time.sleep(3)
        return 'Lamp turned on successfully!'

    else:
        return 'Failed to connect to printer'


@app.route('/turn-on-lampUV4', methods=['POST'])
def illu_on4():
    global printer, handler, lamp, psu, folder_selected
    channel = request.json.get('channel')  # Get the channel number from the request
    if psu and lamp is not None:
        lampcontrols.turn_on_channel(psu,lamp, 5, 1000)
        time.sleep(3)
        return 'Lamp turned on successfully!'

    else:
        return 'Failed to connect to printer'

@app.route('/turn-on-lampUV5', methods=['POST'])
def illu_on5():
    global printer, handler, lamp, psu, folder_selected
    channel = request.json.get('channel')  # Get the channel number from the request
    if psu and lamp is not None:
        lampcontrols.turn_on_channel(psu,lamp, 6, 1000)
        time.sleep(3)
        return 'Lamp turned on successfully!'

    else:
        return 'Failed to connect to printer'

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