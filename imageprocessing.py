import cv2
import numpy as np
import os
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import matplotlib.pyplot as plt
import time
from collections import Counter, defaultdict

import globals


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


#PROCESS CENTER CAMERA - CIRCLE
def process_center(image):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(script_dir, 'templ03_mod3.jpg')
    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)

    if image is None or template is None:
        raise FileNotFoundError("Target or template image not found. Check the file paths.")

    # Step 1: Crop the input image

    # Step 2: Match and extract the template region
    matched_region = center_template_match_and_extract(template, image)

    # Step 4: Detect small dots and extract their contours and areas
    dot_contours, annotated_dots = center_detect_small_dots_and_contours(matched_region)

    # Define the filename with timestamp
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"result_circle_{timestamp}.jpg"
    cv2.imwrite(os.path.join(script_dir, filename), annotated_dots)

    return dot_contours

def center_template_match_and_extract(template, image):

    template_height, template_width = template.shape
    result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)

    # Get the location of the best match
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    # Extract the best-matched region
    top_left = max_loc
    # Ensure the mask size matches the template
    adjustment1 = 5  # Try values like -1, -2 to see if it corrects the shift
    adjustment2 = 5
    corrected_top_left = (top_left[0] + adjustment1, top_left[1] + adjustment2)
    corrected_bottom_right = (corrected_top_left[0] + template_width, corrected_top_left[1] + template_height)
    # Create a blank mask of the same size as the cropped image
    mask_layer = np.zeros_like(image, dtype=np.uint8)
    mask_layer[corrected_top_left[1]:corrected_bottom_right[1],
    corrected_top_left[0]:corrected_bottom_right[0]] = template

    nonzero_coords = np.column_stack(np.where((mask_layer) > 0))  # Get all nonzero pixel coordinates

    if len(nonzero_coords) > 0:
        globals.x_end = int(np.min(nonzero_coords[:, 1]))

        # Write updated x_end back to globals.py
        with open("globals.py", "r") as file:
            lines = file.readlines()

        with open("globals.py", "w") as file:
            for line in lines:
                if line.startswith("x_end"):
                    file.write(f"x_end = {globals.x_end}\n")  # Update it
                else:
                    file.write(line)  # Keep other lines unchanged

        print("Updated x_end in globals.py:", globals.x_end)

    # Apply the mask on the cropped image using bitwise operation
    masked_image = cv2.bitwise_and(image, image, mask=mask_layer)

    return masked_image

def center_detect_small_dots_and_contours(masked_region):

    # Threshold the masked region
    _, thresh = cv2.threshold(masked_region, 100, 255, cv2.THRESH_BINARY)

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
    df = pd.DataFrame(dot_area_column_mapping, columns=['X', 'Y', 'Column', 'Area'])
    df.to_csv('dot_areas_with_columns.csv', index=False)
    return dot_area_column_mapping, annotated_dots



#PROCESS CENTER CAMERA - SLICE

def process_inner_slice(image):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(script_dir, 'templ08_c.jpg')
    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)

    if image is None or template is None:
        raise FileNotFoundError("Target or template image not found. Check the file paths.")
        # Step 1: Crop the input image
    cropped_image = islice_crop_second_two_thirds(image)
    # Step 2: Match the polygonal template and extract the masked region
    polygon_region = islice_template_match_with_polygon(cropped_image, template)
    globals.latest_image = polygon_region
    
    # Step 3: Detect small dots in the polygon region
    dot_contours, annotated_dots, grouped_x = islice_detect_small_dots_and_contours(polygon_region)

    # Define the filename with timestamp
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"result_pizza_{timestamp}.jpg"
    # Save the image in the script directory
    cv2.imwrite(os.path.join(script_dir, filename), annotated_dots)

    #print(dot_contours)
    return dot_contours

def islice_crop_second_two_thirds(image):
    print(globals.x_end)
    cropped_image = image[:, :globals.x_end]
    return cropped_image

