import cv2
import numpy as np
#from GeneralProc.logger import logger
from GeneralProc.config import app_state
import math


def preprocess(image, scale_percent):
    """Resize the image for faster processing.
        Input: Grayscale image
        Output: Scaled image"""
    try:
        image=cv2.resize(image, None, fx=scale_percent / 100, fy=scale_percent / 100, interpolation=cv2.INTER_AREA)
        return image, None
    except cv2.error as e:
#        logger.error("E2011")
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
    """Crop an image.
        Input: Scaled Grayscale image
        Output: Cropped image"""
    print(app_state.x_end)
    try:
        cropped_image = image[:, :app_state.x_end]
        return cropped_image, None
    except Exception as e:
        # Optionally log the error message with details
        # logger.error(f"E2211: Cropping failed - {str(e)}")
          return None, "E2211"


def fill_second_two_thirds(image, template,best_angle, padding_ratio=0.25):

    scale_factor = 10 / 100.0
    try:
        small_image = cv2.resize(image, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_AREA)
        small_template = cv2.resize(template, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_AREA)
    except cv2.error as e:
        #logger.error("E2013")
        return None, None, None, "E2013"

    try:
        result = cv2.matchTemplate(small_image, small_template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, small_top_left = cv2.minMaxLoc(result)
    except cv2.error as e:
        #logger.error("E2014")
        return None, None, None, "E2014"

    top_left_x = round(small_top_left[0] / scale_factor)
    top_left_y = round(small_top_left[1] / scale_factor)

    # Apply correction adjustments (if needed)
    adjustment1 = 4
    adjustment2 = 3
    corrected_top_left = (top_left_x + adjustment1, top_left_y + adjustment2)

    # Template size
    temp_h, temp_w = template.shape[:2]

    # Compute center of matched region (without padding)
    template_center_x = corrected_top_left[0] + temp_w // 2
    template_center_y = corrected_top_left[1] + temp_h // 2

    # Compute padding in pixels
    pad_x = int(temp_w * padding_ratio)
    pad_y = int(temp_h * padding_ratio)

    # Expand region with padding, clamped to image dimensions
    img_h, img_w = image.shape[:2]
    x1 = max(0, corrected_top_left[0] - pad_x)
    y1 = max(0, corrected_top_left[1] - pad_y)
    x2 = min(img_w, corrected_top_left[0] + temp_w + pad_x)
    y2 = min(img_h, corrected_top_left[1] + temp_h + pad_y)

    # Create blank mask
    mask_layer = np.zeros(image.shape[:2], dtype=np.uint8)
    mask_layer[y1:y2, x1:x2] = 255  # Apply white square to mask

    nonzero_coords = np.column_stack(np.where(mask_layer > 0))
    if len(nonzero_coords) == 0:
        #logger.error("E2015")
        return None, None, None, "E2015"

    # Apply the mask
    try:
        masked_image = cv2.bitwise_and(image, image, mask=mask_layer)
        # Crop to the padded region
        masked_image = masked_image[y1:y2, x1:x2]
        analysis_gray = masked_image.copy()
        # Adjust center point to cropped image coordinates
        center_x_local = template_center_x - x1
        center_y_local = template_center_y - y1
        # Convert to color image if needed for drawing
        if len(masked_image.shape) == 2:
            masked_image = cv2.cvtColor(masked_image, cv2.COLOR_GRAY2BGR)

        # Draw the center point

    except cv2.error as e:
        #logger.error("E2016")
        return None, None, None, "E2016"

    # Angle in degrees and convert to radians
    angle_deg = best_angle
    angle_rad = math.radians(angle_deg)

    # Direction vector
    dx = math.cos(angle_rad)
    dy = math.sin(angle_rad)

    # Line length (adjust as needed)
    line_len = 2000

    # Compute endpoints from the center
    x1_line = int(center_x_local - dx * line_len)
    y1_line = int(center_y_local - dy * line_len)
    x2_line = int(center_x_local + dx * line_len)
    y2_line = int(center_y_local + dy * line_len)

    # Draw the line through the center
    cv2.line(masked_image, (x1_line, y1_line), (x2_line, y2_line), (0, 255, 255), 10)

    # # # Create a blank mask same size as the cropped image
    # cv2.circle(masked_image, (center_x_local, center_y_local), 5, (0, 0, 255), -1)  # red dot
    # cv2.imshow("img2", cv2.resize(masked_image, None, fx=0.2, fy=0.2, interpolation=cv2.INTER_AREA))

    try:
        # Create the line mask
        crop_h, crop_w = masked_image.shape[:2]
        line_thickness_ratio = 0.03
        line_thickness = int(crop_h * line_thickness_ratio)

        line_mask = np.zeros(masked_image.shape[:2], dtype=np.uint8)
        cv2.line(line_mask, (x1_line, y1_line), (x2_line, y2_line), 255, line_thickness)

        # Apply the line mask
        line_only_image = cv2.bitwise_and(masked_image, masked_image, mask=line_mask)
        # cv2.imshow("RotatedImage", cv2.resize(masked_image, None, fx=0.2, fy=0.2, interpolation=cv2.INTER_AREA))
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()
        # Detect dots
        gray_line = cv2.cvtColor(line_only_image, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray_line, 100, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        dot_count = 0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if 5 < area < 500:
                dot_count += 1

        result = "A" if dot_count > 0 else "B"
        print(f"Sample TYPE: {result} (Found: {dot_count})")
        # --- work on NON-padded inner ROI (template window) ---
        inner = analysis_gray[pad_y:pad_y + temp_h, pad_x:pad_x + temp_w].copy()

        cx_in = center_x_local - pad_x
        cy_in = center_y_local - pad_y

        h, w = inner.shape[:2]
        Y, X = np.ogrid[:h, :w]
        R = np.sqrt((X - cx_in) ** 2 + (Y - cy_in) ** 2)

        r_template = 0.35 * min(temp_w, temp_h)
        circle_mask = (R <= r_template).astype(np.uint8) * 255

        analysis_in_circle = cv2.bitwise_and(inner, inner, mask=circle_mask)
        cv2.circle( analysis_in_circle, (center_x_local, center_y_local), 5, (0, 0, 255), -1)  # red dot
        # cv2.imshow("img", cv2.resize( analysis_in_circle, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA))
        # cv2.waitKey(0)
        # dots inside the template-defined circle
        _, bw = cv2.threshold(analysis_in_circle, 10, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        cnts, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        areas = np.array([cv2.contourArea(c) for c in cnts], np.float32)
        areas = areas[areas > 0]
        lo, hi = np.percentile(areas, [10, 90]) if areas.size else (0, 0)

        nx, ny = -dy, dx
        hits = 0
        for c in cnts:
            a = cv2.contourArea(c)
            if areas.size and not (lo <= a <= hi):
                continue
            (px, py), r = cv2.minEnclosingCircle(c)
            # NOTE: dot coords are in INNER ROI coords now, line uses center in INNER coords too
            d = abs((px - cx_in) * nx + (py - cy_in) * ny)
            if d < r:
                hits += 1

        print("Line-dot hits (template circle, no padding):", hits)
        # if hits > 0:
        #     return None, None, "E2502"
    except cv2.error as e:
        #logger.error("E2017")
        return None, None, None, "E2017"
    except Exception as e:
        #logger.error("E2018")
        return None, None, "E2018"

    return masked_image, result, hits, None