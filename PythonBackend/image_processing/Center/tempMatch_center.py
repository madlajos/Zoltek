import cv2
import numpy as np
import globals
from GeneralProc import *

def center_template_match_and_extract(template, image):

    scale_factor = 10 / 100.0
    try:
        small_image = cv2.resize(image, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_AREA)
        small_template = cv2.resize(template, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_AREA)
    except cv2.error as e:
        logger.error("E2111")
        return None, "E2111"

    try:
        result = cv2.matchTemplate(small_image, small_template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, small_top_left = cv2.minMaxLoc(result)
    except cv2.error as e:
        logger.error("E2112")
        return None, "E2112"

    top_left_x = round(small_top_left[0] / scale_factor)
    top_left_y = round(small_top_left[1] / scale_factor)
    top_left = (top_left_x, top_left_y)

    # 4️⃣ **Apply correction adjustments (scaled)**
    adjustment1 = 4  # Scale correction to original resolution
    adjustment2 = 3

    corrected_top_left = (top_left[0] + adjustment1, top_left[1] + adjustment2)
    corrected_bottom_right = (corrected_top_left[0] + template.shape[1], corrected_top_left[1] + template.shape[0])

    # Create a blank mask of the same size as the cropped image
    mask_layer = np.zeros_like(image, dtype=np.uint8)
    mask_layer[corrected_top_left[1]:corrected_bottom_right[1],
    corrected_top_left[0]:corrected_bottom_right[0]] = template

    nonzero_coords = np.column_stack(np.where((mask_layer) > 0))  # Get all nonzero pixel coordinates
    if len(nonzero_coords) == 0:
        logger.error("E2113")
        return None, "E2113"
    if len(nonzero_coords) > 0:
        globals.x_end = int(np.min(nonzero_coords[:, 1]))
        try:
        # Write updated x_end back to globals.py
            with open("globals.py", "r") as file:
                lines = file.readlines()

            with open("globals.py", "w") as file:
                for line in lines:
                    if line.startswith("x_end"):
                        file.write(f"x_end = {globals.x_end}\n")  # Update it
                    else:
                        file.write(line)  # Keep other lines unchanged
        except IOError as e:
                logger.error("E2114")
                return None, "E2114"
        print("Updated x_end in globals.py:", globals.x_end)

    # Apply the mask on the cropped image using bitwise operation
    try:
        masked_image = cv2.bitwise_and(image, image, mask=mask_layer)
    except cv2.error as e:
        logger.error("E2115")
        return None, "E2115"

    return masked_image, None