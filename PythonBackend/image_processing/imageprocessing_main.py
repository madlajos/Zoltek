import cv2
from .homeTurntable import *
from .GeneralProc import *
from .Center import *
from .InnerSlice import *
from .OuterSlice import *
import time
import os


DRAW_CENTER_DOTS = True
DRAW_INNER_DOTS = True
DRAW_OUTER_DOTS = True

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
    scale_percent = 10

    image, emsg = imgin_check(image, 'E20')
    if emsg is not None:
        save_image(last_valid_image, 'E20')
        return None, (emsg)
    # Validate template image
    templateL, emsg = load_template(templateL_name, 'E20')
    if emsg is not None:
        save_image(last_valid_image, 'E20')
        return None, emsg
    # Validate template image
    templateS, emsg = load_template(templateS_name, 'E20')
    if emsg is not None:
        save_image(last_valid_image, 'E20')
        return None, emsg


    image_rescaled,emsg = preprocess(image, scale_percent)
    if emsg is not None:
        save_image(last_valid_image, 'E20')
        return None, emsg

    templateL_rescaled, emsg = preprocess(templateL, scale_percent)
    if emsg is not None:
        save_image(last_valid_image, 'E20')
        return None, emsg

    image, emsg = img_ok_check(image, 'E20')
    if emsg is not None:
        save_image(last_valid_image, 'E20')
        return None, (emsg)


    best_angle, best_rotation,emsg=start_temp_match(templateL_rescaled,templateS, image_rescaled, scale_percent)
    if emsg is not None:
        save_image(last_valid_image, 'E20')
        return None, (emsg)
    final_angle = (best_angle + best_rotation) % 360  # Normalize angle to [0, 360)
    print(final_angle)
    normalized_angle = ((final_angle + 180) % 360) - 180  # Converts to [-180, 180]
    print(normalized_angle)
    print(f"Normalized alignment angle: {normalized_angle:.1f} degrees")
    if abs(normalized_angle) > 100:
        # Subtract 180 and reverse the sign of the original angle
        adjusted_angle = (180 - abs(normalized_angle)) * (-1 if normalized_angle > 0 else 1)
    else:
        adjusted_angle = normalized_angle
    # Apply the angle threshold
    angle_threshold = 0.51  # Define the threshold for small changes
    if abs(adjusted_angle) <= angle_threshold:
        adjusted_angle = 0
        print("Small orientation change detected. Alignment skipped.")


    print(f"Best alignment angle: {adjusted_angle:.1f} degrees")

    print('Home process finished successfully.\n''Adjusted angle is ' + str(0 if abs(adjusted_angle) <= 0.51 else adjusted_angle))
    # # **Apply the rotation**
    # (h, w) = image.shape[:2]
    # center = (w // 2, h // 2)
    # rotation_matrix = cv2.getRotationMatrix2D(center, adjusted_angle, 1.0)
    # rotated_image = cv2.warpAffine(image, rotation_matrix, (w, h), flags=cv2.INTER_LINEAR,
    #                                borderMode=cv2.BORDER_REPLICATE)
    # rotated_target2 = cv2.resize(rotated_image, None, fx=0.2, fy=0.2,
    #                              interpolation=cv2.INTER_AREA)
    # cv2.imshow("Template (Resized)", rotated_target2)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()

    # # Ignore small orientation changes
    return 0 if abs(adjusted_angle) <= 0.51 else adjusted_angle, None



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

    cropped_image,emsg = crop_second_two_thirds(image)
    if emsg is not None:
        save_image(last_valid_image, 'E22')
        return None, emsg

    polygon_region, emsg = islice_template_match_with_polygon(cropped_image, template)
    if emsg is not None:
        save_image(last_valid_image, 'E22')
        return None, emsg

    # Step 3: Detect small dots in the polygon region, Draw (True or False)
    dot_contours, annotated_dots, emsg = islice_detect_small_dots_and_contours(polygon_region, DRAW_INNER_DOTS)
    if emsg is not None:
        save_image(last_valid_image, 'E22')
        return None, emsg

    print('InnerSlice: '+ str(len(dot_contours)) + ' dots found!\n' + str(510-len(dot_contours)) + ' dots missing.')
    # print(dot_contours)

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

    polygon_region, annotated_image, polygon_mask, emsg = template_match_with_polygon(image, template)
    if emsg is not None:
        save_image(last_valid_image, 'E23')
        return None, emsg

    dot_contours, annotated_dots, grouped_x, matching_column, emsg = detect_small_dots_and_contours(polygon_region, DRAW_OUTER_DOTS)
    if emsg is not None:
        save_image(last_valid_image, 'E23')
        return None, emsg
    print('OuterSlice: '+ str(len(dot_contours)) + ' dots found!\n' + str(2248-len(dot_contours)) + ' dots missing.')

    return dot_contours, None