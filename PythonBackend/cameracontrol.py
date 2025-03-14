import cv2
import sys
from typing import Optional
from queue import Queue, Empty
from pypylon import pylon
import logging
import datetime
import os
import time
import requests
import threading

from globals import app, stream_running, stream_threads, cameras
from logger_config import CameraError

opencv_display_format = 'BGR8'

def abort(reason: str, return_code: int = 1, usage: bool = False):
    app.logger.error(reason)
    sys.exit(return_code)

def parse_args() -> Optional[str]:
    args = sys.argv[1:]
    argc = len(args)

    for arg in args:
        if arg in ('/h', '-h'):
            sys.exit(0)

    if argc > 1:
        abort(reason="Invalid number of arguments. Abort.", return_code=2, usage=True)

    return None if argc == 0 else args[0]

# Function to continuously generate and send frames
def stream_video(camera_type):
    camera = cameras.get(camera_type)
    if not camera or not camera.IsOpen():
        app.logger.error(f"{camera_type.capitalize()} camera is not open.")
        return

    app.logger.info(f"{camera_type.capitalize()} camera streaming thread started.")
    stream_running[camera_type] = True

    try:
        while stream_running[camera_type]:
            try:
                grab_result = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
            except Exception as e:
                app.logger.error(f"Failed to retrieve result for {camera_type} camera: {e}")
                continue

            if grab_result.GrabSucceeded():
                image = grab_result.Array  # No scaling applied here; scaling may be done downstream.
                # Encode image to JPEG
                success, frame = cv2.imencode('.jpg', image)
                if not success:
                    app.logger.error(f"Failed to encode frame for {camera_type} camera.")
                    grab_result.Release()
                    continue
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame.tobytes() + b'\r\n')
            grab_result.Release()
    except Exception as e:
        app.logger.error(f"Error in {camera_type} video stream: {e}")
    finally:
        stream_running[camera_type] = False
        app.logger.info(f"{camera_type.capitalize()} camera streaming thread stopped.")
        
def get_camera(camera_id: str) -> pylon.InstantCamera:
    factory = pylon.TlFactory.GetInstance()
    devices = factory.EnumerateDevices()

    app.logger.info("Connected devices:")
    for device in devices:
        app.logger.info(f"Device Model: {device.GetModelName()}, Serial Number: {device.GetSerialNumber()}")

    # Search for the requested camera ID
    for device in devices:
        if device.GetSerialNumber() == camera_id:
            try:
                camera = pylon.InstantCamera(factory.CreateDevice(device))
                camera.Open()
                if not camera.IsOpen():
                    raise CameraError(f"Camera '{camera_id}' failed to open after creation.")
                return camera
            except Exception as e:
                app.logger.error(f"Failed to open camera {camera_id}: {e}")
                raise CameraError(f"Failed to open Camera '{camera_id}'.") from e

    raise CameraError(f"Failed to access Camera '{camera_id}'. Available devices: " +
                      f"{[device.GetSerialNumber() for device in devices]}")

def setup_camera(camera: pylon.InstantCamera, camera_params: dict):
    try:
        # It is usually not necessary to call camera.Open() here if already open
        # But if needed, check and open:
        if not camera.IsOpen():
            camera.Open()

        camera.Width.SetValue(round(camera_params['Width']))
        app.logger.info(f"Set Image Width to {round(camera_params['Width'])}")

        camera.Height.SetValue(round(camera_params['Height']))
        app.logger.info(f"Set Image Height to {round(camera_params['Height'])}")

        camera.AcquisitionFrameRateEnable.SetValue(True)
        camera.AcquisitionFrameRate.SetValue(round(camera_params['FrameRate']))
        app.logger.info(f"Set AcquisitionFrameRate to {round(camera_params['FrameRate'])}")

        camera.ExposureTime.SetValue(round(camera_params['ExposureTime']))
        app.logger.info(f"Set ExposureTime to {round(camera_params['ExposureTime'])}")

        camera.Gain.SetValue(round(camera_params['Gain']))
        app.logger.info(f"Set Gain to {round(camera_params['Gain'])}")

    except Exception as e:
        app.logger.error(f"Error setting camera parameters: {e}")
        raise CameraError("Error setting camera parameters.") from e


def setup_pixel_format(camera: pylon.InstantCamera):
    try:
        if camera.PixelFormat.GetValue() != opencv_display_format:
            camera.PixelFormat.SetValue(opencv_display_format)
    except Exception as e:
        app.logger.error(f"Error setting pixel format: {e}")
        raise CameraError("Failed to set pixel format.") from e
        
