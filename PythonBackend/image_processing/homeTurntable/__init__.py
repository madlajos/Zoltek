import os
import sys

# Ensure the parent directory is in the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import modules from homeTurntable

from .preprocessing import preprocess, rotate_image, crop_second_two_thirds, fill_second_two_thirds
from .home_tempmatch import det_dot_home, det_angle
# Import from GeneralProc
from GeneralProc.load_templ import load_template

# Define what gets imported when calling `from homeTurntable import *`
__all__ = [
    "preprocess", "rotate_image",
    "crop_second_two_thirds", "fill_second_two_thirds", "det_dot_home", "det_angle"
]

# Set base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
