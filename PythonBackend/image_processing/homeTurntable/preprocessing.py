import cv2
import numpy as np
from GeneralProc.logger import logger
import globals


def preprocess(image, scale_percent):
    """Resize the image for faster processing.
        Input: Grayscale image
        Output: Scaled image"""


    try:
        image=cv2.resize(image, None, fx=scale_percent / 100, fy=scale_percent / 100, interpolation=cv2.INTER_AREA)
        return image, None
    except cv2.error as e:
        logger.error("E2011")
        return None, "E2011"



def rotate_image(image, angle):
    """Rotate an image by a given angle around its center.
        Input: Scaled Grayscale image, angle of rotation
        Output: Rotated image"""
    try:
        center = (image.shape[1] // 2, image.shape[0] // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1)
        return cv2.warpAffine(image, rotation_matrix, (image.shape[1], image.shape[0]))
    except:
        return None


def crop_second_two_thirds(image):
    print(globals.x_end)
    try:
        cropped_image = image[:, :globals.x_end]
        return cropped_image, None
    except:
        return None, "E2211"


import cv2
import numpy as np
from GeneralProc import logger

def fill_second_two_thirds(image_full, template_full, scale=0.25):
    """
    Matches template in a downscaled image, then maps result back to original size.

    Parameters:
        image_full (np.ndarray): Original high-res image (grayscale or BGR).
        template_full (np.ndarray): Template to match inside the image.
        scale (float): Downscale factor (e.g. 0.25 = 25% size).

    Returns:
        np.ndarray or None: Cropped, masked result.
        str or None: Error code if an error occurs.
    """
    try:
        # Downscale inputs
        small_image = cv2.resize(image_full, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        small_template = cv2.resize(template_full, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

        result = cv2.matchTemplate(small_image, small_template, cv2.TM_CCOEFF_NORMED)
        _, _, _, small_top_left = cv2.minMaxLoc(result)
    except cv2.error:
        logger.error("E2011 - Template matching failed.")
        return None, "E2011"

    # Convert coords back to original scale
    top_left_x = int(round(small_top_left[0] / scale))
    top_left_y = int(round(small_top_left[1] / scale))

    # Clamp to image bounds
    h_img, w_img = image_full.shape[:2]
    h_temp, w_temp = template_full.shape[:2]

    top_left_x = max(0, min(top_left_x, w_img - 1))
    top_left_y = max(0, min(top_left_y, h_img - 1))

    bottom_right_x = min(top_left_x + w_temp, w_img)
    bottom_right_y = min(top_left_y + h_temp, h_img)

    # Sanity check region
    if (bottom_right_x - top_left_x <= 0) or (bottom_right_y - top_left_y <= 0):
        logger.error("E2012 - Invalid mask region.")
        return None, "E2012"

    # Create and apply mask
    mask_layer = np.zeros_like(image_full, dtype=np.uint8)
    try:
        mask_layer[top_left_y:bottom_right_y, top_left_x:bottom_right_x] = template_full
        masked_image = cv2.bitwise_and(image_full, image_full, mask=mask_layer)
    except cv2.error:
        logger.error("E2013 - Mask application failed.")
        return None, "E2013"

    # Convert to grayscale if needed
    if len(masked_image.shape) == 3:
        gray_image = cv2.cvtColor(masked_image, cv2.COLOR_BGR2GRAY)
    else:
        gray_image = masked_image

    # Detect non-black areas for cropping
    col_sums = np.sum(gray_image, axis=0)
    row_sums = np.sum(gray_image, axis=1)
    non_black_cols = np.where(col_sums > 0)[0]
    non_black_rows = np.where(row_sums > 0)[0]

    if len(non_black_cols) == 0 or len(non_black_rows) == 0:
        logger.error("E2014 - No content found after masking.")
        return None, "E2014"

    first_col, last_col = non_black_cols[0], non_black_cols[-1]
    first_row, last_row = non_black_rows[0], non_black_rows[-1]

    cropped_image = masked_image[first_row:last_row + 1, first_col:last_col + 1]
    return cropped_image, None



