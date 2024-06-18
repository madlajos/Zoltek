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
import vim_test

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

opencv_display_format = PixelFormat.Bgr8
app = Flask(__name__)
file_path = ''
common_filenames=[]
image=[]
display=[]
app.secret_key = 'TabletScanner'
CORS(app)
# Global variable to store the current frame being displayed
display = None
folder_selected=[]
handler = Handler(folder_selected)
printer=[]
lamp=[]
psu=[]

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


# Define the route for capturing an image
@app.route('/connect-to-psu', methods=['POST'])
def connect_psu():
    global printer, handler, lamp, psu, folder_selected
    psu = porthandler.connect_to_psu()
    if psu is not None:
        # Store the original printer object
        psu_data = str(psu)
        print(psu_data)  # Print for debugging purposes
        return jsonify('ok')  # Return JSON response
    else:
        return jsonify({'error': 'Failed to connect to printer'}), 500  # Return error response if printer is not connected


@app.route('/connect-to-lamp', methods=['POST'])
def connect_lamp():
    global printer, handler, lamp, psu, folder_selected
    lamp = porthandler.connect_to_lampcontroller()
    time.sleep(1)
    if lamp is not None:
        # Store the original printer object
        lamp_data = str(lamp)
        print(lamp_data)  # Print for debugging purposes

        return jsonify('ok')  # Return JSON response
    else:
        return jsonify({'error': 'Failed to connect to printer'}), 500  # Return error response if printer is not connected


@app.route('/connect-to-lamp2', methods=['POST'])
def connect_lamp2():
    global printer, handler, lamp, psu, folder_selected

    if lamp is not None:
        # Store the original printer object
        lamp_data = str(lamp)
        print(lamp_data)  # Print for debugging purposes
        porthandler.write(lamp, (1,5000))
        return jsonify('ok')  # Return JSON response
    else:
        return jsonify({'error': 'Failed to connect to printer'}), 500  # Return error response if printer is not connected





# Define the route for capturing an image
@app.route('/connect-to-printer', methods=['POST'])
def connect_print():
    global printer, handler, lamp, psu, folder_selected
    time.sleep(1)
    global printer, handler, lamp
    printer = porthandler.connect_to_printer()
    if printer is not None:
        # Store the original printer object
        printer_data = str(printer)
        print(printer_data)  # Print for debugging purposes
        return jsonify('ok')  # Return JSON response
    else:
        return jsonify({'error': 'Failed to connect to printer'}), 500  # Return error response if printer is not connected


@app.route('/printer_home', methods=['POST'])
def printer_home():
    global printer, handler, lamp, psu, folder_selected




    print(str(printer))  # Print the serial object
    time.sleep(1)
    if printer is not None:
        printercontrols.home_axes(printer,'Z')
        return jsonify('Printer axes homed successfully!')
    else:
        return jsonify('Error')






@app.route('/printer_move1', methods=['POST'])
def printer_movez_1():
    global printer, handler, lamp, psu, folder_selected
    with VmbSystem.get_instance() as vimba:
        camera_id = parse_args()
        with get_camera(camera_id) as cam:

            handler = handler   # Use the current handler if available
            cam.start_streaming(handler=handler, buffer_count=10)
            while True:
                    # Retrieve the current frame from the handler
                display = handler.get_image()
                resized_frame = cv2.resize(display, (640, 480))
                _, frame = cv2.imencode('.jpg', resized_frame)
                yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame.tobytes() + b'\r\n')



        if printer is not None:

            printercontrols.move_relative(printer, y=0.1)
        return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
@app.route('/printer_move2', methods=['POST'])
def printer_movez_2():
    global printer, handler, lamp, psu, folder_selected
    if printer is not None:

        printercontrols.move_relative(printer, y=1)
        return 'Printer axes homed successfully!'
    else:
        return 'Failed to connect to printer'

@app.route('/printer_move3', methods=['POST'])
def printer_movez_3():
    global printer, handler, lamp, psu, folder_selected
    if printer is not None:

        printercontrols.move_relative(printer, y=10)
        return 'Printer axes homed successfully!'
    else:
        return 'Failed to connect to printer'

@app.route('/printer_move4', methods=['POST'])
def printer_movez_4():
    global printer, handler, lamp, psu, folder_selected
    with VmbSystem.get_instance() as vimba:
        camera_id = parse_args()
        with get_camera(camera_id) as cam:

            handler = handler  # Use the current handler if available
            cam.start_streaming(handler=handler, buffer_count=10)
            while True:
                # Retrieve the current frame from the handler
                display = handler.get_image()
                resized_frame = cv2.resize(display, (640, 640))
                _, frame = cv2.imencode('.jpg', resized_frame)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame.tobytes() + b'\r\n')

        if printer is not None:
            printercontrols.move_relative(printer, x=0.1)
        return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/printer_move5', methods=['POST'])
def printer_movez_5():
    global printer, handler, lamp, psu, folder_selected
    if printer is not None:

        printercontrols.move_relative(printer, x=1)
        return 'Printer axes homed successfully!'
    else:
        return 'Failed to connect to printer'

