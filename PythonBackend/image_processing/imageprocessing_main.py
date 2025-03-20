import cv2
from .homeTurntable import *
from .GeneralProc import *
from .Center import *
from .InnerSlice import *
from .OuterSlice import *
import time
import os


def home_turntable_with_image(image):
    """Home the turntable and return the best alignment angle.
        Input: Grayscale image - Center camera
        Output: Adjusted angle for rotation
        ErrorCode: "E20xx"
    """

    # Filenames and constant values:
    template_name = 'TempHome.jpg'
    scale_percent = 5
    image, emsg = imgin_check(image, 'E20')
    if emsg is not None:
        return None, (emsg)
   
    image, emsg = img_ok_check(image, 'E20')
    if emsg is not None:
        return None, (emsg)

    # Validate template image
    template, emsg = load_template(template_name, 'E20')
    if emsg is not None:
        return None, emsg

    image_rescaled,emsg = preprocess(image, scale_percent)
    if emsg is not None:
        return None, emsg

    template_rescaled, emsg = preprocess(template, scale_percent)
    if emsg is not None:
        return None, emsg

    rotated_templates = {angle: rotate_image(template_rescaled, angle) for angle in [0, 90, 180, 270]}
    if rotated_templates is None:
        return None, "E2011"

    normalized_angle, emsg=angle_det(rotated_templates, image_rescaled)
    if emsg is not None:
        return None, emsg
        # Ensure the rotation follows the shortest path
        # **Ensure shortest rotation path**
    if normalized_angle > 90:
        adjusted_angle = normalized_angle - 180  # Flip direction to shortest path
    elif normalized_angle < -90:
        adjusted_angle = normalized_angle + 180  # Flip direction to shortest path
    else:
        adjusted_angle = normalized_angle  # No adjustment needed

    adjusted_angle = round(adjusted_angle, 1)
    # Adjust for large rotations
    #adjusted_angle = (180 - abs(normalized_angle)) * (-1 if normalized_angle > 0 else 1) if abs(
     #   normalized_angle) > 100 else normalized_angle

    print('Home process finished successfully.\n''Adjusted angle is ' +str(0 if abs(adjusted_angle) <= 0.51 else adjusted_angle))
    # **Apply the rotation**
    # (h, w) = image.shape[:2]
    # center = (w // 2, h // 2)
    # rotation_matrix = cv2.getRotationMatrix2D(center, adjusted_angle, 1.0)
    # rotated_image = cv2.warpAffine(image, rotation_matrix, (w, h), flags=cv2.INTER_LINEAR,
    #                                borderMode=cv2.BORDER_REPLICATE)
    # rotated_target2 = cv2.resize(rotated_image, None, fx=scale_percent / 100, fy=scale_percent / 100,
    #                              interpolation=cv2.INTER_AREA)
    # cv2.imshow("Template (Resized)", rotated_target2)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()
    # Ignore small orientation changes
    return 0 if abs(adjusted_angle) <= 0.51 else adjusted_angle, None



#PROCESS CENTER CAMERA - CIRCLE

def process_center(image):
    """
    Input: Center camera image - grayscale
    Output: Center circle eval (360 dots)
    ErrorCode: "E21xx"
    """
    # Filenames and constant values:
    template_name = 'TempCenter.jpg'

    image, emsg = imgin_check(image, 'E21')
    if emsg is not None:
        return None, (emsg)
    image, emsg = img_ok_check(image, 'E21')
    if emsg is not None:
        return None, (emsg)

    # Validate template image
    template, emsg = load_template(template_name, 'E21')
    if emsg is not None:
        return None, emsg

    # Match and extract the template region
    matched_region, emsg = center_template_match_and_extract(template, image)
    if emsg is not None:
        return None, emsg
    # Calc dot countours - Draw (True or False)
    dot_contours, emsg = center_detect_small_dots_and_contours(matched_region, True)
    if emsg is not None:
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

    image, emsg = imgin_check(image, 'E22')
    if emsg is not None:
        return None, (emsg)
    image, emsg = img_ok_check(image, 'E22')
    if emsg is not None:
        return None, (emsg)

    # Validate template image
    template, emsg = load_template(template_name, 'E22')
    if emsg is not None:
        return None, emsg

    cropped_image,emsg = crop_second_two_thirds(image)
    if emsg is not None:
        return None, emsg

    polygon_region, emsg = islice_template_match_with_polygon(cropped_image, template)
    if emsg is not None:
        return None, emsg

    # Step 3: Detect small dots in the polygon region, Draw (True or False)
    dot_contours, annotated_dots, grouped_x,emsg = islice_detect_small_dots_and_contours(polygon_region, True)
    if emsg is not None:
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

    image, emsg = imgin_check(image, 'E23')
    if emsg is not None:
        return None, (emsg)
    image, emsg = img_ok_check(image, 'E23')
    if emsg is not None:
        return None, (emsg)
    # Validate template image
    template, emsg = load_template(template_name, 'E23')
    if emsg is not None:
        return None, emsg


    polygon_region, annotated_image, polygon_mask, emsg = template_match_with_polygon(image, template)
    if emsg is not None:
        return None, emsg

    dot_contours, annotated_dots, grouped_x,matching_column, emsg = detect_small_dots_and_contours(polygon_region, True)
    if emsg is not None:
        return None, emsg
    print('OuterSlice: '+ str(len(dot_contours)) + ' dots found!\n' + str(2248-len(dot_contours)) + ' dots missing.')

    return dot_contours, None