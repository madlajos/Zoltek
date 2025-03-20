import cv2
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from GeneralProc import logger  # Ensure centralized logging is used
from homeTurntable.preprocessing import *

def find_best_match_for_angle(angle, cropped_region, template_small):
    """Find best matching rotation using numpy-based operations.
       Returns (angle, max_match_score) or (None, -1) if an error occurs.
    """

    # 1️⃣ Validate Inputs
    if cropped_region is None or template_small is None:
        logger.error("E2016")
        return None, ("E2016")  # Invalid result


    try:
        # 2️⃣ Rotate Image
        rotated = rotate_image(cropped_region, angle)
        if rotated is None:
            logger.error("E2017")
            return None, "E2017"

        # 3️⃣ Perform Template Matching
        match_score = cv2.matchTemplate(rotated, template_small, cv2.TM_CCOEFF_NORMED).max()
        return angle, match_score

    except cv2.error as e:
        logger.error("E2018")
        return None, "E2018"

    except Exception as e:
        logger.error("E2019")
        return None, "E2019"






def find_best_match_and_angle(target_to_match, template_small):
    """Optimized function with hierarchical search (10° → 1° → 0.1°).
       Returns (best_angle, best_score) or (None, -1) if an error occurs.
    """

    # 1️⃣ Validate Inputs
    if target_to_match is None or template_small is None:
        logger.error("E2014")
        return None, "E2014"

    if target_to_match.size == 0 or template_small.size == 0:
        logger.error("E2015")
        return None, -1

    try:
        result = cv2.matchTemplate(target_to_match, template_small, cv2.TM_CCOEFF_NORMED)
        _, _, _, max_loc = cv2.minMaxLoc(result)
        h, w = template_small.shape
        top_left = max_loc
        cropped_region = target_to_match[top_left[1]:top_left[1] + h, top_left[0]:top_left[0] + w]

        # Parallelize the rotation matching
        angles = np.arange(-180, 180, 0.1)
        best_angle = 0
        best_score = -float('inf')

        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(
                executor.map(lambda angle: find_best_match_for_angle(angle, cropped_region, template_small), angles))

        # Find the best angle and score
        for angle, score in results:
            if score > best_score:
                best_score = score
                best_angle = angle

        return best_angle, best_score


    except cv2.error as e:
        logger.error("E2024")



