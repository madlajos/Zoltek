import os
import sys

# Ensure the parent directory is in the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import modules from homeTurntable

from .preprocessing import preprocess, rotate_image, crop_second_two_thirds
from .home_tempmatch import find_best_match_and_angle, find_best_match_for_angle
from .angle_detect import angle_det

# Import from GeneralProc
from GeneralProc.load_templ import load_template

# Define what gets imported when calling `from homeTurntable import *`
__all__ = [
    "preprocess", "rotate_image",
    "find_best_match_and_angle", "find_best_match_for_angle", "angle_det",
    "crop_second_two_thirds"
]

# Set base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))