@app.route('/printer_move6', methods=['POST'])
def printer_movez_6():
    global printer, handler, lamp, psu, folder_selected
    if printer is not None:

        printercontrols.move_relative(printer, x=10)
        return 'Printer axes homed successfully!'
    else:
        return 'Failed to connect to printer'

@app.route('/printer_move7', methods=['POST'])
def printer_movez_7():
    global printer, handler, lamp, psu, folder_selected
    with VmbSystem.get_instance() as vimba:
        camera_id = parse_args()
        with get_camera(camera_id) as cam:

            handler = handler  # Use the current handler if available
            cam.start_streaming(handler=handler, buffer_count=10)
            while True:
                # Retrieve the current frame from the handler
                display = handler.get_image()
                resized_frame = cv2.resize(display, (640, 640))
                _, frame = cv2.imencode('.jpg', resized_frame)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame.tobytes() + b'\r\n')

        if printer is not None:
            printercontrols.move_relative(printer, y=-0.1)
        return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/printer_move8', methods=['POST'])
def printer_movez_8():
    global printer, handler, lamp, psu, folder_selected
    if printer is not None:

        printercontrols.move_relative(printer, y=-1)
        return 'Printer axes homed successfully!'
    else:
        return 'Failed to connect to printer'

@app.route('/printer_move9', methods=['POST'])
def printer_movez_9():
    global printer, handler, lamp, psu, folder_selected
    if printer is not None:

        printercontrols.move_relative(printer, y=-10)
        return 'Printer axes homed successfully!'
    else:
        return 'Failed to connect to printer'


@app.route('/printer_move10', methods=['POST'])
def printer_movez_10():
    global printer, handler, lamp, psu, folder_selected
    with VmbSystem.get_instance() as vimba:
        camera_id = parse_args()
        with get_camera(camera_id) as cam:

            handler = handler  # Use the current handler if available
            cam.start_streaming(handler=handler, buffer_count=10)
            while True:
                # Retrieve the current frame from the handler
                display = handler.get_image()
                resized_frame = cv2.resize(display, (640, 640))
                _, frame = cv2.imencode('.jpg', resized_frame)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame.tobytes() + b'\r\n')

        if printer is not None:
            printercontrols.move_relative(printer, x=-0.1)
        return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/printer_move11', methods=['POST'])
def printer_movez_11():
    global printer, handler, lamp, psu, folder_selected
    if printer is not None:

        printercontrols.move_relative(printer, x=-1)
        return 'Printer axes homed successfully!'
    else:
        return 'Failed to connect to printer'

@app.route('/printer_move12', methods=['POST'])
def printer_movez_12():
    global printer, handler, lamp, psu, folder_selected
    if printer is not None:

        printercontrols.move_relative(printer, x=-10)
        return 'Printer axes homed successfully!'
    else:
        return 'Failed to connect to printer'


@app.route('/printer_move13', methods=['POST'])
def printer_movez_13():
    global printer, handler, lamp, psu, folder_selected
    with VmbSystem.get_instance() as vimba:
        camera_id = parse_args()
        with get_camera(camera_id) as cam:

            handler = handler  # Use the current handler if available
            cam.start_streaming(handler=handler, buffer_count=10)
            while True:
                # Retrieve the current frame from the handler
                display = handler.get_image()
                resized_frame = cv2.resize(display, (640, 640))
                _, frame = cv2.imencode('.jpg', resized_frame)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame.tobytes() + b'\r\n')

        if printer is not None:
            printercontrols.move_relative(printer, z=-0.1)
        return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/printer_move14', methods=['POST'])
def printer_movez_14():
    global printer, handler, lamp, psu, folder_selected
    if printer is not None:

        printercontrols.move_relative(printer, z=-1)
        return 'Printer axes homed successfully!'
    else:
        return 'Failed to connect to printer'



@app.route('/printer_move15', methods=['POST'])
def printer_movez_15():
    global printer, handler, lamp, psu, folder_selected
    if printer is not None:

        printercontrols.move_relative(printer, z=-10)
        return 'Printer axes homed successfully!'
    else:
        return 'Failed to connect to printer'


@app.route('/printer_move16', methods=['POST'])
def printer_movez_16():
    global printer, handler, lamp, psu, folder_selected
    with VmbSystem.get_instance() as vimba:
        camera_id = parse_args()
        with get_camera(camera_id) as cam:

            handler = handler  # Use the current handler if available
            cam.start_streaming(handler=handler, buffer_count=10)
            while True:
                # Retrieve the current frame from the handler
                display = handler.get_image()
                resized_frame = cv2.resize(display, (640, 640))
                _, frame = cv2.imencode('.jpg', resized_frame)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame.tobytes() + b'\r\n')

        if printer is not None:
            printercontrols.move_relative(printer, z=0.1)
        return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/printer_move17', methods=['POST'])
def printer_movez_17():
    global printer, handler, lamp, psu, folder_selected
    if printer is not None:

        printercontrols.move_relative(printer, z=1)
        return 'Printer axes homed successfully!'
    else:
        return 'Failed to connect to printer'

@app.route('/printer_move18', methods=['POST'])
def printer_movez_18():
    global printer, handler, lamp, psu, folder_selected
    if printer is not None:

        printercontrols.move_relative(printer, z=10)
        return 'Printer axes homed successfully!'
    else:
        return 'Failed to connect to printer'

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