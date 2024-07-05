import cv2
import sys
from typing import Optional
from queue import Queue
from vmbpy import *
import logging
from queue import Queue, Empty  # Import Empty from queue module

opencv_display_format = PixelFormat.Bgr8

def abort(reason: str, return_code: int = 1, usage: bool = False):
    print(reason + '\n')
    if usage:
        print_usage()
    sys.exit(return_code)

def parse_args() -> Optional[str]:
    args = sys.argv[1:]
    argc = len(args)

    for arg in args:
        if arg in ('/h', '-h'):
            print_usage()
            sys.exit(0)

    if argc > 1:
        abort(reason="Invalid number of arguments. Abort.", return_code=2, usage=True)

    return None if argc == 0 else args[0]

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

def setup_camera(camera: Camera, camera_params: dict):
    with camera:
        try:
            camera.AcquisitionFrameRateEnable.set(True)
            camera.AcquisitionFrameRate.set(camera_params['FrameRate'])
            logging.info(f"Set AcquisitionFrameRate to {camera_params['FrameRate']}")

            camera.ExposureTime.set(camera_params['ExposureTime'])
            logging.info(f"Set ExposureTime to {camera_params['ExposureTime']}")

            camera.Gain.set(camera_params['Gain'])
            logging.info(f"Set Gain to {camera_params['Gain']}")

            camera.Gamma.set(camera_params['Gamma'] / 100)
            logging.info(f"Set Gamma to {camera_params['Gamma'] / 100}")
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
        self.save_next_frame = False  # Flag to save the next frame
        self.folder_selected = folder_selected

    def get_image(self):
        try:
            return self.display_queue.get(timeout=1)  # Added timeout to prevent blocking
        except Empty: 
            return None

    def set_save_next_frame(self):
        self.save_next_frame = True

    def save_frame(self, frame):
        frame_np = frame.as_opencv_image()
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        filename = os.path.join(self.folder_selected, f"image_from_stream_{timestamp}.jpg")
        cv2.imwrite(filename, frame_np)
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
