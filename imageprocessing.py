import math
import cv2
import numpy as np
import time  # Import time module for timing
import os
from concurrent.futures import ThreadPoolExecutor

global result

def home_turntable_with_image(image, scale_percent=10, resize_percent=20):
    """
    Align a template to a target image and find the best rotation angle.
    Includes handling for rotated and vertically mirrored images.

    Parameters:
        image (numpy array): Target image loaded as a numpy array.
        scale_percent (int): Percent to scale down images for computation.
        resize_percent (int): Percent to resize images for visualization.

    Returns:
        float: The best alignment angle in degrees.
    """


    # Convert the target image to grayscale
    target = (image)

    # Construct the template path dynamically
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(script_dir, 'templ03.jpg')
    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)

    if target is None or template is None:
        raise FileNotFoundError("Target or template image not found. Check the file paths.")

    # Preprocessing with Canny edge detection
    def preprocess(image, scale_percent):
        return cv2.resize(image, None, fx=scale_percent / 100, fy=scale_percent / 100, interpolation=cv2.INTER_AREA)

    # Preprocess the target and template
    target_small = preprocess(target, scale_percent)

    # Rotate the template and store versions
    def rotate_image(image, angle):
        center = (image.shape[1] // 2, image.shape[0] // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1)
        return cv2.warpAffine(image, rotation_matrix, (image.shape[1], image.shape[0]))

    rotated_templates = {
        0: preprocess(template, scale_percent),  # Original template
        90: preprocess(rotate_image(template, 90), scale_percent),
        180: preprocess(rotate_image(template, 180), scale_percent),
        270: preprocess(rotate_image(template, 270), scale_percent),
    }

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
        cropped_region = target_to_match[top_left[1]:top_left[1] + h, top_left[0]:top_left[0] + w]

        # Parallelize the rotation matching
        angles = np.arange(-180, 180, 0.1)
        best_angle = 0
        best_score = -float('inf')

        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(lambda angle: find_best_match_for_angle(angle, cropped_region, template_small), angles))

        # Find the best angle and score
        for angle, score in results:
            if score > best_score:
                best_score = score
                best_angle = angle

        return best_angle, best_score

    # Track the best match across all templates
    best_angle = None
    best_score = -float('inf')
    best_rotation = 0  # Tracks the rotation of the template

    for rotation, template_variant in rotated_templates.items():
        angle, score = find_best_match_and_angle(target_small, template_variant)
        if score > best_score:
            best_score = score
            best_angle = angle
            best_rotation = rotation

    # Combine template rotation and alignment angle
    final_angle = (best_angle + best_rotation) % 360  # Normalize angle to [0, 360)
    normalized_angle = ((final_angle + 180) % 360) - 180  # Converts to [-180, 180]
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
    print(adjusted_angle)


    print(f"Best alignment angle: {adjusted_angle:.1f} degrees")


    return adjusted_angle


def start(image):
    """
    Entry point to process the provided image.
    """
    original_image = image
    cropped_image = image

    # Construct the template path dynamically
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(script_dir, 'templ05_mod2.jpg')

    if original_image is None:
        raise ValueError("The provided image is None. Ensure a valid image is passed.")

    if not os.path.exists(template_path):
        raise FileNotFoundError("Template file not found. Check the file path.")

    try:
        result = process_image(original_image, template_path)

    except Exception as e:
        print(f"An error occurred during processing: {e}")
        
    return result
        

def crop_second_two_thirds(image_path):
    """
    Crops the second 2/3 horizontally of an image and returns it.
    """
    cropped_image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    original_image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if cropped_image is None or original_image is None:
        raise FileNotFoundError(f"Image not found at {image_path}")

    return original_image, cropped_image

def preprocess(image, scale_percent=100):
    """
    Preprocesses the image by resizing it according to the scale percentage.
    """
    if scale_percent != 100:
        width = int(image.shape[1] * scale_percent / 100)
        height = int(image.shape[0] * scale_percent / 100)
        resized_image = cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)
        return resized_image
    return image

