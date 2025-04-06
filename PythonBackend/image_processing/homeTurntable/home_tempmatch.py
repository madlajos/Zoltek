import math
import os
import numpy as np
import cv2
from GeneralProc import logger  # Assuming you already have this in your codebase
from homeTurntable import *
from concurrent.futures import ThreadPoolExecutor


# Rotate the template and store versions
def rotate_image(image, angle):
    center = (image.shape[1] // 2, image.shape[0] // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1)

    return cv2.warpAffine(image, rotation_matrix, (image.shape[1], image.shape[0]))


def find_best_match_for_angle(angle, cropped_region, template_small):
    """
    Helper function to compute the correlation score for a given angle.
    """
    rotated = rotate_image(cropped_region, angle)
    correlation = cv2.matchTemplate(rotated, template_small, cv2.TM_CCOEFF_NORMED).max()
    return angle, correlation


def find_best_match_and_angle(target_to_match, template_small):
    result = cv2.matchTemplate(target_to_match, template_small, cv2.TM_CCOEFF_NORMED)
    _, _, _, max_loc = cv2.minMaxLoc(result)
    h, w = template_small.shape
    top_left = max_loc
    
    padding = 0.25  # 25% extra around the match region

    pad_h = int(h * padding)
    pad_w = int(w * padding)

    start_y = max(0, top_left[1] - pad_h)
    end_y = min(target_to_match.shape[0], top_left[1] + h + pad_h)
    start_x = max(0, top_left[0] - pad_w)
    end_x = min(target_to_match.shape[1], top_left[0] + w + pad_w)

    cropped_region = target_to_match[start_y:end_y, start_x:end_x]

    def parallel_search(angle_list):
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(
                executor.map(lambda angle: find_best_match_for_angle(angle, cropped_region, template_small),
                             angle_list))
        return results

        # Coarse search (fast, wide scan)

    coarse_angles = np.arange(-180, 180, 1)
    coarse_results = parallel_search(coarse_angles)
    best_coarse_angle, best_score = max(coarse_results, key=lambda x: x[1])

    # Fine search (slow, focused scan)
    fine_range = 5  # degrees around the best coarse match
    fine_angles = np.arange(best_coarse_angle - fine_range, best_coarse_angle + fine_range, 0.1)
    fine_results = parallel_search(fine_angles)
    best_fine_angle, best_fine_score = max(fine_results, key=lambda x: x[1])
    # Ambiguity check: Are 2 peaks near 90° apart and similar in score?

    return best_fine_angle, best_fine_score


def find_best_match_and_angle2(image, template):
    result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
    _, _, _, max_loc = cv2.minMaxLoc(result)
    h, w = template.shape
    top_left = max_loc
    cropped_region = image[top_left[1]:top_left[1] + h, top_left[0]:top_left[0] + w]

    def parallel_search(angle_list):
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(
                executor.map(lambda angle: find_best_match_for_angle(angle, cropped_region, template),
                             angle_list))
        return results

        # Coarse search (fast, wide scan)

    coarse_angles = np.arange(-180, 180, 1)
    coarse_results = parallel_search(coarse_angles)
    best_coarse_angle, best_score = max(coarse_results, key=lambda x: x[1])

    # Fine search (slow, focused scan)
    fine_range = 10  # degrees around the best coarse match
    fine_angles = np.arange(best_coarse_angle - fine_range, best_coarse_angle + fine_range, 0.1)
    fine_results = parallel_search(fine_angles)
    best_fine_angle, best_fine_score = max(fine_results, key=lambda x: x[1])
    # Ambiguity check: Are 2 peaks near 90° apart and similar in score?

    return best_fine_angle, best_fine_score

    # Track the best match across all templates

def start_temp_match(templateL, templateS, image, scale_percent):
    try:
        best_angle = None
        best_score = -float('inf')
        best_rotation = 0

        rotated_templatesL = {
            0: templateL,
            90: rotate_image(templateL, 90),
            180: rotate_image(templateL, 180),
            270: rotate_image(templateL, 270),
        }

        for rotation, template_variant in rotated_templatesL.items():
            if template_variant is None:
                logger.error(f"E2022 - Failed to rotate templateL at {rotation}°")
                continue
            angle, score = find_best_match_and_angle(image, template_variant)
            if isinstance(score, str):  # An error code was returned
                continue
            if score > best_score:
                best_score = score
                best_angle = angle
                best_rotation = rotation

        print(best_score)

        # def preprocess(img, scale_percent):
        #     return cv2.resize(img, None, fx=scale_percent / 100, fy=scale_percent / 100, interpolation=cv2.INTER_AREA)

        # if best_score < 0.44:
        #     print('ok')
        #     rotated_templatesS = {
        #         0: preprocess(templateS, scale_percent),
        #         90: preprocess(rotate_image(templateS, 90), scale_percent),
        #         180: preprocess(rotate_image(templateS, 180), scale_percent),
        #         270: preprocess(rotate_image(templateS, 270), scale_percent),
        #     }
        #
        #     for rotation, template_variant2 in rotated_templatesS.items():
        #         if template_variant2 is None:
        #             logger.error(f"E2023 - Failed to rotate templateS at {rotation}°")
        #             continue
        #         angle, score = find_best_match_and_angle2(image, template_variant2)
        #         if isinstance(score, str):  # An error code was returned
        #             continue
        #         if score > best_score:
        #             best_score = score
        #             best_angle = angle
        #             best_rotation = rotation
        #
        #     print(" Score too low — retrying fine search with small template")
        #     print(f"New score with small template: {best_score:.3f}")
        #

        return best_angle, best_rotation,best_score, None

    except Exception as e:
        logger.error("E2024 - Error in start_temp_match")
        return None, None, "E2024"


