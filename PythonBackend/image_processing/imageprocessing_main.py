import cv2
import numpy as np
from .homeTurntable import *
from .GeneralProc import *
from .Center import *
from .InnerSlice import *
from .OuterSlice import *

DRAW_CENTER_DOTS = False
DRAW_INNER_DOTS = False
DRAW_OUTER_DOTS = False

def home_turntable_with_image(image):
    """
        Home the turntable and return the best alignment angle.
        Input: Grayscale image - Center camera
        Output: Adjusted angle for rotation
        ErrorCode: "E20xx"
    """
    last_valid_image = image.copy()

    # Filenames and constant values:
    templateL_name = 'TempHomeL.jpg'
    templateS_name = 'TempHomeS.jpg'
    templateC_name = 'TempCenter.jpg'
    best_Type3=0
    scale_percent = 5

    # Validate input_image
    image, emsg = imgin_check(image, 'E20')
    if emsg is not None:
        save_image(last_valid_image, 'E20')
        return None, (emsg)

    # Validate template image
    templateL, emsg = load_template(templateL_name, 'E20')
    if emsg is not None:
        save_image(last_valid_image, 'E20')
        return None, emsg

    templateS, emsg = load_template(templateS_name, 'E20')
    if emsg is not None:
        save_image(last_valid_image, 'E20')
        return None, emsg

    templateC, emsg = load_template(templateC_name, 'E20')
    if emsg is not None:
        save_image(last_valid_image, 'E20')
        return None, emsg

    # Rescale images
    image_rescaled,emsg = preprocess(image, scale_percent)
    if emsg is not None:
        save_image(last_valid_image, 'E20')
        return None, emsg

    templateL_rescaled, emsg = preprocess(templateL, scale_percent)
    if emsg is not None:
        save_image(last_valid_image, 'E20')
        return None, emsg

    templateC_rescaled, emsg = preprocess(templateC, scale_percent)
    if emsg is not None:
        save_image(last_valid_image, 'E20')
        return None, emsg

    # Check dot distribution and brightness
    image, emsg = img_ok_check(image, 'E20')
    if emsg is not None:
        save_image(last_valid_image, 'E20')
        return None, emsg

    # Match template
    best_angle, best_rotation, best_Type1, emsg = start_temp_match(templateL_rescaled, templateS, image_rescaled, scale_percent)

    if best_Type1 < 0.25:
        emsg = "2400"
        if emsg is not None:
            save_image(last_valid_image, 'E24')
            #logger.error("E2400")
            return None, emsg

    # Determine initial angle
    final_angle = (best_angle + best_rotation) % 360  # Normalize angle to [0, 360)
    normalized_angle = ((final_angle + 180) % 360) - 180  # Converts to [-180, 180]
    if abs(normalized_angle) > 100:
        # Subtract 180 and reverse the sign of the original angle
        adjusted_angle = (180 - abs(normalized_angle)) * (-1 if normalized_angle > 0 else 1)
    else:
        adjusted_angle = normalized_angle

    # Refine angle for sample type

    new, result, emsg = fill_second_two_thirds(image, templateC, normalized_angle)
    if result == 'B':
        adjusted_angle = adjusted_angle + 10

    angle_threshold = 0.51  # Define the threshold for small changes
    if abs(adjusted_angle) <= angle_threshold:
        adjusted_angle = 0
        print("Small orientation change detected. Alignment skipped.")

    print('Home process finished successfully.\n''Adjusted angle is ' + str(0 if abs(adjusted_angle) <= 0.51 else adjusted_angle))
    # **Apply the rotation**
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, adjusted_angle, 1.0)
    rotated_image = cv2.warpAffine(image, rotation_matrix, (w, h), flags=cv2.INTER_LINEAR,
                                   borderMode=cv2.BORDER_REPLICATE)
    rotated_target2 = cv2.resize(rotated_image, None, fx=0.2, fy=0.2,
                                 interpolation=cv2.INTER_AREA)
    #cv2.imshow("RotatedImage", rotated_target2)
    #cv2.waitKey(0)
    #cv2.destroyAllWindows()

    return 0 if abs(adjusted_angle) <= 0.51 else adjusted_angle, None

