import cv2
import numpy as np
import time
import os
import logging

logger = logging.getLogger(__name__)

def center_detect_small_dots_and_contours(masked_region, drawtf):
    """Detects small dots and contours in a masked region with error handling."""

    try:
        # Validate Input**
        if masked_region is None:
            logger.error("E2116")
            return None, "E2116"

        # ✅ **2️⃣ Apply Thresholding (Error-Proofed)**
        try:
            _, thresh = cv2.threshold(masked_region, 100, 255, cv2.THRESH_BINARY)
        except cv2.error as e:
            logger.error("E2117")
            return None, "E2117"

        # ✅ **3️⃣ Detect Contours (Error Handling)**
        try:
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        except cv2.error as e:
            logger.error("E2118")
            return None, "E2118"

        # ✅ **4️⃣ Process Contours Efficiently**
        dot_area_column_mapping = []  # Store (X, Y, Column, Area)
        for contour in contours:
            try:
                area = cv2.contourArea(contour)
                if area > 0:  # Ignore tiny contours
                    M = cv2.moments(contour)
                    if M["m00"] != 0:
                        cX = int(M["m10"] / M["m00"])
                        cY = int(M["m01"] / M["m00"])
                        dot_area_column_mapping.append((cX, cY, 0, area))
            except cv2.error as e:
                logger.error("E2119")
                return None, "E2119"

        if drawtf == True:
            # Optional Draw:
            annotated_dots = cv2.cvtColor(masked_region, cv2.COLOR_GRAY2BGR)
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > 0:  # Only consider non-zero area contours
                    # Compute the center of the dot
                    M = cv2.moments(contour)
                    if M["m00"] != 0:
                        cX = int(M["m10"] / M["m00"])
                        cY = int(M["m01"] / M["m00"])



                        # Draw the dot and annotate it
                        cv2.drawContours(annotated_dots, [contour], -1, (0, 255, 0), 1)
                        cv2.putText(annotated_dots, f"{area:.1f}", (cX, cY), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                                    (255, 255, 0), 1)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"result_circle_{timestamp}.jpg"
            results_dir = os.path.join(os.getcwd(), "Results")
            os.makedirs(results_dir, exist_ok=True)  # Make sure the folder exists
            cv2.imwrite(os.path.join(results_dir, filename), annotated_dots)
            return dot_area_column_mapping, None  # Success

        return dot_area_column_mapping, None  # Success

    except Exception as e:
        logger.error('E2120')
        return None, "E2120"





# def center_detect_small_dots_and_contours(masked_region):
#
#     # Threshold the masked region
#     _, thresh = cv2.threshold(masked_region, 100, 255, cv2.THRESH_BINARY)
#
#     # Detect contours
#     contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
#
#     # Store dot positions and areas
#     dot_area_column_mapping = []  # List to store dot data
#    # annotated_dots = cv2.cvtColor(masked_region, cv2.COLOR_GRAY2BGR)
#     for contour in contours:
#         area = cv2.contourArea(contour)
#         if area > 0:  # Only consider non-zero area contours
#             # Compute the center of the dot
#             M = cv2.moments(contour)
#             if M["m00"] != 0:
#                 cX = int(M["m10"] / M["m00"])
#                 cY = int(M["m01"] / M["m00"])
#
#                 # Append to the structured list (X, Y, 0, Area)
#                 dot_area_column_mapping.append((cX, cY, 0, area))
#
#                 # Draw the dot and annotate it
#               #  cv2.drawContours(annotated_dots, [contour], -1, (0, 255, 0), 1)
#                # cv2.putText(annotated_dots, f"{area:.1f}", (cX, cY), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
#
#     # Test - Save res to file
#     #script_dir = os.path.dirname(os.path.abspath(__file__))
#     #timestamp = time.strftime("%Y%m%d_%H%M%S")
#     #filename = f"result_circle_{timestamp}.jpg"
#     #cv2.imwrite(os.path.join(script_dir, filename), annotated_dots)
#
#     return dot_area_column_mapping
