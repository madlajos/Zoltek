from flask import Flask, jsonify, request, send_from_directory, Response
from flask import Flask, send_file
from flask_cors import CORS
from flask import request
from tkinter import filedialog, Tk
import os
import cv2
import logging
import threading
from logging.handlers import RotatingFileHandler
from flask_debugtoolbar import DebugToolbarExtension
from globals import cameras, stream_running, stream_threads, grab_locks, turntable_position
from pypylon import pylon
from cameracontrol import apply_camera_settings, set_centered_offset, validate_and_set_camera_param, get_camera_properties, parse_args, get_camera, setup_camera, Handler
import porthandler
import imageprocessing
from settings_manager import load_settings, save_settings, get_settings, set_settings

app = Flask(__name__)
app.secret_key = 'Zoltek'
logging.basicConfig(level=logging.DEBUG)
CORS(app)
app.debug = True
toolbar = DebugToolbarExtension(app)

file_path = ''
image=[]
camera = None
camera_properties = {'main': None, 'side': None}
folder_selected=[]
handler = Handler('default_directory_path')

MAIN_CAMERA_ID = '40569959'
SIDE_CAMERA_ID = '40569958'

settings_loaded = False
turntable_position = None

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
    file_handler.setLevel(app.logger)
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
def get_serial_device_status(device_name):
    logging.debug(f"Received status request for device: {device_name}")
    device = None
    if device_name == 'turntable':
        device = porthandler.turntable
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
def connect_serial_device(device_name):
    try:
        app.logger.info(f"Attempting to connect to {device_name}")
        device = None
        if device_name == 'turntable':
            device = porthandler.connect_to_turntable()
            app.logger.debug(f"Turntable connection attempt result: {device}")
        else:
            app.logger.error(f"Invalid device name: {device_name}")
            return jsonify({'error': 'Invalid device name'}), 400

        if device is not None:
            # Update global state
            if device_name == 'turntable':
                porthandler.turntable = device

            app.logger.info(f"Successfully connected to {device_name}")
            return jsonify('ok')
        else:
            app.logger.error(f"Failed to connect to {device_name}: No COM ports or matching device not found")
            return jsonify({'error': f'Failed to connect to {device_name}. No COM ports available or matching device not found'}), 404
    except Exception as e:
        app.logger.exception(f"Exception occurred while connecting to {device_name}")
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

@app.route('/api/check-connections', methods=['GET'])
def check_serial_connections():
    turntable_connected = porthandler.turntable is not None
    return jsonify({
        'turntableConnected': turntable_connected
    })
    
     

### Turntable Functions ###
@app.route('/home_turntable_with_image', methods=['POST'])
def home_turntable_with_image():
    try:
        app.logger.info("Homing process initiated.")
        camera_type = 'main'

        with grab_locks[camera_type]:
            camera = cameras.get(camera_type)

            if camera is None or not camera.IsOpen():
                app.logger.error("Main camera is not connected or open.")
                return jsonify({"error": "Main camera is not connected or open."}), 400

            # Grab a single image without stopping the stream
            grab_result = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)

            if grab_result.GrabSucceeded():
                app.logger.info("Image grabbed successfully.")
                image = grab_result.Array
                grab_result.Release()

                # Process the image
                rotation_needed = imageprocessing.home_turntable_with_image(image)
                command = f"{abs(rotation_needed)},{1 if rotation_needed > 0 else 0}"
                
                app.logger.info(f"Image processing complete. Rotation needed: {rotation_needed}")

                # Send rotation command to the turntable
                porthandler.write_turntable(command)
                app.logger.info("Rotation command sent to turntable.")

                # Set position to 0 after homing
                globals.turntable_position = 0  
                app.logger.info("Homing completed successfully.")

                return jsonify({
                    "message": "Homing successful",
                    "rotation": rotation_needed,
                    "current_position": globals.turntable_position
                })
            else:
                grab_result.Release()
                app.logger.error("Failed to grab image from camera.")
                return jsonify({"error": "Failed to grab image from camera."}), 500

    except Exception as e:
        app.logger.error(f"Exception during homing: {str(e)}")
        return jsonify({"error": str(e)}), 500

    