def islice_template_match_with_polygon(cropped_image, template, start_x=0, start_y=0):

    best_match = None
    best_max_val = -1
    best_top_left = None
    result = cv2.matchTemplate(cropped_image, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val > best_max_val:
            best_max_val = max_val
            best_match = template
            best_top_left = (max_loc[0] + start_x, max_loc[1] + start_y)  # Offset by search region

    # Validate the best match
    if best_max_val < 0:  # Adjust threshold for confidence
        raise ValueError("Template match confidence is too low.")

    # Get the region where the template matches
    best_template_height, best_template_width = best_match.shape
    top_left = best_top_left
    bottom_right = (top_left[0] + best_template_width, top_left[1] + best_template_height)
    matched_region = cropped_image[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]]

    # Create the original binary mask (1 inside, 0 outside)
    original_mask = np.zeros_like(best_match, dtype=np.uint8)
    original_mask[best_match > 10] = 1  # Threshold only the mask, NOT the image

    # **Step 1: Expand the mask by 15 pixels**
    kernel = np.ones((35, 35), np.uint8)  # 15 pixels in each direction (total size 31x31)
    expanded_mask = cv2.dilate(original_mask, kernel, iterations=1)

    # **Step 2: Create the 15-pixel white boundary**
    boundary_mask = expanded_mask - original_mask  # Subtract original to get only boundary

    # **Step 3: Set boundary to white (255), and keep the original mask as 1**
    final_mask = np.copy(expanded_mask)
    final_mask[boundary_mask == 1] = 255  # Set boundary pixels to white
    final_mask[original_mask == 1] = 1  # Keep the original mask as 1

    # **Apply the final mask to the matched region**
    masked_polygon_region = cv2.bitwise_and(matched_region, matched_region, mask=expanded_mask)

    return masked_polygon_region


def generate_gradient_colors(n):
    colormap = plt.cm.get_cmap('jet', n)
    return [(int(255 * r), int(255 * g), int(255 * b)) for r, g, b, _ in colormap(np.linspace(0, 1, n))]

