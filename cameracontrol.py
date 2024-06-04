import cv2
import sys
from typing import Optional
from queue import Queue
from vmbpy import *

opencv_display_format = PixelFormat.Bgr8

# Library to handle Camera parameters
# Gamma is stored with a 100 multiplication
camera_params = {
    'ImageWidth': 800, 
    'ImageHeight': 400, 
    'FrameRate': 60, 
    'ExposureTime': 200, 
    'Gain': 10, 
    'Gamma': 100,
    'CenterROI_x': True,
    'CenterROI_y': True,
    'OffsetX': 320,
    'OffsetY': 900 
}

# Function to calculate nearest accepted image size to user specified value
def nearestAcceptedImgSize(user_size, dimension, camera: Camera):
    if dimension == "width":
        min_size = camera.Width.GetMin()
        max_size = camera.Width.GetMax()
        min_increment = camera.Width.GetInc()

    elif dimension == "height": 
        min_size = camera.Height.GetMin()
        max_size = camera.Height.GetMax()
        min_increment = camera.Height.GetInc()
    
    else:
        raise ValueError(f"Invalid dimension: {dimension}")

    if(user_size < min_size):
        nearest_accepted_size = min_size
    elif(user_size > max_size):
        nearest_accepted_size = max_size
    else:
        diff = user_size - min_size
        nearest_accepted_size = min_size + diff // min_increment * min_increment
    
    return nearest_accepted_size

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

def setup_camera(camera: Camera):
    with camera:
        try:
            camera.AcquisitionFrameRateEnable.set(True)
            camera.AcquisitionFrameRate.set(camera_params['FrameRate'])
            camera.ExposureTime.set(camera_params['ExposureTime'])
            camera.Gain.set(camera_params['Gain'])
            camera.Gamma.set(camera_params['Gamma'] / 100)
            camera.BalanceWhiteAuto.set('Off')
        except (AttributeError, VmbFeatureError):
            print("Error setting camera parameters")

        try:
            stream = camera.get_streams()[0]
            stream.GVSPAdjustPacketSize.run()
            while not stream.GVSPAdjustPacketSize.is_done():
                pass
        except (AttributeError, VmbFeatureError):
            pass

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
    def __init__(self):
        self.display_queue = Queue(10)

    def get_image(self):
        return self.display_queue.get(True)

    def __call__(self, cam: Camera, stream: Stream, frame: Frame):
        if frame.get_status() == FrameStatus.Complete:
            print('{} acquired {}'.format(cam, frame), flush=True)
            if frame.get_pixel_format() == opencv_display_format:
                display = frame
            else:
                display = frame.convert_pixel_format(opencv_display_format)
            self.display_queue.put(display.as_opencv_image(), True)
        cam.queue_frame(frame)

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
