import math
import os
import numpy as np
import cv2
from GeneralProc import logger  # Assuming you already have this in your codebase

def det_dot_home(image):
    try:
        if image is None:
            logger.error("E2015")
            return None, "E2015"

        if len(image.shape) != 2:
            logger.error("E2016 - Input image must be grayscale.")
            return None, "E2016"

        # Threshold to detect white regions
        _, thresh = cv2.threshold(image, 10, 255, cv2.THRESH_BINARY)

        # Find contours instead of blob detection
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        output = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        dot_count = 0

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if 5 < area < 500:
                M = cv2.moments(cnt)
                if M["m00"] == 0:
                    continue
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                radius = int(np.sqrt(area / np.pi)) + 15
                cv2.circle(output, (cx, cy), radius, (0, 0, 255), thickness=-1)
                dot_count += 1

        #print(f"Detected and marked {dot_count} white dots.")
        return output, None

    except cv2.error:
        logger.error("E2017")
        return None, "E2017"

    except Exception as e:
        logger.error("E2018")
        return None, "E2018"



def det_angle(image, show=False):
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Threshold to get black center gap
        _, binary = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)

        # Focus only on central region
        h, w = binary.shape
        binary[:int(h * 0.15), :] = 0
        binary[int(h * 0.85):, :] = 0
        binary[:, :int(w * 0.15)] = 0
        binary[:, int(w * 0.85):] = 0

        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Filter contours near vertical center
        center_x = w // 2
        candidate_contours = []
        for cnt in contours:
            x, y, cw, ch = cv2.boundingRect(cnt)
            contour_center_x = x + cw // 2
            if abs(contour_center_x - center_x) < w * 0.2:
                candidate_contours.append(cnt)

        if not candidate_contours:
            logger.error("E2019")
            return None, "E2019"

        contour = max(candidate_contours, key=cv2.contourArea)

        # Fit a line
        [vx, vy, x0, y0] = cv2.fitLine(contour, cv2.DIST_L2, 0, 0.01, 0.01)
        scale = max(h, w)
        pt1 = (int(x0 - vx * scale), int(y0 - vy * scale))
        pt2 = (int(x0 + vx * scale), int(y0 + vy * scale))

        output = image.copy()
        cv2.line(output, pt1, pt2, (0, 255, 255), 2)

        # Compute angle
        angle_rad = math.atan2(vy, vx)
        angle_deg = math.degrees(angle_rad)
        if angle_deg < 0:
            angle_deg += 180

        print(f"Detected center gap angle: {angle_deg:.2f} degrees")

        # Show or save
        if show:
            cv2.imshow("Final Line Fit", cv2.resize(output, None, fx=0.5, fy=0.5))
            cv2.waitKey(0)
            cv2.destroyAllWindows()


        return angle_deg, None

    except cv2.error as e:
        logger.error("E2020")
        return None, "E2020"

    except Exception as e:
        logger.error("E2021")
        return None, "E2021"