def islice_detect_small_dots_and_contours(masked_region, x_threshold=40):

    # Apply threshold to find dots
    _, thresh = cv2.threshold(masked_region, 100, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # **Extract dot centers and filter out zero-area contours**
    dot_centers = []
    dot_areas = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > 1:  # Ignore zero-area dots
            (x, y), _ = cv2.minEnclosingCircle(contour)
            dot_centers.append((int(x), int(y)))
            dot_areas.append(area)
    dot_centers = np.array(dot_centers, dtype=np.int32)
    if len(dot_centers) < 2:
        print("Not enough dots for clustering.")
        return dot_centers, masked_region, {}

    # **Step 1: Sort dots by X-coordinate (left to right), then by Y-coordinate**
    sorted_indices = np.lexsort((-dot_centers[:, 1], -dot_centers[:, 0]))  # Reverse X and Y sorting
    dot_centers = dot_centers[sorted_indices]
    dot_areas = np.array(dot_areas)[sorted_indices]
    # **Identify Rows & Exclude Last Two Rows**
    unique_y_values = np.unique(dot_centers[:, 1])  # Unique Y-coordinates (row positions)
    if len(unique_y_values) > 2:
        excluded_rows = unique_y_values[-2:]  # Last two unique Y-values
        mask = ~np.isin(dot_centers[:, 1], excluded_rows)  # Mask to filter out last two rows
        dot_centers = dot_centers[mask]
        dot_areas = dot_areas[mask]

    # **Step 2: Iteratively find columns**
    columns = []
    column_labels = {}
    dot_area_column_mapping = []
    while len(dot_centers) > 0:
        # Start a new column with the leftmost unassigned dot
        first_dot = dot_centers[0]
        new_column = [first_dot]
        new_column_areas = [dot_areas[0]]
        # Find dots that belong to this column
        remaining_dots = []
        remaining_areas = []
        for i in range(1, len(dot_centers)):
            dot = dot_centers[i]
            area = dot_areas[i]
            if abs(dot[0] - first_dot[0]) <= x_threshold:
                new_column.append(dot)
                new_column_areas.append(area)
            else:
                remaining_dots.append(dot)
                remaining_areas.append(area)
        # Assign column index
        col_idx = len(columns)
        for i, dot in enumerate(new_column):
            column_labels[tuple(dot)] = col_idx
            dot_area_column_mapping.append((dot[0], dot[1], col_idx, new_column_areas[i]))
        columns.append(new_column)
        dot_centers = np.array(remaining_dots)
        dot_areas = np.array(remaining_areas)

    # **Step 3: Remove Last Two Columns**
    num_columns = len(columns)
    if num_columns > 2:
        columns = columns[:-5]  # Remove last two columns
        valid_column_indices = set(range(num_columns - 5))  # Keep only valid column indices
    else:
        valid_column_indices = set(range(num_columns))  # Keep all if there are 2 or fewer columns

    # **Step 4: Modify Column Indexing**
    # Extract all x-coordinates
    x_values = [x for x, _, _, _ in dot_area_column_mapping]
    # Find the minimum x-coordinate
    max_x = max(x_values) if x_values else None

    if max_x is not None and max_x < 2600:
        counter = 2  # Start numbering from 1
        print("The first column is missing!")
    else:
        counter = 1
    column_mapping = {}


    filtered_dot_area_column_mapping = []
    for x, y, col, area in dot_area_column_mapping:
        if col in valid_column_indices:
            if col not in column_mapping:  # Assign a new index
                column_mapping[col] = counter
                counter += 1
            new_col = column_mapping[col]  # Use assigned index

            filtered_dot_area_column_mapping.append((x, y, new_col, area))

    # **Step 3.1: Detect missing columns by analyzing spacing**
    column_x_positions = [min(col, key=lambda d: d[0])[0] for col in columns if
                          len(col) > 0]  # Get leftmost dot X in each column

    # Sort detected column positions
    column_x_positions.sort()
    # Compute distances between adjacent columns
    missing_columns = []
    missing_column_pairs = []  # Store which columns the missing ones are between
    missing_column_labels = {}
    if len(column_x_positions) > 1:
        column_distances = np.diff(column_x_positions)
        # Compute median column spacing (ignoring large outliers)
        median_spacing = np.median(column_distances)
        # Identify missing columns by checking large gaps
        for i in range(len(column_distances)):
            gap_size = column_distances[i]
            if gap_size > 1.5 * median_spacing:  # Large gap means missing columns
                num_missing = round(gap_size / median_spacing) - 1  # Estimate missing column count
                # Insert multiple missing columns in the large gap
                for j in range(1, num_missing + 1):
                    estimated_x = column_x_positions[i] + int(j * median_spacing)
                    missing_columns.append(estimated_x)
                    # Store which columns this missing column is between
                    missing_column_pairs.append((column_x_positions[i], column_x_positions[i + 1]))

                    # **Assign missing column label**
                    missing_column_labels[
                        (estimated_x, -1)] = f"Missing between {column_x_positions[i]} and {column_x_positions[i + 1]}"

    # Print detected missing columns with their locations
    if missing_columns:
        # Step 1: Create a dictionary to map X positions to column numbers
        x_to_col_number = {x: col for x, y, col, area in filtered_dot_area_column_mapping}

        # Step 2: Get column numbers for missing columns' surrounding existing columns
        for missing_x, (left_col, right_col) in zip(missing_columns, missing_column_pairs):
            left_col_number = x_to_col_number.get(left_col, f"Unknown Col at {left_col}")
            right_col_number = x_to_col_number.get(right_col, f"Unknown Col at {right_col}")

            print(
                f"Missing column at X={missing_x} is between column {left_col_number} (X={left_col}) and column {right_col_number} (X={right_col})")

        # **Update column_labels dictionary**
        for x_missing, label in missing_column_labels.items():
            column_labels[x_missing] = label  # Store missing column information

    # Step 1: Find the next available column number
    next_column_number = max(column_mapping.values(), default=0) + 1

    # Step 2: Insert missing columns into filtered_dot_area_column_mapping
    for missing_x, (left_col, right_col) in zip(missing_columns, missing_column_pairs):
        left_col_number = x_to_col_number[left_col]
        right_col_number = x_to_col_number[right_col]

        # Assign a new column number for the missing column
        if (missing_x not in x_to_col_number):  # Avoid duplicates
            x_to_col_number[missing_x] = next_column_number
            column_mapping[missing_x] = next_column_number
            next_column_number += 1  # Increment for the next missing column

        # Insert into filtered_dot_area_column_mapping with default values (adjust as needed)
        filtered_dot_area_column_mapping.append((missing_x, -1, x_to_col_number[missing_x], 0))

    # Step 3: Sort filtered_dot_area_column_mapping by X position to maintain order
    filtered_dot_area_column_mapping.sort(key=lambda item: item[0])

    # Step 1: Create a dictionary mapping X positions to column numbers
    x_to_col_number = {x: col for x, y, col, area in filtered_dot_area_column_mapping}

    # Step 2: Identify missing columns dynamically
    missing_counts = {}
    missing_blocks = defaultdict(list)

    for missing_x, (left_col, right_col) in zip(missing_columns, missing_column_pairs):
        missing_blocks[(left_col, right_col)].append(missing_x)

    for (left_col, right_col), missing_x_positions in missing_blocks.items():
        missing_counts[(left_col, right_col)] = len(missing_x_positions)

    # Step 3: Sort columns and initialize tracking variables
    sorted_x_positions = sorted(x_to_col_number.keys())
    updated_mapping = {}  # Stores new column assignments
    cumulative_shift = 0  # Tracks total shifts applied
    col_shift_mapping = {}  # Maps original columns to their shifted values

    # Step 4: Assign missing columns and compute shifts dynamically
    for x in sorted_x_positions:
        original_col = x_to_col_number[x]

        # If the column was already assigned a shift, use it
        if original_col in col_shift_mapping:
            new_col = col_shift_mapping[original_col]
        else:
            # Apply cumulative shift dynamically
            new_col = original_col + cumulative_shift
            col_shift_mapping[original_col] = new_col

        updated_mapping[x] = new_col

        # Update shift when encountering a missing column range
        if x in missing_columns:
            cumulative_shift += 1  # Increment shift for each missing column detected


    # Step 6: Update filtered_dot_area_column_mapping with correct column numbers
    filtered_dot_area_column_mapping = sorted([
        (x, y, updated_mapping.get(x, col), area) for x, y, col, area in filtered_dot_area_column_mapping
    ], key=lambda row: row[0])

    # **Step 6: Count dots per column**
    column_dot_counts = {col_idx: sum(1 for _, _, col, _ in filtered_dot_area_column_mapping if col == col_idx) for
                         col_idx in valid_column_indices}

    # **Step 8: Annotate the image (excluding last two columns)**
    annotated_dots = cv2.cvtColor(masked_region, cv2.COLOR_GRAY2BGR)
    # Step 1: Identify the correct numbering for missing columns
    missing_column_replacements = {}
    cumulative_shift = 0  # Tracks the total number of missing columns added so far

    # Iterate over the missing blocks and assign correct numbering
    for (left_col, right_col), missing_x_positions in sorted(missing_blocks.items()):
        left_col_number = x_to_col_number[left_col]  # Known column before the missing block
        right_col_number = x_to_col_number[right_col]  # Known column after the missing block

        # Assign missing columns dynamically, while accounting for prior shifts
        for i, missing_x in enumerate(missing_x_positions):
            new_col_number = left_col_number + 1 + i + cumulative_shift  # Assign sequentially with shift
            missing_column_replacements[missing_x] = new_col_number

        # Update cumulative shift after assigning missing columns in this block
        cumulative_shift += len(missing_x_positions)

    # Step 2: Update only missing columns in updated_mapping
    for missing_x in missing_columns:
        if missing_x in missing_column_replacements:
            updated_mapping[missing_x] = missing_column_replacements[missing_x]

    # Step 4: Apply updated mapping to filtered_dot_area_column_mapping
    filtered_dot_area_column_mapping = sorted([
        (x, y, updated_mapping.get(x, col), area) for x, y, col, area in filtered_dot_area_column_mapping
    ], key=lambda row: row[0])

    valid_column_indices2 = set(range(min(51, num_columns)))
    # **Step 5: Assign colors to columns**
    colors = generate_gradient_colors(len(valid_column_indices2))
    column_colors = {col_idx: colors[i] for i, col_idx in enumerate(valid_column_indices2)}
    for (x, y, col_label, area) in filtered_dot_area_column_mapping:
        if col_label in valid_column_indices2:  # Only annotate valid columns
            color = column_colors[col_label]

            # Draw dot
            cv2.circle(annotated_dots, (x, y), 3, color, -1)

            # Draw enclosing circle
            cv2.circle(annotated_dots, (x, y), int(np.sqrt(area / np.pi)), (0, 255, 0), 1)  # Green circle

            # Display dot area near the dot
            cv2.putText(annotated_dots, f"{int(area)}", (x + 10, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)  # Yellow text for area

            # Display column number near the dot
            cv2.putText(annotated_dots, f"Col {col_label}", (x - 10, y + 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)  # White text for column
        # **Step 8.1: Highlight Missing Columns**
        for x_missing in missing_columns:
            height = annotated_dots.shape[0]  # Get image height for full vertical line
            for y in range(0, height, 10):  # Draw dashed lines (10px spacing)
                if y % 20 == 0:
                    cv2.line(annotated_dots, (x_missing, y), (x_missing, y + 10), (0, 0, 255), 2)  # Red dashed line

            # Label the missing column
            cv2.putText(annotated_dots, "MISSING", (x_missing - 20, 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)  # Red text for missing columns
        # **Step 9: Save dot areas with column numbers (excluding last two columns)**
        # Define the column names
    columns = ['X', 'Y', 'Column', 'Area']
    filtered_dot_area_column_mapping2 = [
        (x, y, col_label, area)
        for (x, y, col_label, area) in filtered_dot_area_column_mapping
        if col_label in valid_column_indices2
    ]
    # Convert filtered_dot_area_column_mapping to a DataFrame
    new_data = pd.DataFrame(filtered_dot_area_column_mapping2, columns=columns)

    # Check if the file already exists
    file_path = 'dot_areas_with_columns.csv'
    if os.path.exists(file_path):
        # If the file exists, read it
        existing_data = pd.read_csv(file_path)
        # Append the new data to the existing data
        updated_data = pd.concat([existing_data, new_data], ignore_index=True)
    else:
        # If the file doesn't exist, use the new data as the dataset
        updated_data = new_data

    # Save the updated data back to CSV
    updated_data.to_csv(file_path, index=False)
    # for i, dot in enumerate(filtered_dot_area_column_mapping2):
    #    print(f"Dot {i + 1}: X = {dot[0]}, Y = {dot[1]}, Column = {dot[2]}, Area = {dot[3]}")
    # Extract column labels
    column_counts = {}

    # Count occurrences of each column
    for entry in filtered_dot_area_column_mapping2:
        column_label = entry[2]  # Third value in the tuple
        column_counts[column_label] = column_counts.get(column_label, 0) + 1
    # Generate the formatted output
    output = "\n".join([f"Col {col}: {count} dots" for col, count in column_counts.items()])

    return filtered_dot_area_column_mapping2, annotated_dots, column_dot_counts


#PROCESS SIDE CAMERA - SLICE
def start_side_slice(image):
    cropped_image =  image
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(script_dir, 'templ05_mod2.jpg')
    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)

    polygon_region, annotated_image, polygon_mask = template_match_with_polygon(cropped_image, template)


    # Step 3: Detect small dots in the polygon region
    dot_contours, annotated_dots, grouped_x,matching_column = detect_small_dots_and_contours(polygon_region)

    return dot_contours




def template_match_with_polygon(cropped_image, template):


    if template is None:
        raise FileNotFoundError(f"Template not found at {template}")

    template_height, template_width = template.shape
    best_match = None
    best_max_val = -1
    best_scale = 1.0
    best_top_left = None

    # Multi-scale template matching
    scales = np.linspace(1, 1.2, 1)  # Adjust scales to search (e.g., 84% to 100%)
    for scale in scales:
        resized_template = cv2.resize(template, (int(template_width * scale), int(template_height * scale)))
        result = cv2.matchTemplate(cropped_image, resized_template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val > best_max_val:
            best_max_val = max_val
            best_match = resized_template
            best_top_left = max_loc
            best_scale = scale

    # Validate the best match
    if best_max_val < 0:  # Adjust threshold for confidence
        raise ValueError("Template match confidence is too low.")

    # Get the region where the template matches
    best_template_height, best_template_width = best_match.shape
    top_left = best_top_left
    bottom_right = (top_left[0] + best_template_width, top_left[1] + best_template_height)
    matched_region = cropped_image[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]]

    # Create the original binary mask (1 inside, 0 outside)
    original_mask = np.zeros_like(best_match, dtype=np.uint8)
    original_mask[best_match > 10] = 1  # Threshold only the mask, NOT the image

    # **Step 1: Expand the mask by 15 pixels**
    kernel = np.ones((200, 200), np.uint8)  # 15 pixels in each direction (total size 31x31)
    expanded_mask = cv2.dilate(original_mask, kernel, iterations=1)

    # **Step 2: Create the 15-pixel white boundary**
    boundary_mask = expanded_mask - original_mask  # Subtract original to get only boundary

    # **Step 3: Set boundary to white (255), and keep the original mask as 1**
    final_mask = np.copy(expanded_mask)
    final_mask[boundary_mask == 1] = 255  # Set boundary pixels to white
    final_mask[original_mask == 1] = 1    # Keep the original mask as 1

    # **Apply the final mask to the matched region**
    masked_polygon_region = cv2.bitwise_and(matched_region, matched_region, mask=expanded_mask)
    
    globals.latest_image = masked_polygon_region

    # Annotate the matched polygon on the cropped image
    annotated_image = cv2.cvtColor(cropped_image, cv2.COLOR_GRAY2BGR)
    cv2.rectangle(annotated_image, top_left, bottom_right, (0, 255, 0), 2)
    cv2.putText(annotated_image, f"Scale: {best_scale:.2f}", (top_left[0], top_left[1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)



    return masked_polygon_region, annotated_image, final_mask




def find_first_column(dot_centers, x_threshold=0):
    """
    Finds the first column by identifying the leftmost dots and moving downward,
    ensuring all dots in the first column belong to the same X range.
    """

    # Sort dots by X first, then Y (ensures left-to-right processing)
    dot_centers = dot_centers[np.lexsort((dot_centers[:, 0], dot_centers[:, 1]))]

    # Get the leftmost-topmost dot as the first point
    first_dot = tuple(dot_centers[0])
    first_column = [first_dot]

    # Convert remaining dots to a list of tuples for easy processing
    remaining_dots = [tuple(dot) for dot in dot_centers[1:]]

    # Determine column X width dynamically (average of closest X gaps)
    x_values = dot_centers[:, 0]
    x_diffs = np.diff(np.sort(x_values))

    if len(x_diffs) > 0:
        median_x_gap = np.median(x_diffs[x_diffs > 0])  # Ignore zero gaps
        separation_threshold = max(15, min(median_x_gap * 2, 60))  # Allow a slightly wider threshold
        separation_threshold0 = -separation_threshold
    else:
        separation_threshold = 30  # Fallback value

    while True:
        last_dot = first_column[-1]
        min_y_diff = float('inf')
        next_dot = None

        x_min, x_max = last_dot[0] + separation_threshold0, last_dot[0] + separation_threshold
        possible_dots = [
            dot for dot in remaining_dots
            if 0 < dot[1] - last_dot[1] <= 3000 and x_min <= dot[0] <= x_max
        ]

        for dot in possible_dots:
            y_diff = dot[1] - last_dot[1]
            if y_diff < min_y_diff:
                min_y_diff = y_diff
                next_dot = dot

        if next_dot is None:
            break  # No more dots to add to this column

        first_column.append(next_dot)
        remaining_dots.remove(next_dot)

    return np.array(first_column), np.array(remaining_dots)






def detect_small_dots_and_contours(masked_region, x_threshold=40):
    # Apply threshold to find dots
    _, thresh = cv2.threshold(cv2.resize(masked_region, None, fx=1, fy=1, interpolation=cv2.INTER_AREA),
                             100, 255, cv2.THRESH_BINARY)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # Extract dot centers and store contour areas
    dot_centers = []
    dot_areas = [] # Store contour areas
    dot_areas2=[]
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > 1:  # Ignore very small dots
            (x, y), _ = cv2.minEnclosingCircle(contour)
            dot_centers.append((int(x), int(y), int(area)))
            dot_areas.append(area)  # Store the area
            dot_areas2.append((int(x), int(y), area))  # Store the area

    dot_centers = np.array(dot_centers, dtype=np.int32)
    dot_centers2 = np.array(dot_areas2, dtype=np.int32)


    if len(dot_centers) < 2:
        print("Not enough dots for clustering.")
        return dot_centers, masked_region, {}, -1

    # **Step 1: Detect All Columns Iteratively**
    columns = []
    column_labels = {}
    column_areas = []  # Store areas per column
    column_x_positions = []  # Store leftmost X position

    while len(dot_centers) > 0:
        first_column, remaining_dots = find_first_column(dot_centers, x_threshold)

        col_idx = len(columns)
        col_area_list = [dot_areas[i] for i, dot in enumerate(dot_centers) if tuple(dot) in first_column]
        column_areas.append(col_area_list)  # Store areas for each column

        if len(first_column) > 0:
            leftmost_x = min(first_column, key=lambda d: d[0])[0]  # Get leftmost X position
            column_x_positions.append(leftmost_x)

        for dot in first_column:
            column_labels[tuple(dot)] = col_idx

        columns.append(first_column)

        # Sort remaining dots again to prioritize leftmost dots first
        if remaining_dots.size>0:
            remaining_dots = np.array(remaining_dots)
            remaining_dots = remaining_dots[np.argsort(remaining_dots[:, 0])]
            dot_centers = remaining_dots
        else:
            dot_centers = np.array([])



    # **Step 2: Sort Columns from Left to Right**

    sorted_column_indices = np.argsort(column_x_positions)[::-1]  # Reverse the order
    sorted_columns = [columns[i] for i in sorted_column_indices]  # Reorder columns
    # Create a mapping from old indices to new sorted indices
    column_remap = {old_idx: new_idx for new_idx, old_idx in enumerate(sorted_column_indices)}

    # Create a mapping from old indices to new sorted indices
    column_remap = {old_idx: new_idx for new_idx, old_idx in enumerate(sorted_column_indices)}

    # Update column labels based on the new sorted order
    new_column_labels = {}
    for dot, old_col_idx in column_labels.items():
        new_col_idx = column_remap[old_col_idx]
        new_column_labels[dot] = new_col_idx  # Assign new column index

    # **Step 6: Annotate All Detected Columns (with Sorted Indices)**
    annotated_dots = cv2.cvtColor(cv2.resize(masked_region, None, fx=1, fy=1, interpolation=cv2.INTER_AREA),
                                  cv2.COLOR_GRAY2BGR)



    data = []

    for col_idx, column_array in enumerate(sorted_columns):  # Loop over each column array in the list
        for row in column_array:  # Loop over each row within that column array
            x, y, area = row  # Unpack the row
            data.append((x, y, col_idx, area))  # Store x, y, col_idx (column index), and area



    best_match=1
    # Create an annotated image
    annotated_dots_sorted = cv2.cvtColor(cv2.resize(masked_region, None, fx=1, fy=1, interpolation=cv2.INTER_AREA),
                                         cv2.COLOR_GRAY2BGR)

    # Initialize label index starting from 49

    num_columns = len(columns)
    print(f"Total columns detected: {num_columns}")
    all_columns = 77
    starting_column = num_columns - all_columns
    # Iterate through columns starting from the closest column
    valid_column_indices2 = set(range(starting_column,num_columns ))
    add_factor=51-starting_column
    # **Step 5: Assign colors to columns**
    colors = generate_gradient_colors(len(valid_column_indices2))
    column_colors = {col_idx: colors[i] for i, col_idx in enumerate(valid_column_indices2)}
    for (x, y, col_label, area) in data:
        if col_label in valid_column_indices2:  # Only annotate valid columns
            color = column_colors[col_label]

            # Draw dot
            cv2.circle(annotated_dots_sorted, (x, y), 3, color, -1)

            # Draw enclosing circle
            cv2.circle(annotated_dots_sorted, (x, y), int(np.sqrt(area / np.pi)), (0, 255, 0), 1)  # Green circle

            # Display dot area near the dot
            cv2.putText(annotated_dots_sorted, f"{int(area)}", (x + 10, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)  # Yellow text for area

            # Display column number near the dot
            cv2.putText(annotated_dots_sorted, f"Col {col_label+add_factor}", (x - 10, y + 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)  # White text for column

    data = []

    # Start numbering columns from 51
    starting_label = 51

    # Process all columns, but only keep valid ones
    for new_col_idx, (col_idx, column_array) in enumerate(
            [(idx, sorted_columns[idx]) for idx in valid_column_indices2]
    ):
        new_label = starting_label + new_col_idx  # Assign new labels starting from 51
        for row in column_array:  # Loop over each row within that column array
            x, y, area = row  # Unpack the row
            data.append((x, y, new_label, area))  # Store x, y, new column label, and area

    print("Filtered & Renumbered Processed Data:", data)

    # Save the filtered data to a CSV file
    df = pd.DataFrame(data, columns=["X", "Y", "Column_Index", "Area"])
    df.to_csv("filtered_columns_data.csv", index=False)

        # **Step 8.1: Highlight Missing Columns**
    timestamp = time.strftime("%Y%m%d_%H%M%S")


        # Define the filename with timestamp
    filename = f"result_sidepizza_{timestamp}.jpg"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cv2.imwrite(os.path.join(script_dir, filename), annotated_dots_sorted)
    print("Annotated image saved as 'result_sidepizza.png'.")

    return data, annotated_dots, sorted_columns, best_match