def start_streaming(camera: pylon.InstantCamera):
    handler = Handler()
    try:
        camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
        while camera.IsGrabbing():
            grab_result = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
            if grab_result.GrabSucceeded():
                image = grab_result.Array
                cv2.imshow("Stream", image)
                if cv2.waitKey(1) == 13:  # Enter key to exit streaming loop
                    break
                handler.save_frame(grab_result)  # Pass grab_result or image based on implementation
            grab_result.Release()
    except Exception as e:
        app.logger.error(f"Error during streaming: {e}")
        raise CameraError("Streaming error encountered.") from e
    finally:
        try:
            camera.StopGrabbing()
            camera.Close()
        except Exception as e:
            app.logger.error(f"Error stopping streaming: {e}")
        
def stop_streaming(camera: pylon.InstantCamera):
    try:
        if camera.IsGrabbing():
            camera.StopGrabbing()
            app.logger.info(f"Stopped streaming for camera: {camera.GetDeviceInfo().GetSerialNumber()}")
        else:
            app.logger.info(f"Camera {camera.GetDeviceInfo().GetSerialNumber()} is not currently streaming.")
    except Exception as e:
        app.logger.error(f"Error stopping streaming for camera: {e}")
        raise CameraError("Failed to stop streaming.") from e

class Handler:
    def __init__(self, folder_selected):
        self.display_queue = Queue(10)
        self.save_next_frame = False
        self.folder_selected = folder_selected
        self.saved_image_path = None

    def get_image(self):
        try:
            return self.display_queue.get(timeout=1)
        except Empty: 
            return None

    def set_save_next_frame(self):
        self.save_next_frame = True

    def get_latest_image_name(self):
        return self.saved_image_path

    def save_frame(self, frame):
        try:
            # If frame is a GrabResult, convert it to an OpenCV image.
            # You might need to check if frame has an 'Array' attribute.
            if hasattr(frame, 'Array'):
                frame_np = frame.Array
            else:
                frame_np = frame
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            filename = os.path.join(self.folder_selected, f"IMG_{timestamp}.jpg")
            cv2.imwrite(filename, frame_np)
            self.saved_image_path = f"IMG_{timestamp}.jpg"
            app.logger.info(f"Image saved as: {filename}")
        except Exception as e:
            app.logger.error(f"Error saving frame: {e}")
            # Optionally, raise an exception if saving the image is critical.
            raise

    def __call__(self, cam: pylon.InstantCamera, stream, frame: pylon.GrabResult):
        try:
            if frame.GrabSucceeded():
                app.logger.debug(f"{cam} acquired frame.")
                if frame.get_pixel_format() == opencv_display_format:
                    display = frame
                else:
                    display = frame.convert_pixel_format(opencv_display_format)
                self.display_queue.put(display.as_opencv_image(), True)

                if self.save_next_frame:
                    self.save_frame(frame)
                    self.save_next_frame = False

                cam.queue_frame(frame)
                return frame
        except Exception as e:
            app.logger.error(f"Handler error: {e}")
            raise

def get_camera_properties(camera: pylon.InstantCamera) -> dict:
    properties = {}
    try:
        properties['Width'] = {
            'min': camera.Width.GetMin(), 
            'max': camera.Width.GetMax(), 
            'inc': camera.Width.GetInc()
        }
        properties['Height'] = {
            'min': camera.Height.GetMin(), 
            'max': camera.Height.GetMax(), 
            'inc': camera.Height.GetInc()
        }
        properties['OffsetX'] = {
            'min': camera.OffsetX.GetMin(), 
            'max': camera.OffsetX.GetMax(), 
            'inc': camera.OffsetX.GetInc()
        }
        properties['OffsetY'] = {
            'min': camera.OffsetY.GetMin(), 
            'max': camera.OffsetY.GetMax(), 
            'inc': camera.OffsetY.GetInc()
        }
        properties['ExposureTime'] = {
            'min': camera.ExposureTime.GetMin(), 
            'max': camera.ExposureTime.GetMax(), 
            'inc': camera.ExposureTime.GetInc()
        }
        properties['Gain'] = {
            'min': camera.Gain.GetMin(), 
            'max': camera.Gain.GetMax(), 
            'inc': None
        }
        if hasattr(camera, 'Gamma'):
            properties['Gamma'] = {
                'min': camera.Gamma.GetMin(), 
                'max': camera.Gamma.GetMax(), 
                'inc': None
            }
        properties['FrameRate'] = {
            'min': camera.AcquisitionFrameRate.GetMin(), 
            'max': camera.AcquisitionFrameRate.GetMax(), 
            'inc': 0.01
        }
    except Exception as e:
        app.logger.error(f"Error getting camera properties: {e}")
        # Optionally, re-raise as CameraError if these properties are critical.
    return properties

