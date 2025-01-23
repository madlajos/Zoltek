import cv2
import numpy as np
import time  # Import time module for timing
import os
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
        edges = cv2.Canny(image, 50, 150)  # Adjust thresholds for better edge detection
        return cv2.resize(edges, None, fx=scale_percent / 100, fy=scale_percent / 100, interpolation=cv2.INTER_AREA)

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

    def find_best_match_and_angle(target_to_match, template_small):
        result = cv2.matchTemplate(target_to_match, template_small, cv2.TM_CCOEFF_NORMED)
        _, _, _, max_loc = cv2.minMaxLoc(result)
        h, w = template_small.shape
        top_left = max_loc
        cropped_region = target_to_match[top_left[1]:top_left[1] + h, top_left[0]:top_left[0] + w]

        best_angle = 0
        best_score = -float('inf')

        # Rotate and find the best angle
        for angle in np.arange(-180, 180, 0.1):
            rotated = rotate_image(cropped_region, angle)
            correlation = cv2.matchTemplate(rotated, template_small, cv2.TM_CCOEFF_NORMED).max()
            if correlation > best_score:
                best_score = correlation
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

    print(adjusted_angle)
    rotated_target = rotate_image(target, adjusted_angle)



    print(f"Best alignment angle: {final_angle:.1f} degrees")



    return adjusted_angle

# Example Usage
