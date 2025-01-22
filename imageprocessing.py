import cv2
import numpy as np
import os

def home_turntable_with_image(image, scale_percent=10, resize_percent=20):
    """
    Align a template to a target image and find the best rotation angle.

    Parameters:
        image (numpy.ndarray): Target image to align the template with.
        scale_percent (int): Percent to scale down images for computation.
        resize_percent (int): Percent to resize images for visualization.

    Returns:
        float: The best alignment angle in degrees.
    """

    # Convert target image to grayscale
    target = image

    # Construct the template path dynamically
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(script_dir, 'templ.jpg')
    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)

    if target is None or template is None:
        raise FileNotFoundError("Target or template image not found. Check the file paths.")

    # Downscale images for faster computation
    target_small = cv2.resize(target, None, fx=scale_percent / 100, fy=scale_percent / 100, interpolation=cv2.INTER_AREA)
    template_small = cv2.resize(template, None, fx=scale_percent / 100, fy=scale_percent / 100, interpolation=cv2.INTER_AREA)

    # Perform template matching
    result = cv2.matchTemplate(target_small, template_small, cv2.TM_CCOEFF_NORMED)
    _, _, _, max_loc = cv2.minMaxLoc(result)

    # Get dimensions and calculate matched region
    h, w = template_small.shape
    top_left = max_loc
    bottom_right = (top_left[0] + w, top_left[1] + h)

    # Scale coordinates back to original image size
    scale_factor = 100 / scale_percent
    top_left_full = (int(top_left[0] * scale_factor), int(top_left[1] * scale_factor))
    bottom_right_full = (int(bottom_right[0] * scale_factor), int(bottom_right[1] * scale_factor))

    # Crop the matched region from the original image
    matched_region_full = target[top_left_full[1]:bottom_right_full[1], top_left_full[0]:bottom_right_full[0]]

    # Define function to rotate an image
    def rotate_image(image, angle):
        center = (image.shape[1] // 2, image.shape[0] // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1)
        return cv2.warpAffine(image, rotation_matrix, (image.shape[1], image.shape[0]))

    # Find the best rotation angle
    best_angle = 0
    best_score = -float('inf')
    for angle in np.arange(-180, 180, 0.1):
        rotated = rotate_image(target_small[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]], angle)
        correlation = cv2.matchTemplate(rotated, template_small, cv2.TM_CCOEFF_NORMED).max()
        if correlation > best_score:
            best_score = correlation
            best_angle = angle

    # Print the best alignment angle
    print(f"Best alignment angle: {best_angle:.1f} degrees")

    # Return the best alignment angle
    return best_angle