def validate_param(param_name: str, param_value: float, properties: dict) -> float:
    try:
        param_value = float(param_value)  # Ensure param_value is a float
    except Exception as e:
        raise ValueError(f"Invalid parameter value for {param_name}: {e}")
    
    prop = properties.get(param_name)
    if prop:
        min_value = prop['min']
        max_value = prop['max']
        increment = prop['inc']
        if increment is None:
            increment = 1
        if param_value < min_value:
            return round(min_value, 3)
        elif param_value > max_value:
            return round(max_value, 3)
        else:
            diff = param_value - min_value
            return round(min_value + round(diff / increment) * increment, 3)
    else:
        raise KeyError(f"Property '{param_name}' not found in camera properties.")
    
def apply_camera_settings(camera_type, cameras, camera_properties, settings):
    app.logger.info(f"Loaded settings in apply_camera_settings: {settings}")

    camera_settings = settings.get('camera_params', {}).get(camera_type, {})

    if not camera_settings:
        app.logger.warning(f"No settings found for {camera_type} in apply_camera_settings. Check the settings.json structure.")
        return

    app.logger.info(f"Applying settings to {camera_type}: {camera_settings}")

    camera = cameras.get(camera_type)
    if camera and camera.IsOpen():
        try:
            for setting_name, setting_value in camera_settings.items():
                app.logger.info(f"Setting {setting_name} = {setting_value} on {camera_type} camera")
                validate_and_set_camera_param(
                    camera,
                    setting_name,
                    setting_value,
                    camera_properties[camera_type],
                    camera_type                  
                )
            app.logger.info(f"{camera_type.capitalize()} camera settings applied successfully.")
        except Exception as e:
            app.logger.error(f"Failed to apply settings to {camera_type} camera: {e}")
            raise CameraError(f"Error applying settings to {camera_type} camera.") from e
    else:
        app.logger.warning(f"{camera_type.capitalize()} camera is not open. Cannot apply settings.")

def validate_and_set_camera_param(camera, param_name: str, param_value: float, properties: dict, camera_type: str):
    valid_value = validate_param(param_name, param_value, properties)
    try:
        was_streaming = stream_running[camera_type] 
        if param_name in ['Width', 'Height'] and was_streaming:
            stream_running[camera_type] = False
            if camera.IsGrabbing():
                camera.StopGrabbing()
                app.logger.info(f"{camera_type.capitalize()} stream stopped to apply {param_name} change.")
            if stream_threads.get(camera_type) and stream_threads[camera_type].is_alive():
                stream_threads[camera_type].join(timeout=2)
                app.logger.info(f"{camera_type.capitalize()} stream thread joined.")
            stream_threads[camera_type] = None
            time.sleep(0.5)  # Short pause to ensure the camera is ready

        if not camera.IsOpen():
            camera.Open()
            app.logger.info(f"{camera_type.capitalize()} camera reopened to apply {param_name}.")

        if param_name == 'Width':
            camera.Width.SetValue(valid_value)
        elif param_name == 'Height':
            camera.Height.SetValue(valid_value)
        elif param_name == 'OffsetX':
            camera.OffsetX.SetValue(valid_value)
        elif param_name == 'OffsetY':
            camera.OffsetY.SetValue(valid_value)
        elif param_name == 'ExposureTime':
            camera.ExposureTime.SetValue(valid_value)
        elif param_name == 'FrameRate':
            camera.AcquisitionFrameRateEnable.SetValue(True)
            camera.AcquisitionFrameRate.SetValue(valid_value)
        elif param_name == 'Gain':
            camera.Gain.SetValue(valid_value)
        elif param_name == 'Gamma':
            camera.Gamma.SetValue(valid_value)
        
        camera.ReverseX.SetValue(True)
        camera.ReverseY.SetValue(True)

        app.logger.info(f"{camera_type.capitalize()} camera {param_name} set to {valid_value}")

        if param_name in ['Width', 'Height'] and was_streaming:
            stream_running[camera_type] = True
            stream_threads[camera_type] = threading.Thread(target=stream_video, args=(camera_type, 1.0))
            stream_threads[camera_type].start()
            app.logger.info(f"🔄 {camera_type.capitalize()} stream restarted after {param_name} change.")

    except Exception as e:
        app.logger.error(f"Failed to set {param_name} for {camera_type} camera: {e}")
        raise CameraError(f"Error setting {param_name} for {camera_type} camera.") from e

    return valid_value

def notify_stream_status(camera_type: str, is_streaming: bool):
    try:
        response = requests.post(f'http://localhost:4200/api/stream-status', json={
            'camera_type': camera_type,
            'is_streaming': is_streaming
        })
        if response.status_code == 200:
            app.logger.info(f"Stream status for {camera_type} updated to {is_streaming}")
        else:
            app.logger.warning(f"Failed to update stream status for {camera_type}: {response.status_code}")
    except Exception as e:
        app.logger.error(f"Error notifying frontend about stream status: {e}")