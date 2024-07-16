import cv2
import sys
from typing import Optional
from queue import Queue
from vmbpy import *
import logging
import datetime
import os
from queue import Queue, Empty  # Import Empty from queue module

opencv_display_format = PixelFormat.Bgr8

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

def get_camera(camera_id: Optional[str]) -> Camera:
    with VmbSystem.get_instance() as vmb:
        if camera_id:
            try:
                return vmb.get_camera_by_id(camera_id)
            except VmbCameraError:
                raise ValueError(f"Failed to access Camera '{camera_id}'.")
        else:
            cams = vmb.get_all_cameras()
            if not cams:
                raise ValueError('No Cameras accessible.')
            return cams[0]

def setup_camera(camera: Camera, camera_params: dict):
    with camera:
        try:
            camera.Width.set(round(camera_params['Width'], 3))
            logging.info(f"Set Image Width to {round(camera_params['Width'], 3)}")
            
            camera.Height.set(round(camera_params['Height'], 3))
            logging.info(f"Set Image Height to {round(camera_params['Height'], 3)}")
            
            camera.AcquisitionFrameRateEnable.set(True)
            camera.AcquisitionFrameRate.set(round(camera_params['FrameRate'], 3))
            logging.info(f"Set AcquisitionFrameRate to {round(camera_params['FrameRate'], 3)}")

            camera.ExposureTime.set(round(camera_params['ExposureTime'], 3))
            logging.info(f"Set ExposureTime to {round(camera_params['ExposureTime'], 3)}")

            camera.Gain.set(round(camera_params['Gain'], 3))
            logging.info(f"Set Gain to {round(camera_params['Gain'], 3)}")

            camera.Gamma.set(round(camera_params['Gamma'], 3))
            logging.info(f"Set Gamma to {round(camera_params['Gamma'], 3)}")
        except AttributeError as ae:
            logging.error(f"AttributeError setting camera parameters: {ae}")
        except VmbFeatureError as vfe:
            logging.error(f"VmbFeatureError setting camera parameters: {vfe}")


def setup_pixel_format(cam: Camera):
    cam_formats = cam.get_pixel_formats()
    cam_color_formats = intersect_pixel_formats(cam_formats, COLOR_PIXEL_FORMATS)
    convertible_color_formats = tuple(f for f in cam_color_formats
                                      if opencv_display_format in f.get_convertible_formats())
    cam_mono_formats = intersect_pixel_formats(cam_formats, MONO_PIXEL_FORMATS)
    convertible_mono_formats = tuple(f for f in cam_mono_formats
                                     if opencv_display_format in f.get_convertible_formats())
    if opencv_display_format in cam_formats:
        cam.set_pixel_format(opencv_display_format)
    elif convertible_color_formats:
        cam.set_pixel_format(convertible_color_formats[0])
    elif convertible_mono_formats:
        cam.set_pixel_format(convertible_mono_formats[0])
    else:
        raise ValueError('Camera does not support an OpenCV compatible format.')

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

    def __call__(self, cam: Camera, stream: Stream, frame: Frame):
        if frame.get_status() == FrameStatus.Complete:
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

        
def start_streaming(camera: Camera):
    setup_camera(camera)
    setup_pixel_format(camera)
    handler = Handler()
    try:
        camera.start_streaming(handler=handler, buffer_count=1)
        msg = 'Stream from \'{}\'. Press <Enter> to stop stream.'
        ENTER_KEY_CODE = 13
        while True:
            key = cv2.waitKey(1)
            if key == ENTER_KEY_CODE:
                cv2.destroyWindow(msg.format(camera.get_name()))
                break
            display = handler.get_image()
            cv2.imshow(msg.format(camera.get_name()), display)
    finally:
        camera.stop_streaming()
        

def get_camera_properties(camera: Camera) -> dict:
    properties = {}
    try:
        properties['Width'] = {'min': camera.Width.get_range()[0], 'max': camera.Width.get_range()[1], 'inc': camera.Width.get_increment()}
        properties['Height'] = {'min': camera.Height.get_range()[0], 'max': camera.Height.get_range()[1], 'inc': camera.Height.get_increment()}
        properties['OffsetX'] = {'min': camera.OffsetX.get_range()[0], 'max': camera.OffsetX.get_range()[1], 'inc': camera.OffsetX.get_increment()}
        properties['OffsetY'] = {'min': camera.OffsetY.get_range()[0], 'max': camera.OffsetY.get_range()[1], 'inc': camera.OffsetY.get_increment()}
        properties['ExposureTime'] = {'min': camera.ExposureTime.get_range()[0], 'max': camera.ExposureTime.get_range()[1], 'inc': camera.ExposureTime.get_increment()}
        properties['Gain'] = {'min': camera.Gain.get_range()[0], 'max': camera.Gain.get_range()[1], 'inc': camera.Gain.get_increment()}
        properties['Gamma'] = {'min': camera.Gamma.get_range()[0], 'max': camera.Gamma.get_range()[1], 'inc': camera.Gamma.get_increment()}
        properties['FrameRate'] = {'min': camera.AcquisitionFrameRate.get_range()[0], 'max': camera.AcquisitionFrameRate.get_range()[1], 'inc': 0.01}
    except VmbFeatureError as vfe:
        logging.error(f"VmbFeatureError getting camera properties: {vfe}")
    return properties

def validate_param(param_name: str, param_value: int, properties: dict) -> float:
    prop = properties.get(param_name)
    if prop:
        min_value = prop['min']
        max_value = prop['max']
        increment = prop.get('inc', 1)
        if param_value < min_value:
            return round(min_value, 3)
        elif param_value > max_value:
            return round(max_value, 3)
        else:
            diff = param_value - min_value
            return round(min_value + round(diff / increment) * increment, 3)
    else:
        raise KeyError(f"Property '{param_name}' not found in camera properties.")

def validate_and_set_camera_param(camera: Camera, param_name: str, param_value: int, properties: dict):
    valid_value = validate_param(param_name, param_value, properties)
    with camera:
        try:
            if param_name == 'Width':
                camera.Width.set(valid_value)
            elif param_name == 'Height':
                camera.Height.set(valid_value)
            elif param_name == 'OffsetX':
                camera.OffsetX.set(valid_value)
            elif param_name == 'OffsetY':
                camera.OffsetY.set(valid_value)
            elif param_name == 'ExposureTime':
                camera.ExposureTime.set(valid_value)
            elif param_name == 'FrameRate':
                camera.AcquisitionFrameRateEnable.set(True)
                camera.AcquisitionFrameRate.set(valid_value)
            elif param_name == 'Gain':
                camera.Gain.set(valid_value)
            elif param_name == 'Gamma':
                camera.Gamma.set(valid_value)
            logging.info(f"Set {param_name} to {valid_value}")
        except AttributeError as ae:
            logging.error(f"AttributeError setting camera parameter {param_name}: {ae}")
        except VmbFeatureError as vfe:
            logging.error(f"VmbFeatureError setting camera parameter {param_name}: {vfe}")