def home_check(image):
    """
    Check home with side camera image
    Input: Side camera image
    Output: Applied angle correction
    """
    last_valid_image = image.copy()
    template_name = 'TempOSlice.jpg'

    image, emsg = imgin_check(image, 'E25')
    if emsg is not None:
        save_image(last_valid_image, 'E25')
        return None, emsg

    image, emsg = img_ok_check(image, 'E25')
    if emsg is not None:
        save_image(last_valid_image, 'E25')
        return None, emsg

    template, emsg = load_template(template_name, 'E23')
    if emsg is not None:
        save_image(last_valid_image, 'E23')
        return None, emsg

    polygon_region, annotated_image, polygon_mask, (top_left2, bottom_right), emsg = template_match_with_polygon(
        image, template)
    if emsg is not None:
        save_image(last_valid_image, 'E23')
        return None, emsg

    crop_offset_y = top_left2[1]

    # Get top and bottom of non-white content (in local/cropped coordinates)
    non_white_rows = np.where(np.any(polygon_region > 100, axis=1))[0]
    top_row = non_white_rows[0] + crop_offset_y
    bottom_row = non_white_rows[-1] + crop_offset_y

    print(top_row)
    print(bottom_row)

    # Dead zone check: if vertical difference ≤ 5 pixels, skip correction
    top_margin = top_row
    bottom_margin = image.shape[0] - bottom_row
    print(top_margin)
    print(bottom_margin)

    if abs(top_margin-bottom_margin)< 5:
        print("Top and bottom within 5 pixels of image edges. No correction needed.")
        return 0.0, None

    non_white_center = abs(top_margin - bottom_margin) / 2
    imbalance = non_white_center
    print(imbalance)
    rows_per_degree = 100
    optimal_angle = imbalance / rows_per_degree
    if top_margin>bottom_margin:
        optimal_angle=-optimal_angle



    print(f"Estimated rotation angle: {optimal_angle:.4f} degrees")

    # Assume you're rotating 'image'
    (h, w) = image.shape[:2]

    # ✅ Make sure you compute the center from the full image
    center = (w / 2, h / 2)

    # ✅ Generate the rotation matrix using correct center
    rotation_matrix = cv2.getRotationMatrix2D(center, optimal_angle, 1.0)

    # ✅ Apply the warpAffine using same size (w, h)
    rotated_image = cv2.warpAffine(
        image, rotation_matrix, (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE
    )


    # Show resized image for preview
    rotated_preview = cv2.resize(rotated_image, None, fx=0.2, fy=0.2, interpolation=cv2.INTER_AREA)

    return optimal_angle, None


#PROCESS CENTER CAMERA - CIRCLE

def process_center(image):
    """
    Input: Center camera image - grayscale
    Output: Center circle eval (360 dots)
    ErrorCode: "E21xx"
    """
    last_valid_image = image.copy()
    # Filenames and constant values:
    template_name = 'TempCenter.jpg'

    image, emsg = imgin_check(image, 'E21')
    if emsg is not None:
        save_image(last_valid_image, 'E21')
        return None, (emsg)

    image, emsg = img_ok_check(image, 'E21')
    if emsg is not None:
        save_image(last_valid_image, 'E21')
        return None, (emsg)

    # Validate template image
    template, emsg = load_template(template_name, 'E21')
    if emsg is not None:
        save_image(last_valid_image, 'E21')
        return None, emsg

    # Match and extract the template region
    matched_region, emsg = center_template_match_and_extract(template, image)
    if emsg is not None:
        save_image(last_valid_image, 'E21')
        return None, emsg

    # Calc dot countours - Draw (True or False)
    dot_contours, emsg = center_detect_small_dots_and_contours(matched_region, DRAW_CENTER_DOTS)
    if emsg is not None:
        save_image(last_valid_image, 'E21')
        return None, emsg

    a = 360 - len(dot_contours)
    if a < 0:
        return None, 'E2199'
    
    print('Center: '+ str(len(dot_contours)) + ' dots found!\n' + str(360-len(dot_contours)) + ' dots missing.')

    return dot_contours, None



#PROCESS CENTER CAMERA - INNER SLICE

def process_inner_slice(image):
    """
    Input: Center camera image - grayscale
    Output: Inner slice eval (510 dots - Rows: 1-50)
    ErrorCode: "E22xx"
    """
    template_name = 'TempISlice.jpg'

    last_valid_image = image.copy()

    image, emsg = imgin_check(image, 'E22')
    if emsg is not None:
        save_image(last_valid_image, 'E22')
        return None, (emsg)

    image, emsg = img_ok_check(image, 'E22')
    if emsg is not None:
        save_image(last_valid_image, 'E22')
        return None, (emsg)

    # Validate template image
    template, emsg = load_template(template_name, 'E22')
    if emsg is not None:
        save_image(last_valid_image, 'E22')
        return None, emsg

    cropped_image, emsg = crop_second_two_thirds(image)
    if emsg is not None:
        save_image(last_valid_image, 'E22')
        return None, emsg
    # cv2.imshow('croped',cv2.resize(cropped_image, None, fx=0.2, fy=0.2,  interpolation=cv2.INTER_AREA))
    # cv2.waitKey(0)

    polygon_region, polygon_offset, emsg = islice_template_match_with_polygon(cropped_image, template)
    if emsg is not None:
        save_image(last_valid_image, 'E22')
        return None, emsg

    # Step 3: Detect small dots in the polygon region, Draw (True or False)
    dot_contours, annotated_dots, emsg = islice_detect_small_dots_and_contours(polygon_region, DRAW_INNER_DOTS)

    if emsg is not None:
        save_image(last_valid_image, 'E22')
        return None, emsg
    print('InnerSlice: ' + str(len(dot_contours)) + ' dots found!\n' + str(510 - len(dot_contours)) + ' dots missing.')

    return dot_contours, None


#PROCESS SIDE CAMERA - OUTER SLICE


def start_side_slice(image):
    """
    Input: Side camera image - grayscale
    Output: Outer slice eval (2248 dots)
    ErrorCode: "E23xx"
    """
    template_name = 'TempOSlice.jpg'

    last_valid_image = image.copy()

    image, emsg = imgin_check(image, 'E23')
    if emsg is not None:
        save_image(last_valid_image, 'E23')
        return None, (emsg)

    image, emsg = img_ok_check(image, 'E23')
    if emsg is not None:
        save_image(last_valid_image, 'E23')
        return None, (emsg)

    # Validate template image
    template, emsg = load_template(template_name, 'E23')
    if emsg is not None:
        save_image(last_valid_image, 'E23')
        return None, emsg

    polygon_region, annotated_image, polygon_mask, (top_left, bottom_right), emsg = template_match_with_polygon(image, template)
    if emsg is not None:
        save_image(last_valid_image, 'E23')
        return None, emsg

    dot_contours, annotated_dots, grouped_x, matching_column, emsg = detect_small_dots_and_contours(polygon_region, DRAW_OUTER_DOTS)
    if emsg is not None:
        save_image(last_valid_image, 'E23')
        return None, emsg
    print('OuterSlice: '+ str(len(dot_contours)) + ' dots found!\n' + str(2248-len(dot_contours)) + ' dots missing.')
    # Shift dot coordinates from polygon region to original image space
    shifted_dot_contours = [
        (x + top_left[0], y + top_left[1], col, area)
        for (x, y, col, area) in dot_contours]

    return shifted_dot_contours, None