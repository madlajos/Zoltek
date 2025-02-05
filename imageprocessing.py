import math
import cv2
import numpy as np
import time  # Import time module for timing
import os
from concurrent.futures import ThreadPoolExecutor
import pandas

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



def center_eval(image):
    image = cv2.flip(image, 0)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(script_dir, 'templ03_mod3.jpg')
    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)

    if image is None or template is None:
        raise FileNotFoundError("Target or template image not found. Check the file paths.")

    # Step 1: Crop the input image
    cropped_image = crop_second_two_thirds(image)
    # Step 2: Match and extract the template region
    matched_region = template_match_and_extract(template, cropped_image)

    # Step 4: Detect small dots and extract their contours and areas
    dot_contours, annotated_dots = detect_small_dots_and_contours(matched_region)

    # Print the areas of the detected dots
    for i, dot in enumerate(dot_contours):
        print(f"Dot {i + 1}: X = {dot[0]}, Y = {dot[1]}, Column = {dot[2]}, Area = {dot[3]}")

    cv2.imwrite(os.path.join(script_dir, 'result.jpg'), annotated_dots)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    return dot_contours

def crop_second_two_thirds(image):
    """
    Crops the second 2/3 horizontally of an image and returns it.
    """
    if image is None:
        raise FileNotFoundError(f"Image not obtained from the center camera.")
    if image is not None:
       # height, width = image.shape
        #crop_start = width // 2
        #cropped_image = image[:, :crop_start]
        cropped_image=image
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    return cropped_image




def template_match_and_extract(template, cropped_image):
    """
    Performs template matching on the cropped image, extracts the best-matched region,
    and applies the mask at the matched location.
    """

    template_height, template_width = template.shape
    result = cv2.matchTemplate(cropped_image, template, cv2.TM_CCOEFF_NORMED)

    # Get the location of the best match
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    print(f"Best match confidence: {max_val}")

    # Extract the best-matched region
    top_left = max_loc
    bottom_right = (top_left[0] + template_width, top_left[1] + template_height)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    mask_path = os.path.join(script_dir, 'templ03_mod3.jpg')
    mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)

    # Ensure the mask size matches the template
    mask_resized = cv2.resize(mask, (template_width, template_height), interpolation=cv2.INTER_AREA)
    adjustment1 = 5  # Try values like -1, -2 to see if it corrects the shift
    adjustment2 = 5
    corrected_top_left = (top_left[0] + adjustment1, top_left[1]+adjustment2)
    corrected_bottom_right = (corrected_top_left[0] + template_width, corrected_top_left[1] + template_height)
    # Create a blank mask of the same size as the cropped image
    mask_layer = np.zeros_like(cropped_image, dtype=np.uint8)
    mask_layer[corrected_top_left[1]:corrected_bottom_right[1],corrected_top_left[0]:corrected_bottom_right[0]] = mask_resized





    # Apply the mask on the cropped image using bitwise operation
    masked_image = cv2.bitwise_and(cropped_image, cropped_image, mask=mask_layer)

    # Save and show results
    cv2.imwrite('matched_region.png', masked_image)
    # cv2.imshow("Masked Region", masked_image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    return masked_image


def detect_small_dots_and_contours(masked_region):
    """
    Detect small dots in the masked region, extract their contours, and calculate areas.
    Returns a list of dot positions and areas in the format:
    (X, Y, 0, Area)
    """
    # Threshold the masked region
    _, thresh = cv2.threshold(masked_region, 130, 255, cv2.THRESH_BINARY)

    # Detect contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Store dot positions and areas
    dot_area_column_mapping = []  # List to store dot data
    annotated_dots = cv2.cvtColor(masked_region, cv2.COLOR_GRAY2BGR)

    for contour in contours:
        area = cv2.contourArea(contour)
        if area > 0:  # Only consider non-zero area contours
            # Compute the center of the dot
            M = cv2.moments(contour)
            if M["m00"] != 0:
                cX = int(M["m10"] / M["m00"])
                cY = int(M["m01"] / M["m00"])

                # Append to the structured list (X, Y, 0, Area)
                dot_area_column_mapping.append((cX, cY, 0, area))

                # Draw the dot and annotate it
                cv2.drawContours(annotated_dots, [contour], -1, (0, 255, 0), 1)
                cv2.putText(annotated_dots, f"{area:.1f}", (cX, cY), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
    df = pandas.DataFrame(dot_area_column_mapping, columns=['X', 'Y', 'Column', 'Area'])
    df.to_csv('dot_areas_with_columns.csv', index=False)
    return dot_area_column_mapping, annotated_dots