def rotate_image(image, angle):
    """
    Rotates the image by the specified angle (in degrees) around its center.
    """
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(image, matrix, (w, h))
    return rotated

def template_match_with_all_rotations(cropped_image, rotated_templates):
    """
    Matches the best template (with all rotations) in the cropped image and
    returns the matched region, its coordinates, and the rotation angle.
    """
    best_match = None
    best_angle = None
    best_val = -1
    best_top_left = None
    best_template_shape = None

    for angle, rotated_template in rotated_templates.items():
        if (rotated_template.shape[0] > cropped_image.shape[0] or
            rotated_template.shape[1] > cropped_image.shape[1]):
            continue

        result = cv2.matchTemplate(cropped_image, rotated_template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val > best_val:
            best_val = max_val
            best_angle = angle
            best_top_left = max_loc
            best_template_shape = rotated_template.shape

    if best_val < 0.05:
        raise ValueError(f"Template match confidence too low (max_val: {best_val:.3f}). Template likely not found.")

    template_height, template_width = best_template_shape
    top_left = best_top_left
    bottom_right = (top_left[0] + template_width, top_left[1] + template_height)

    matched_region = cropped_image[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]]

    return matched_region, top_left, best_template_shape[1], best_template_shape[0], best_angle

def template_match_with_polygon(cropped_image, template_path):
    """
    Matches a template in the cropped image and returns the matched region and its coordinates.
    """
    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    if template is None:
        raise FileNotFoundError(f"Template not found at {template_path}")

    result = cv2.matchTemplate(cropped_image, template, cv2.TM_CCOEFF_NORMED)
    _, _, _, max_loc = cv2.minMaxLoc(result)

    template_height, template_width = template.shape
    top_left = max_loc
    bottom_right = (top_left[0] + template_width, top_left[1] + template_height)

    matched_region = cropped_image[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]]

    return matched_region, top_left, template_width, template_height

def calculate_alignment_angle(image_shape, top_left, template_width, template_height, cropped_offset):
    """
    Calculate the angle required to align the matched region so that the distances
    from the top-right and bottom-right corners to the top and bottom edges are equal.
    """
    img_height, img_width = image_shape
    top_left_original = (top_left[0] + cropped_offset, top_left[1])

    top_right = (top_left_original[0] + template_width, top_left_original[1])
    bottom_right = (top_left_original[0] + template_width, top_left_original[1] + template_height)

    top_right_distance = top_right[1]
    bottom_right_distance = img_height - bottom_right[1]

    horizontal_distance = template_width

    vertical_difference = bottom_right_distance - top_right_distance
    angle = math.degrees(math.atan2(vertical_difference, horizontal_distance))

    return -angle

def process_image(image, template_path):
    """
    Processes the provided image using the template and returns the alignment angle.
    """
    try:
        original_image = image
        cropped_image = image

        # Step 2: Create rotated templates for initial alignment
        template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
        if template is None:
            raise FileNotFoundError(f"Template not found at {template_path}")

        rotated_templates = {
            0: preprocess(template),
            5: preprocess(rotate_image(template, 5)),
            10: preprocess(rotate_image(template, 10)),
            -5: preprocess(rotate_image(template, -5)),
            -10: preprocess(rotate_image(template, -10)),
        }

        matched_region, top_left, template_width, template_height, best_angle = template_match_with_all_rotations(
            cropped_image, rotated_templates
        )

        reverse_angle = -best_angle
        aligned_image = rotate_image(original_image, reverse_angle)

        # Step 3: Perform polygon-based matching on the aligned image
        matched_region, top_left, template_width, template_height = template_match_with_polygon(
            aligned_image, template_path
        )

        cropped_offset = original_image.shape[1] // 3
        alignment_angle = calculate_alignment_angle(
            original_image.shape, top_left, template_width, template_height, cropped_offset
        )
        print(round(alignment_angle,2))
        result = (round(alignment_angle,2))
        
        return result

    except Exception as e:
        print(f"An error occurred: {e}")
        return None