@app.route('/move_turntable_relative', methods=['POST'])
def move_turntable_relative():
    global turntable_position
    data = request.get_json()
    move_by = data.get('degrees')

    if move_by is None or not isinstance(move_by, (int, float)):
        return jsonify({'error': 'Invalid input, provide degrees as a number'}), 400

    direction = 'CW' if move_by > 0 else 'CCW'
    command = f"{abs(move_by)},{1 if move_by > 0 else 0}"

    try:
        porthandler.write_turntable(command)

        if turntable_position is not None:
            turntable_position = (turntable_position + move_by) % 360  # Update position only if homed
        
        return jsonify({
            'message': f'Turntable moved {move_by} degrees {direction}',
            'current_position': turntable_position if turntable_position is not None else '?'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/move_turntable_absolute', methods=['POST'])
def move_turntable_absolute():
    global turntable_position
    data = request.get_json()
    target_position = data.get('degrees')

    if target_position is None or not isinstance(target_position, (int, float)):
        return jsonify({'error': 'Invalid input, provide degrees as a number'}), 400

    # Calculate the shortest path to target position
    move_by = (target_position - turntable_position) % 360
    if move_by > 180:
        move_by -= 360  # Take the shorter path

    direction = 1 if move_by > 0 else 0
    command = f"{abs(move_by)},{direction}"

    try:
        # Send command to Arduino
        porthandler.write_turntable(command)

        #TODO: Wait for confirmation from Arduino that the rotation was successful
        # Update the global position
        turntable_position = target_position % 360

        return jsonify({'message': f'Turntable moved to {target_position} degrees {direction}',
                        'current_position': turntable_position})
    except Exception as e:
        return jsonify({'error': str(e)}), 500













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
    camera_type = request.args.get('type')
    scale_factor = float(request.args.get('scale', 0.25))

    app.logger.info(f"Received request to start {camera_type} stream with scale factor {scale_factor}")

    if camera_type not in cameras:
        app.logger.error(f"Invalid camera type: {camera_type}")
        return jsonify({"error": "Invalid camera type specified"}), 400

    camera = cameras.get(camera_type)

    if camera is None or not camera.IsOpen():
        app.logger.error(f"{camera_type.capitalize()} camera is not connected or open.")
        return jsonify({"error": f"{camera_type.capitalize()} camera not connected"}), 400

    with grab_locks[camera_type]:
        if stream_running.get(camera_type, False):
            app.logger.info(f"{camera_type.capitalize()} stream is already running.")
            return jsonify({"message": "Stream already running."}), 200

        if not camera.IsGrabbing():
            app.logger.info(f"{camera_type.capitalize()} camera starting grabbing.")
            camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

        # Start the stream if the thread isn't alive
        if not stream_threads.get(camera_type) or not stream_threads[camera_type].is_alive():
            app.logger.info(f"Starting new thread for {camera_type}")
            stream_running[camera_type] = True
            stream_threads[camera_type] = threading.Thread(target=generate_frames, args=(camera_type, scale_factor))
            stream_threads[camera_type].start()
        else:
            app.logger.info(f"{camera_type.capitalize()} stream thread already running.")

    app.logger.info(f"{camera_type.capitalize()} video stream started successfully.")
    return Response(generate_frames(camera_type, scale_factor),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

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
    camera = cameras.get(camera_type)

    if not camera:
        app.logger.error(f"{camera_type.capitalize()} camera is not connected.")
        return

    if not camera.IsGrabbing():
        app.logger.info(f"{camera_type.capitalize()} camera starting grabbing.")
        camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

    try:
        while stream_running[camera_type]:
            with grab_locks[camera_type]:
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
    finally:
        stream_running[camera_type] = False
        app.logger.info(f"{camera_type.capitalize()} camera streaming thread stopped.")


@app.route('/connect-camera', methods=['POST'])
def connect_camera():
    camera_type = request.args.get('type')

    # Check if camera type is valid before proceeding
    if camera_type not in CAMERA_IDS:
        app.logger.error(f"Invalid camera type: {camera_type}")
        return jsonify({"error": "Invalid camera type specified"}), 400

    # Assign the target serial number safely
    target_serial = CAMERA_IDS.get(camera_type)
    
    try:
        app.logger.info(f"Attempting to connect {camera_type} camera with serial {target_serial}.")
        app.logger.info(f"Cameras dictionary: {cameras}")

        factory = pylon.TlFactory.GetInstance()
        devices = factory.EnumerateDevices()

        if not devices:
            app.logger.error("No cameras detected.")
            return jsonify({"error": "No cameras connected"}), 400

        # Locate the correct camera by its serial number
        selected_device = None
        for device in devices:
            if device.GetSerialNumber() == target_serial:
                selected_device = device
                break

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

        settings_data = get_settings()
        apply_camera_settings(camera_type, cameras, camera_properties, settings_data)

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

    camera = cameras.get(camera_type, None)
    if camera and camera.IsGrabbing():
        camera.StopGrabbing()
        app.logger.info(f"{camera_type.capitalize()} camera grabbing stopped.")

    if camera and camera.IsOpen():
        camera.Close()
        app.logger.info(f"{camera_type.capitalize()} camera closed.")

    # Clean up references
    cameras[camera_type] = None
    camera_properties[camera_type] = None  # Make sure camera_properties is in scope
    app.logger.info(f"{camera_type.capitalize()} camera disconnected successfully.")

    return jsonify({"status": "disconnected"}), 200

    
@app.route('/api/status/camera', methods=['GET'])
def check_camera_status():
    camera_type = request.args.get('type')

    if camera_type not in cameras:
        app.logger.error(f"Invalid camera type: {camera_type}")
        return jsonify({"error": "Invalid camera type specified"}), 400

    camera = cameras.get(camera_type)

    if camera is not None and camera.IsOpen():
        return jsonify({"connected": True}), 200
    else:
        return jsonify({"connected": False}), 200

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
            cameras[camera_type],
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

@app.route('/video-stream', methods=['GET'])
def video_stream():
    camera_type = request.args.get('type')

    if camera_type not in cameras:
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
    

def stop_camera_stream(camera_type):
    """
    Stops the stream for the specified camera_type in Python,
    without returning a Flask response.
    Raises exceptions or returns info as needed.
    """
    if camera_type not in cameras:
        raise ValueError(f"Invalid camera type: {camera_type}")

    camera = cameras.get(camera_type)

    with grab_locks[camera_type]:
        if not stream_running.get(camera_type, False):
            # Nothing to do
            return "Stream already stopped."
        
        try:
            stream_running[camera_type] = False

            if camera and camera.IsGrabbing():
                camera.StopGrabbing()
                app.logger.info(f"{camera_type.capitalize()} camera stream stopped.")

            # If you’re also joining the thread, do it here:
            if stream_threads.get(camera_type) and stream_threads[camera_type].is_alive():
                stream_threads[camera_type].join(timeout=2)
                app.logger.info(f"{camera_type.capitalize()} stream thread joined and stopped.")

            stream_threads[camera_type] = None
            return f"{camera_type.capitalize()} stream stopped."
        except Exception as e:
            # Let the caller handle this exception or re-raise
            raise RuntimeError(f"Failed to stop {camera_type} stream: {str(e)}")

@app.before_request
def initialize_settings():
    global settings_loaded
    if not settings_loaded:
        try:
            load_settings()  # Load settings from settings.json
            app.logger.info("Settings loaded successfully.")
            settings_loaded = True  # Prevent multiple loads
        except Exception as e:
            app.logger.error(f"Failed to load settings on startup: {e}")

if __name__ == '__main__':      
    load_settings()
    app.run()

