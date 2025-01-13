import cv2
import sys
from typing import Optional
from queue import Queue
from pypylon import pylon
import logging
import datetime
import os
from queue import Queue, Empty  # Import Empty from queue module
import time
import requests

opencv_display_format = 'BGR8'


def abort(reason: str, return_code: int = 1, usage: bool = False):
    print(reason + '\n')
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

def get_camera(camera_id: str) -> pylon.InstantCamera:
    factory = pylon.TlFactory.GetInstance()
    devices = factory.EnumerateDevices()

    if not devices:
        raise ValueError('No cameras connected.')

    logging.info("Connected devices:")
    for device in devices:
        logging.info(f"Device Model: {device.GetModelName()}, Serial Number: {device.GetSerialNumber()}")

    # Search for the requested camera ID
    for device in devices:
        if device.GetSerialNumber() == camera_id:
            try:
                camera = pylon.InstantCamera(factory.CreateDevice(device))
                camera.Open()
                return camera
            except Exception as e:
                logging.error(f"Failed to open camera {camera_id}: {e}")
                raise ValueError(f"Failed to open Camera '{camera_id}'.")

    raise ValueError(f"Failed to access Camera '{camera_id}'. Available devices: {[device.GetSerialNumber() for device in devices]}")

    

def setup_camera(camera: pylon.InstantCamera, camera_params: dict):
    camera.Open()
    try:
        camera.Width.SetValue(round(camera_params['Width']))
        logging.info(f"Set Image Width to {round(camera_params['Width'])}")

        camera.Height.SetValue(round(camera_params['Height']))
        logging.info(f"Set Image Height to {round(camera_params['Height'])}")

        camera.AcquisitionFrameRateEnable.SetValue(True)
        camera.AcquisitionFrameRate.SetValue(round(camera_params['FrameRate']))
        logging.info(f"Set AcquisitionFrameRate to {round(camera_params['FrameRate'])}")

        camera.ExposureTime.SetValue(round(camera_params['ExposureTime']))
        logging.info(f"Set ExposureTime to {round(camera_params['ExposureTime'])}")

        camera.Gain.SetValue(round(camera_params['Gain']))
        logging.info(f"Set Gain to {round(camera_params['Gain'])}")

    except Exception as e:
        logging.error(f"Error setting camera parameters: {e}")


def setup_pixel_format(camera: pylon.InstantCamera):
    if camera.PixelFormat.GetValue() != opencv_display_format:
        camera.PixelFormat.SetValue(opencv_display_format)
        
def start_streaming(camera: pylon.InstantCamera):
    handler = Handler()
    try:
        camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
        while camera.IsGrabbing():
            grab_result = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
            if grab_result.GrabSucceeded():
                image = grab_result.Array
                cv2.imshow("Stream", image)
                if cv2.waitKey(1) == 13:  # Enter key
                    break
                handler.save_frame(image)
            grab_result.Release()
    finally:
        camera.StopGrabbing()
        camera.Close()
        
def stop_streaming(camera: pylon.InstantCamera):
    if camera.IsGrabbing():
        camera.StopGrabbing()
        logging.info(f"Stopped streaming for camera: {camera.GetDeviceInfo().GetSerialNumber()}")
    else:
        logging.info(f"Camera {camera.GetDeviceInfo().GetSerialNumber()} is not currently streaming.")

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
        frame_np = frame.as_opencv_image()
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        filename = os.path.join(self.folder_selected, f"IMG_{timestamp}.jpg")
        cv2.imwrite(filename, frame_np)
        self.saved_image_path = f"IMG_{timestamp}.jpg"
        print("Image saved as:", filename)

    def __call__(self, cam: pylon.InstantCamera, stream, frame: pylon.GrabResult):
        if frame.GrabSucceeded():
            print('{} acquired {}'.format(cam, frame), flush=True)
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

