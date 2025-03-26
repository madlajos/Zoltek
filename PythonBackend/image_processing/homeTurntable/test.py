import cv2
import numpy as np
import unittest
import angle_detect
from homeTurntable.preprocessing import preprocess
from homeTurntable.angle_detect import angle_det
from GeneralProc.load_templ import load_template

def rotate_image(image, angle):
    """Rotate an image by a given angle."""
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(image, rotation_matrix, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


class TestAngleDetection(unittest.TestCase):
    def setUp(self):
        global rotated_templates, image_rescaled
        image=cv2.imread(r'D:\Lali\december19\Image__2025-03-20__14-51-382.jpg', cv2.IMREAD_GRAYSCALE)
        scale_percent=5
        template_name = 'TempHome4.jpg'
        scale_percent = 5

        # Validate template image
        template, emsg = load_template(template_name, 'E20')
        if emsg is not None:
            return None, emsg

        image_rescaled, emsg = preprocess(image, scale_percent)
        if emsg is not None:
            return None, emsg

        template_rescaled, emsg = preprocess(template, scale_percent)
        if emsg is not None:
            return None, emsg

        rotated_templates = {angle: rotate_image(template_rescaled, angle) for angle in [0, 90, 180, 270]}
        if rotated_templates is None:
            return None, "E2011"

        if image_rescaled is None or rotated_templates is None:
                self.fail("Test images not loaded properly.")

    def test_angle_detection(self):
        """Test if `angle_det` correctly detects rotation for 0-360°."""
        results = []

        for angle in range(0, 361, 1):  # Rotating from 0° to 360° in 1° increments
            rotated_img = rotate_image(image_rescaled, angle)

            # Call the function to test
            normalized_angle, emsg = angle_det(rotated_templates, rotated_img)

            adjusted_angle = normalized_angle
            if adjusted_angle > 180:
                adjusted_angle -= 360
            elif adjusted_angle < -180:
                adjusted_angle += 360

            # Print output for debugging
            print(f"Input Rotation: {angle}° | Detected: {normalized_angle}° | Adjusted: {adjusted_angle}°")

            # Store results for later analysis
            results.append((angle, normalized_angle, adjusted_angle))

            # Ensure the estimated angle is close to the expected

        # Optionally save results to a file for analysis
        with open("angle_detection_results.txt", "w") as f:
            for angle, detected, adjusted in results:
                f.write(f"{angle},{detected},{adjusted}\n")


if __name__ == "__main__":
    unittest.main()
