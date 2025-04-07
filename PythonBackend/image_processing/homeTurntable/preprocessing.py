import cv2
import numpy as np
from GeneralProc.logger import logger
import globals
from homeTurntable import *


def preprocess(image, scale_percent):
    """Resize the image for faster processing.
        Input: Grayscale image
        Output: Scaled image"""


    try:
        image=cv2.resize(image, None, fx=scale_percent / 100, fy=scale_percent / 100, interpolation=cv2.INTER_AREA)
        return image, None
    except cv2.error as e:
        logger.error("E2011")
        return None, "E2011"



def rotate_image(image, angle):
    """Rotate an image by a given angle around its center.
        Input: Scaled Grayscale image, angle of rotation
        Output: Rotated image"""
    try:
        center = (image.shape[1] // 2, image.shape[0] // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1)
        return cv2.warpAffine(image, rotation_matrix, (image.shape[1], image.shape[0]))
    except:
        return None


def crop_second_two_thirds(image):
    print(globals.x_end)
    try:
        cropped_image = image[:, :globals.x_end]
        return cropped_image, None
    except:
        return None, "E2211"


import cv2
import numpy as np
from GeneralProc import logger
import math

def fill_second_two_thirds(image, template,best_angle, scale=0.1, padding_ratio=0.25):
    scale_factor = 10 / 100.0
    try:
        small_image = cv2.resize(image, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_AREA)
        small_template = cv2.resize(template, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_AREA)
    except cv2.error as e:
        logger.error("E2111")
        return None, "E2111"

    try:
        result = cv2.matchTemplate(small_image, small_template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, small_top_left = cv2.minMaxLoc(result)
    except cv2.error as e:
        logger.error("E2112")
        return None, "E2112"

    top_left_x = round(small_top_left[0] / scale_factor)
    top_left_y = round(small_top_left[1] / scale_factor)

    # 4️⃣ Apply correction adjustments (if needed)
    adjustment1 = 4
    adjustment2 = 3
    corrected_top_left = (top_left_x + adjustment1, top_left_y + adjustment2)

    # Template size
    # Template size
    temp_h, temp_w = template.shape[:2]

    # Compute center of matched region (without padding)
    template_center_x = corrected_top_left[0] + temp_w // 2
    template_center_y = corrected_top_left[1] + temp_h // 2
    print(f"🎯 Center of matched template: ({template_center_x}, {template_center_y})")

    # Compute padding in pixels
    pad_x = int(temp_w * padding_ratio)
    pad_y = int(temp_h * padding_ratio)

    # Expand region with padding, clamped to image dimensions
    img_h, img_w = image.shape[:2]
    x1 = max(0, corrected_top_left[0] - pad_x)
    y1 = max(0, corrected_top_left[1] - pad_y)
    x2 = min(img_w, corrected_top_left[0] + temp_w + pad_x)
    y2 = min(img_h, corrected_top_left[1] + temp_h + pad_y)

    # Create blank mask
    mask_layer = np.zeros(image.shape[:2], dtype=np.uint8)
    mask_layer[y1:y2, x1:x2] = 255  # Apply white square to mask

    nonzero_coords = np.column_stack(np.where(mask_layer > 0))
    if len(nonzero_coords) == 0:
        logger.error("E2113")
        return None, "E2113"

    globals.x_end = int(np.min(nonzero_coords[:, 1]))
    try:
        with open("globals.py", "r") as file:
            lines = file.readlines()

        with open("globals.py", "w") as file:
            for line in lines:
                if line.startswith("x_end"):
                    file.write(f"x_end = {globals.x_end}\n")
                else:
                    file.write(line)
    except IOError as e:
        logger.error("E2114")
        return None, "E2114"

    print("Updated x_end in globals.py:", globals.x_end)

    # Apply the mask
    try:
        masked_image = cv2.bitwise_and(image, image, mask=mask_layer)
        # Crop to the padded region
        masked_image = masked_image[y1:y2, x1:x2]
        # Adjust center point to cropped image coordinates
        center_x_local = template_center_x - x1
        center_y_local = template_center_y - y1
        # Convert to color image if needed for drawing
        if len(masked_image.shape) == 2:
            masked_image = cv2.cvtColor(masked_image, cv2.COLOR_GRAY2BGR)

        # Draw the center point
        cv2.circle(masked_image, (center_x_local , center_y_local ), 5, (0, 0, 255), -1)  # red dot

    except cv2.error as e:
        logger.error("E2115")
        return None, "E2115"

    # Angle in degrees and convert to radians
    angle_deg = best_angle
    angle_rad = math.radians(angle_deg)

    # Direction vector
    dx = math.cos(angle_rad)
    dy = math.sin(angle_rad)

    # Line length (adjust as needed)
    line_len = 2000

    # Compute endpoints from the center
    x1_line = int(center_x_local - dx * line_len)
    y1_line = int(center_y_local - dy * line_len)
    x2_line = int(center_x_local + dx * line_len)
    y2_line = int(center_y_local + dy * line_len)

    # Draw the line through the center
    cv2.line(masked_image, (x1_line, y1_line), (x2_line, y2_line), (0, 255, 255), 10)
    cv2.putText(masked_image, "-170°", (x2_line + 5, y2_line),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

    # Create a blank mask same size as the cropped image
    line_mask = np.zeros(masked_image.shape[:2], dtype=np.uint8)


    # Draw the line as a filled thick strip on the mask
    line_thickness = 50  # You can adjust thickness of the region
    cv2.line(line_mask, (x1_line, y1_line), (x2_line, y2_line), 255, line_thickness)
    # Apply the line mask: keep only the line region, black out the rest
    line_only_image = cv2.bitwise_and(masked_image, masked_image, mask=line_mask)
    # cv2.imshow("line_region_masked", cv2.resize(line_only_image, None, fy=0.5, fx=0.5,interpolation=cv2.INTER_AREA) )
    # cv2.waitKey(0)
    # print("✅ Line region masked and saved as 'line_region_masked.png'")
    # Step: Convert to grayscale
    gray_line = cv2.cvtColor(line_only_image, cv2.COLOR_BGR2GRAY)

    # Threshold to isolate white dots
    _, thresh = cv2.threshold(gray_line, 100, 255, cv2.THRESH_BINARY)

    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    dot_count = 0
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if 5 < area < 500:  # Adjust thresholds for dot size
            dot_count += 1

    # Decide result
    result = "A" if dot_count > 0 else "B"
    print(f"📌 Final line-only dot evaluation: {result} (Dots found: {dot_count})")

    return masked_image,result, None









    # try:
    #     small_image = cv2.resize(image_full, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    #     small_template = cv2.resize(template_full, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    #
    #     result = cv2.matchTemplate(small_image, small_template, cv2.TM_CCOEFF_NORMED)
    #     _, _, _, small_top_left = cv2.minMaxLoc(result)
    # except cv2.error:
    #     logger.error("E2011 - Template matching failed.")
    #     return None, "E2011"
    #
    # top_left_x = int(round(small_top_left[0] / scale))
    # top_left_y = int(round(small_top_left[1] / scale))
    #
    # h_img, w_img = image_full.shape[:2]
    # h_temp, w_temp = template_full.shape[:2]
    #
    # top_left_x = max(0, min(top_left_x, w_img - 1))
    # top_left_y = max(0, min(top_left_y, h_img - 1))
    #
    # bottom_right_x = min(top_left_x + w_temp, w_img)
    # bottom_right_y = min(top_left_y + h_temp, h_img)
    #
    # if (bottom_right_x - top_left_x <= 0) or (bottom_right_y - top_left_y <= 0):
    #     logger.error("E2012 - Invalid mask region.")
    #     return None, "E2012"
    #
    # try:
    #     # Prepare a binary mask the same size as image_full
    #     full_mask = np.zeros(image_full.shape[:2], dtype=np.uint8)
    #
    #     # Convert template to grayscale and threshold to binary
    #     if len(template_full.shape) == 3:
    #         template_gray = cv2.cvtColor(template_full, cv2.COLOR_BGR2GRAY)
    #     else:
    #         template_gray = template_full
    #
    #     _, binary_template = cv2.threshold(template_gray, 1, 255, cv2.THRESH_BINARY)
    #
    #     # Insert the binary template into the correct subregion of full_mask
    #     h_sub, w_sub = binary_template.shape
    #     full_mask[top_left_y:top_left_y+h_sub, top_left_x:top_left_x+w_sub] = binary_template
    #
    #     # Apply mask to original image
    #     masked_image = cv2.bitwise_and(image_full, image_full, mask=full_mask)
    #
    # except cv2.error:
    #     logger.error("E2013 - Mask application failed.")
    #     return None, "E2013"
    # visualize=1
    # if visualize:
    #     vis_image = image_full.copy()
    #     color = (0, 255, 0) if len(vis_image.shape) == 3 else 255
    #     cv2.rectangle(vis_image, (top_left_x, top_left_y), (bottom_right_x, bottom_right_y), color, 2)
    #     cv2.imshow("match_visualization.png", cv2.resize(vis_image, None, fy=0.2, fx=0.2, interpolation=cv2.INTER_AREA))
    #     cv2.waitKey(0)
    #     print("Saved visualization to 'match_visualization.png'")
    #
    # return masked_image, None
    # col_sums = np.sum(gray_image, axis=0)
    # row_sums = np.sum(gray_image, axis=1)
    # non_black_cols = np.where(col_sums > 0)[0]
    # non_black_rows = np.where(row_sums > 0)[0]
    #
    # if len(non_black_cols) == 0 or len(non_black_rows) == 0:
    #     logger.error("E2014 - No content found after masking.")
    #     return None, "E2014"
    #
    # first_col, last_col = non_black_cols[0], non_black_cols[-1]
    # first_row, last_row = non_black_rows[0], non_black_rows[-1]
    #
    # # Save crop offset to map back later
    # crop_offset_x = first_col
    # crop_offset_y = first_row
    #
    # cropped_image = masked_image[first_row:last_row + 1, first_col:last_col + 1]
    # rotated_target2 = cv2.resize(cropped_image, None, fx=0.2, fy=0.2, interpolation=cv2.INTER_AREA)
    # cv2.imshow("RotatedImage", rotated_target2)
    # cv2.waitKey(0)
    #
    # if len(cropped_image.shape) == 3:
    #     gray_cropped = cv2.cvtColor(cropped_image, cv2.COLOR_BGR2GRAY)
    # else:
    #     gray_cropped = cropped_image.copy()
    #
    # _, thresh_dots = cv2.threshold(gray_cropped, 10, 255, cv2.THRESH_BINARY)
    # contours_dots, _ = cv2.findContours(thresh_dots, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    #
    # dot_x = []
    # dot_y = []
    # for cnt in contours_dots:
    #     area = cv2.contourArea(cnt)
    #     if 5 < area < 500:
    #         M = cv2.moments(cnt)
    #         if M["m00"] == 0:
    #             continue
    #         cx = int(M["m10"] / M["m00"])
    #         cy = int(M["m01"] / M["m00"])
    #         dot_x.append(cx)
    #         dot_y.append(cy)
    #
    # if dot_x and dot_y:
    #     left = max(0, min(dot_x))
    #     right = min(cropped_image.shape[1], max(dot_x))
    #     top = max(0, min(dot_y))
    #     bottom = min(cropped_image.shape[0], max(dot_y))
    #
    #     pad = 5
    #     left = max(0, left - pad)
    #     right = min(cropped_image.shape[1], right + pad)
    #     top = max(0, top - pad)
    #     bottom = min(cropped_image.shape[0], bottom + pad)
    #
    #     cropped_image = cropped_image[top:bottom + 1, left:right + 1]
    #
    # dot_pts = np.array(list(zip(dot_x, dot_y)), dtype=np.float32)
    # center_x = np.mean(dot_x)
    # center_y = np.mean(dot_y)
    # distances = [math.hypot(x - center_x, y - center_y) for x, y in zip(dot_x, dot_y)]
    # radius = max(distances)
    #
    # output = gray_cropped.copy()
    # cv2.circle(output, (int(center_x), int(center_y)), int(radius), (0, 255, 0), 2)
    # cv2.circle(output, (int(center_x), int(center_y)), 3, (0, 0, 255), -1)
    # cv2.imshow("Better Fitted Circle", output)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()
    #
    # allowed_margin = 10
    # dots_on_circle = []
    #
    # for x, y in zip(dot_x, dot_y):
    #     dist = math.hypot(x - center_x, y - center_y)
    #     if abs(dist - radius) <= allowed_margin:
    #         dots_on_circle.append((x, y))
    #
    # dot_angles = []
    # for x, y in dots_on_circle:
    #     angle = math.atan2(y - center_y, x - center_x)
    #     dot_angles.append(angle)
    #
    # dot_angles = [a if a >= 0 else a + 2 * math.pi for a in dot_angles]
    # dot_angles.sort()
    #
    # gaps = []
    # for i in range(len(dot_angles)):
    #     current = dot_angles[i]
    #     next_angle = dot_angles[(i + 1) % len(dot_angles)]
    #     gap = (next_angle - current) % (2 * math.pi)
    #     gaps.append((gap, current, next_angle))
    #
    # gaps.sort(reverse=True, key=lambda g: g[0])
    # largest_gap_1 = gaps[0]
    # largest_gap_2 = gaps[1]
    #
    # print("🔓 Largest gap 1:", math.degrees(largest_gap_1[0]), "degrees between",
    #       math.degrees(largest_gap_1[1]), "→", math.degrees(largest_gap_1[2]))
    # print("🔓 Largest gap 2:", math.degrees(largest_gap_2[0]), "degrees between",
    #       math.degrees(largest_gap_2[1]), "→", math.degrees(largest_gap_2[2]))
    #
    # a1_1 = largest_gap_1[1]
    # a2_1 = largest_gap_1[2]
    # x1_1 = int(center_x + radius * math.cos(a1_1))
    # y1_1 = int(center_y + radius * math.sin(a1_1))
    # x2_1 = int(center_x + radius * math.cos(a2_1))
    # y2_1 = int(center_y + radius * math.sin(a2_1))
    #
    # a1_2 = largest_gap_2[1]
    # a2_2 = largest_gap_2[2]
    # x1_2 = int(center_x + radius * math.cos(a1_2))
    # y1_2 = int(center_y + radius * math.sin(a1_2))
    # x2_2 = int(center_x + radius * math.cos(a2_2))
    # y2_2 = int(center_y + radius * math.sin(a2_2))
    #
    # if len(output.shape) == 2:
    #     output = cv2.cvtColor(output, cv2.COLOR_GRAY2BGR)
    #
    # cv2.line(output, (x1_1, y1_1), (x2_1, y2_1), (255, 0, 255), 2)
    # cv2.putText(output, "Gap 1", ((x1_1 + x2_1) // 2, (y1_1 + y2_1) // 2),
    #             cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)
    # cv2.line(output, (x1_2, y1_2), (x2_2, y2_2), (0, 255, 255), 2)
    # cv2.putText(output, "Gap 2", ((x1_2 + x2_2) // 2, (y1_2 + y2_2) // 2),
    #             cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    #
    # cv2.imshow("Gaps on Circle", output)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()
    #
    # # Map center from cropped_image to image_full
    # global_center_x = int(center_x + crop_offset_x)
    # global_center_y = int(center_y + crop_offset_y)
    # crop_radius = int(radius * 1.4)
    #
    # # Coordinates of the large crop from original image
    # x1 = max(0, global_center_x - crop_radius)
    # x2 = min(image_full.shape[1], global_center_x + crop_radius)
    # y1 = max(0, global_center_y - crop_radius)
    # y2 = min(image_full.shape[0], global_center_y + crop_radius)
    #
    # # Crop from original image
    # large_crop = image_full[y1:y2, x1:x2]
    #
    # # Draw the gap lines on the large crop
    # # Step 1: Compute global coordinates of gap points
    # gap_points_global = []
    #
    # for a1, a2 in [(largest_gap_1[1], largest_gap_1[2]), (largest_gap_2[1], largest_gap_2[2])]:
    #     gx1 = int(global_center_x + radius * math.cos(a1))
    #     gy1 = int(global_center_y + radius * math.sin(a1))
    #     gx2 = int(global_center_x + radius * math.cos(a2))
    #     gy2 = int(global_center_y + radius * math.sin(a2))
    #     gap_points_global.append(((gx1, gy1), (gx2, gy2)))
    #
    # # Step 2: Draw on large_crop (adjusted by the crop offset x1, y1)
    # if len(large_crop.shape) == 2:
    #     large_crop = cv2.cvtColor(large_crop, cv2.COLOR_GRAY2BGR)
    #
    # cv2.circle(large_crop, (global_center_x - x1, global_center_y - y1), int(radius), (0, 255, 0), 2)
    #
    # colors = [(255, 0, 255), (0, 255, 255)]
    # for idx, ((pt1x, pt1y), (pt2x, pt2y)) in enumerate(gap_points_global):
    #     pt1_rel = (pt1x - x1, pt1y - y1)
    #     pt2_rel = (pt2x - x1, pt2y - y1)
    #     color = colors[idx]
    #     cv2.line(large_crop, pt1_rel, pt2_rel, color, 2)
    #     mid_x = (pt1_rel[0] + pt2_rel[0]) // 2
    #     mid_y = (pt1_rel[1] + pt2_rel[1]) // 2
    #     cv2.putText(large_crop, f"Gap {idx + 1}", (mid_x, mid_y),
    #                 cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    #
    # # Show final visual result
    # cv2.imshow("Gaps on Large Original Crop", large_crop)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()
    #
    # # Step 1: Get midpoint of each gap (in relative crop coords)
    # gap1_pt1, gap1_pt2 = gap_points_global[0]
    # gap2_pt1, gap2_pt2 = gap_points_global[1]
    #
    # gap1_mid = ((gap1_pt1[0] + gap1_pt2[0]) // 2 - x1, (gap1_pt1[1] + gap1_pt2[1]) // 2 - y1)
    # gap2_mid = ((gap2_pt1[0] + gap2_pt2[0]) // 2 - x1, (gap2_pt1[1] + gap2_pt2[1]) // 2 - y1)
    #
    # # Step 2: Compute direction vector
    # dx = gap2_mid[0] - gap1_mid[0]
    # dy = gap2_mid[1] - gap1_mid[1]
    #
    # # Normalize direction
    # length = math.hypot(dx, dy)
    # if length == 0:
    #     return cropped_image, "E9999 - Midpoints are identical"
    # dx /= length
    # dy /= length
    #
    # # Step 3: Extend line in both directions
    # h, w = large_crop.shape[:2]
    # line_pts = []
    #
    # for scale in [-2000, 2000]:  # Large enough range to go outside crop
    #     x = int(gap1_mid[0] + dx * scale)
    #     y = int(gap1_mid[1] + dy * scale)
    #     line_pts.append((x, y))
    #
    # # Step 4: Draw line on large_crop
    # cv2.line(large_crop, line_pts[0], line_pts[1], (0, 0, 255), 2)  # Red line
    #
    # # Optional: mark midpoints
    # cv2.circle(large_crop, gap1_mid, 5, (255, 0, 0), -1)
    # cv2.circle(large_crop, gap2_mid, 5, (0, 255, 0), -1)
    #
    # # Show final result
    # cv2.imshow("Extended Line Through Gaps", large_crop)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()
    #
    # # Step 1: Create a mask
    # mask = np.zeros(large_crop.shape[:2], dtype=np.uint8)
    #
    # # Step 2: Draw a white line between the two midpoints
    # cv2.line(mask, gap1_mid, gap2_mid, 255, 20)  # white line on black
    # # Show final result
    #
    #
    # # Step 3: Convert large_crop to grayscale if needed
    # if len(large_crop.shape) == 3:
    #     gray_large_crop = cv2.cvtColor(large_crop, cv2.COLOR_BGR2GRAY)
    # else:
    #     gray_large_crop = large_crop.copy()
    #
    # # Step 4: Extract the pixels along the line
    # line_pixels = gray_large_crop[mask == 255]
    #
    # mean_intensity = np.mean(line_pixels)
    # found_black = mean_intensity < 30  # or another threshold, e.g. 50
    #
    # print(f"📏 Mean intensity along line: {mean_intensity:.2f}")
    # print("🟡 Line is dark" if found_black else "✅ Line is bright enough")
    #
    # # Step 2: Draw a white line between the two midpoints
    # line_thickness = 50
    # cv2.line(mask, line_pts[0], line_pts[1], 255, line_thickness)
    # # Convert large_crop to color if it's grayscale
    # if len(large_crop.shape) == 2:
    #     large_crop_color = cv2.cvtColor(large_crop, cv2.COLOR_GRAY2BGR)
    # else:
    #     large_crop_color = large_crop.copy()
    #
    # # Create a red overlay mask using the white line
    # overlay = np.zeros_like(large_crop_color)
    # overlay[mask == 255] = (0, 0, 255)  # Red line
    #
    # # Blend the red line onto the image
    # visual = cv2.addWeighted(large_crop_color, 0.8, overlay, 0.5, 0)
    #
    # # Show it
    # cv2.imshow("Scan Line Over Large Crop", visual)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()
    # # Optionally: return it
    #
    # # Step 1: Get the line equation from the extended line on large_crop
    # x1, y1 = line_pts[0]
    # x2, y2 = line_pts[1]
    #
    # A = y2 - y1
    # B = x1 - x2
    # C = x2 * y1 - x1 * y2
    # norm = math.hypot(A, B)
    # distance_threshold = 1  # pixels
    #
    # # === Final accurate dot-on-line detection ===
    # dots_on_line = []
    #
    # # Use line mask already drawn earlier with line_pts and line_thickness
    # # Check if dot centers fall inside the mask (i.e., white line area)
    # for x_local, y_local in zip(dot_x, dot_y):
    #     # Convert to image_full coordinates
    #     x_full = int(x_local + crop_offset_x)
    #     y_full = int(y_local + crop_offset_y)
    #
    #     # Convert to large_crop-relative coordinates
    #     x_rel = x_full - x1
    #     y_rel = y_full - y1
    #
    #     if 0 <= x_rel < mask.shape[1] and 0 <= y_rel < mask.shape[0]:
    #         if mask[y_rel, x_rel] == 255:
    #             dots_on_line.append((x_rel, y_rel))
    #
    # print(f"🔎 Number of dots on or near the extended line: {len(dots_on_line)}")
    #
    # # ✅ Optional: draw them on large_crop
    # for (x, y) in dots_on_line:
    #     cv2.circle(large_crop, (x, y), 5, (0, 255, 0), -1)
    #
    # # Show result with marked dots on the line
    # cv2.imshow("Dots on Scan Line", large_crop)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()
    #
    # # Or if this is part of the bigger function, maybe:
    # # return cropped_image, None, found_black
    # return cropped_image, None
    #
    #
    #