def get_camera_properties(camera: pylon.InstantCamera) -> dict:
    properties = {}
    try:
        properties['Width'] = {'min': camera.Width.GetMin(), 'max': camera.Width.GetMax(), 'inc': camera.Width.GetInc()}
        properties['Height'] = {'min': camera.Height.GetMin(), 'max': camera.Height.GetMax(), 'inc': camera.Height.GetInc()}
        properties['OffsetX'] = {'min': camera.OffsetX.GetMin(), 'max': camera.OffsetX.GetMax(), 'inc': camera.OffsetX.GetInc()}
        properties['OffsetY'] = {'min': camera.OffsetY.GetMin(), 'max': camera.OffsetY.GetMax(), 'inc': camera.OffsetY.GetInc()}
        properties['ExposureTime'] = {'min': camera.ExposureTime.GetMin(), 'max': camera.ExposureTime.GetMax(), 'inc': camera.ExposureTime.GetInc()}
        properties['Gain'] = {'min': camera.Gain.GetMin(), 'max': camera.Gain.GetMax(), 'inc': None}
        if hasattr(camera, 'Gamma'):
            properties['Gamma'] = {'min': camera.Gamma.GetMin(), 'max': camera.Gamma.GetMax(), 'inc': None}
        properties['FrameRate'] = {'min': camera.AcquisitionFrameRate.GetMin(), 'max': camera.AcquisitionFrameRate.GetMax(), 'inc': 0.01}
    except Exception as e:
        logging.error(f"Error getting camera properties: {e}")
    return properties


def validate_param(param_name: str, param_value: float, properties: dict) -> float:
    param_value = float(param_value)  # Ensure param_value is a float
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

def validate_and_set_camera_param(camera, param_name: str, param_value: float, properties: dict, camera_type: str):
    valid_value = validate_param(param_name, param_value, properties)

    try:
        was_streaming = camera.IsGrabbing()

        # ✅ Stop the stream ONLY for Width or Height changes
        if param_name in ['Width', 'Height'] and was_streaming:
            stop_streaming(camera)
            logging.info(f"{camera_type.capitalize()} stream stopped to apply {param_name} change.")
            time.sleep(0.5)  # ✅ Short delay to ensure proper stop

        # ✅ Ensure the camera is open before applying any setting
        if not camera.IsOpen():
            camera.Open()
            logging.info(f"{camera_type.capitalize()} camera opened to apply {param_name}.")

        # ✅ Apply the setting based on the parameter name
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

        logging.info(f"Set {param_name} to {valid_value}")

        # ✅ Restart the stream ONLY if it was stopped
        if param_name in ['Width', 'Height'] and was_streaming:
            start_streaming(camera)
            logging.info(f"{camera_type.capitalize()} stream resumed after applying {param_name} change.")

    except Exception as e:
        logging.error(f"Failed to set {param_name} for {camera_type} camera: {e}")

    return valid_value



# ✅ Notify frontend about stream status
def notify_stream_status(camera_type: str, is_streaming: bool):
    try:
        response = requests.post(f'http://localhost:4200/api/stream-status', json={
            'camera_type': camera_type,
            'is_streaming': is_streaming
        })
        if response.status_code == 200:
            logging.info(f"Stream status for {camera_type} updated to {is_streaming}")
        else:
            logging.warning(f"Failed to update stream status for {camera_type}")
    except Exception as e:
        logging.error(f"Error notifying frontend about stream status: {e}")

def set_centered_offset(camera: pylon.InstantCamera):
    properties = get_camera_properties(camera)
    sensor_width = camera.SensorWidth.get()
    sensor_height = camera.SensorHeight.get()
    width = camera.Width.get()
    height = camera.Height.get()

    centered_x = (sensor_width - width) // 2
    centered_y = (sensor_height - height) // 2

    validate_and_set_camera_param(camera, 'OffsetX', centered_x, properties)
    validate_and_set_camera_param(camera, 'OffsetY', centered_y, properties)

    return {'OffsetX': centered_x, 'OffsetY': centered_y}