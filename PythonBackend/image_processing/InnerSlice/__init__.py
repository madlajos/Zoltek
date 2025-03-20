import os


from .iTempMatchPolygon import islice_template_match_with_polygon
from .iDetDots import islice_detect_small_dots_and_contours




__all__ = [
    "islice_template_match_with_polygon", "islice_detect_small_dots_and_contours"
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
