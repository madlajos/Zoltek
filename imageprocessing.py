import cv2
import numpy as np
import os
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import matplotlib.pyplot as plt
import time
from collections import Counter

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

def process_center(image):
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
    #for i, dot in enumerate(dot_contours):
    #    print(f"Dot {i + 1}: X = {dot[0]}, Y = {dot[1]}, Column = {dot[2]}, Area = {dot[3]}")
    
    print("Center fütyi")
    print(dot_contours)
    
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
    
    nonzero_coords = np.column_stack(np.where((mask_layer) > 0))  # Get all nonzero pixel coordinates

    if len(nonzero_coords) > 0:
        globals.x_end = np.min(nonzero_coords[:, 1])  # Find max x-coordinate
        # print(f"Mask ends at x = {globals.x_end}")

    print("x_end FÜTYI:")
    print(globals.x_end)
    
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
    df = pd.DataFrame(dot_area_column_mapping, columns=['X', 'Y', 'Column', 'Area'])
    df.to_csv('dot_areas_with_columns.csv', index=False)
    return dot_area_column_mapping, annotated_dots

def process_inner_slice(image):
    image = cv2.flip(image, 0)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(script_dir, 'templ06_mod5.jpg')
    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)

    if image is None or template is None:
        raise FileNotFoundError("Target or template image not found. Check the file paths.")
        # Step 1: Crop the input image
    cropped_image = crop_second_two_thirds1(image)

    # Step 2: Match the polygonal template and extract the masked region
    try:
        polygon_region, annotated_image, polygon_mask = template_match_with_polygon1(cropped_image, template)
    except ValueError as e:
        print(e)
        exit()

    # Step 3: Detect small dots in the polygon region
    dot_contours, annotated_dots, grouped_x = detect_small_dots_and_contours1(polygon_region)
    # Get current timestamp
    timestamp = time.strftime("%Y%m%d_%H%M%S")


    print("Side fütyi 1")
    print(dot_contours)


    # Define the filename with timestamp
    filename = f"result_pizza_{timestamp}.jpg"

    # Save the image in the script directory
    cv2.imwrite(os.path.join(script_dir, filename), annotated_dots)

    return dot_contours

def crop_second_two_thirds1(image, save_path=None):
    """
    Crops the second 2/3 horizontally of an image and returns it.
    """
    cropped_image =image[:, globals.x_end:]

    return cropped_image

def template_match_with_polygon1(cropped_image, template, start_x=0, start_y=0, search_width=None, search_height=None,
                                 save_path=None):

    # Ensure grayscale consistency
    cropped_image = cv2.cvtColor(cropped_image, cv2.COLOR_BGR2GRAY) if len(cropped_image.shape) == 3 else cropped_image
    template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY) if len(template.shape) == 3 else template

    # Define the search area
    if search_width is None:
        search_width = cropped_image.shape[1] - start_x
    if search_height is None:
        search_height = cropped_image.shape[0] - start_y

    # Extract the subregion where matching will occur
    search_region = cropped_image[start_y:start_y + search_height, start_x:start_x + search_width]

    template_height, template_width = template.shape
    best_match = None
    best_max_val = -1
    best_scale = 1.0
    best_top_left = None

    # Multi-scale template matching
    scales = np.linspace(0.99, 1, 1)  # Adjust scales to search (e.g., 84% to 100%)
    for scale in scales:
        resized_template = cv2.resize(template, (int(template_width * scale), int(template_height * scale)))
        result = cv2.matchTemplate(search_region, resized_template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val > best_max_val:
            best_max_val = max_val
            best_match = resized_template
            best_top_left = (max_loc[0] + start_x, max_loc[1] + start_y)  # Offset by search region
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
    kernel = np.ones((31, 31), np.uint8)  # 15 pixels in each direction (total size 31x31)
    expanded_mask = cv2.dilate(original_mask, kernel, iterations=1)

    # **Step 2: Create the 15-pixel white boundary**
    boundary_mask = expanded_mask - original_mask  # Subtract original to get only boundary

    # **Step 3: Set boundary to white (255), and keep the original mask as 1**
    final_mask = np.copy(expanded_mask)
    final_mask[boundary_mask == 1] = 255  # Set boundary pixels to white
    final_mask[original_mask == 1] = 1  # Keep the original mask as 1

    # **Apply the final mask to the matched region**
    masked_polygon_region = cv2.bitwise_and(matched_region, matched_region, mask=expanded_mask)


    # Annotate the matched polygon on the cropped image
    annotated_image = cv2.cvtColor(cropped_image, cv2.COLOR_GRAY2BGR)
    cv2.rectangle(annotated_image, top_left, bottom_right, (0, 255, 0), 2)
    cv2.putText(annotated_image, f"Scale: {best_scale:.2f}", (top_left[0], top_left[1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

    # Optionally save the masked region
    if save_path:
        cv2.imwrite(save_path, masked_polygon_region)

    return masked_polygon_region, annotated_image, final_mask

def generate_gradient_colors1(n):
    """Generate a gradient of distinct colors for visualization."""
    colormap = plt.cm.get_cmap('jet', n)
    return [(int(255 * r), int(255 * g), int(255 * b)) for r, g, b, _ in colormap(np.linspace(0, 1, n))]

def detect_small_dots_and_contours1(masked_region, x_threshold=40):
    """
    Detects dots, groups them into columns, and excludes the last two rows & columns when saving and annotating.
    """
    # Apply threshold to find dots
    _, thresh = cv2.threshold(masked_region, 130, 255, cv2.THRESH_BINARY)

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
    sorted_indices = np.lexsort((dot_centers[:, 1], dot_centers[:, 0]))  # First sort by X, then by Y
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
        columns = columns[:-7]  # Remove last two columns
        valid_column_indices = set(range(num_columns - 7))  # Keep only valid column indices
    else:
        valid_column_indices = set(range(num_columns))  # Keep all if there are 2 or fewer columns
    # **Step 3.1: Detect missing columns by analyzing spacing**
    column_x_positions = [min(col, key=lambda d: d[0])[0] for col in columns if
                          len(col) > 0]  # Get leftmost dot X in each column

    # Sort detected column positions
    column_x_positions.sort()

    # Compute distances between adjacent columns
    missing_columns = []

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

    # Print detected missing columns
    if missing_columns:
        print(f"Missing columns detected at X positions: {missing_columns}")

        # Insert missing columns
        for x_missing in missing_columns:
            columns.append([(x_missing, -1)])  # Placeholder for missing column
            column_labels[(x_missing, -1)] = -1  # Label as missing
    # **Step 4: Modify Column Indexing**
    column_mapping = {}
    counter = 1  # Start numbering from 1

    filtered_dot_area_column_mapping = []
    for x, y, col, area in dot_area_column_mapping:
        if col in valid_column_indices:
            if col not in column_mapping:  # Assign a new index
                column_mapping[col] = counter
                counter += 1
            new_col = column_mapping[col]  # Use assigned index

            filtered_dot_area_column_mapping.append((x, y, new_col, area))

    # Update column labels to start from 1 when annotating
    column_labels = {dot: column_mapping[col] for dot, col in column_labels.items() if col in column_mapping}

    # **Step 5: Assign colors to columns**
    colors = generate_gradient_colors1(len(valid_column_indices))
    column_colors = {col_idx: colors[i] for i, col_idx in enumerate(valid_column_indices)}

    # **Step 6: Count dots per column**
    column_dot_counts = {col_idx: sum(1 for _, _, col, _ in filtered_dot_area_column_mapping if col == col_idx) for
                         col_idx in valid_column_indices}

    # **Step 7: Print column-wise dot counts**
    # print("\n### Dot Count per Column ###")
    # for column, count in column_dot_counts.items():
    #   print(f"Column {column}: {count} dots")

    # **Step 8: Annotate the image (excluding last two columns)**
    annotated_dots = cv2.cvtColor(masked_region, cv2.COLOR_GRAY2BGR)

    for (x, y, col_label, area) in filtered_dot_area_column_mapping:
        if col_label in valid_column_indices:  # Only annotate valid columns
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

    # Convert filtered_dot_area_column_mapping to a DataFrame
    new_data = pd.DataFrame(filtered_dot_area_column_mapping, columns=columns)

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
    #print(f"Dot areas with column numbers saved to '{file_path}'.")

    # Extract last column index
    if valid_column_indices:
        globals.last_column_idx = max(valid_column_indices)  # Last valid column index

        # Get the areas of dots in the last column
        last_column_areas = [area for x, y, col, area in filtered_dot_area_column_mapping if col == globals.last_column_idx]

        # Sum the areas if needed
        globals.total_last_column_area = (last_column_areas)

        #print(f"Total Area of Last Column ({globals.last_column_idx}): {globals.total_last_column_area}")


    return filtered_dot_area_column_mapping, annotated_dots, column_dot_counts






def start_side_slice(image):
    cropped_image = crop_second_two_thirds2(cv2.flip(image, 0))
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(script_dir, 'templ05_mod2.jpg')
    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)

    if image is None or template is None:
        raise FileNotFoundError("Target or template image not found. Check the file paths.")
        # Step 1: Crop the input image

    # Step 2: Match the polygonal template and extract the masked region
    try:
        polygon_region, annotated_image, polygon_mask = template_match_with_polygon2(cropped_image, template)

    except ValueError as e:
        print(e)
        exit()

    # Step 3: Detect small dots in the polygon region
    dot_contours, annotated_dots, grouped_x,matching_column = detect_small_dots_and_contours2(polygon_region)
    
    print("Center fütyi2")
    print(dot_contours)
    
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    return dot_contours


def crop_second_two_thirds2(image):
    """
    Crops the second 2/3 horizontally of an image and returns it.
    """
    cropped_image = image

    return cropped_image


def template_match_with_polygon2(cropped_image, template):
    """
    Matches a pizza-slice-shaped template in the cropped image using multi-scale template matching.
    Extracts and masks the matched polygon region without altering pixel intensities.
    Expands the mask by 15 pixels with a white boundary while keeping the original mask as 1.
    """
    # Load the template

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

    # Annotate the matched polygon on the cropped image
    annotated_image = cv2.cvtColor(cropped_image, cv2.COLOR_GRAY2BGR)
    cv2.rectangle(annotated_image, top_left, bottom_right, (0, 255, 0), 2)
    cv2.putText(annotated_image, f"Scale: {best_scale:.2f}", (top_left[0], top_left[1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)



    return masked_polygon_region, annotated_image, final_mask




def find_first_column2(dot_centers, x_threshold=25):
    """
        Finds the first column by starting from the topmost-leftmost dot and moving downward.
        """
    # Sort dots by X, then Y (ensures left-to-right processing)
    dot_centers = dot_centers[np.lexsort((dot_centers[:, 0], dot_centers[:, 1]))]


    # Get the topmost-leftmost dot as the first point
    first_dot = tuple(dot_centers[0])
    first_column = [first_dot]

    # Convert remaining dots to list of tuples for easier removal
    remaining_dots = [tuple(dot) for dot in dot_centers[1:]]

    while True:
        last_dot = first_column[-1]
        min_y_diff = float('inf')
        next_dot = None

        for dot in remaining_dots:
            x_diff = abs(dot[0] - last_dot[0])
            y_diff = dot[1] - last_dot[1]

            # Ensure the dot is below and within the X threshold
            if  0 < y_diff <= 3000 and x_diff <= x_threshold:
                if y_diff < min_y_diff:  # Find the closest dot in Y direction
                    min_y_diff = y_diff
                    next_dot = dot

        if next_dot is None:
            break  # No more dots to add to this column

        first_column.append(next_dot)

        # Remove the next_dot from remaining_dots by converting it to a tuple for comparison
        remaining_dots = [dot for dot in remaining_dots if tuple(dot) != tuple(next_dot)]

    return np.array(first_column), [np.array(dot) for dot in remaining_dots]

def generate_gradient_colors(num_colors):
    """Generates distinct colors for different columns."""
    cmap = cv2.applyColorMap(np.linspace(0, 255, num_colors, dtype=np.uint8).reshape(-1, 1), cv2.COLORMAP_JET)
    return [tuple(map(int, color[0])) for color in cmap]


def detect_small_dots_and_contours2(masked_region, x_threshold=10):
    # Apply threshold to find dots
    _, thresh = cv2.threshold(cv2.resize(masked_region, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA),
                              80, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Extract dot centers and store contour areas
    dot_centers = []
    contour_areas = []  # Store contour areas

    for contour in contours:
        area = cv2.contourArea(contour)
        if area > 1:  # Ignore very small dots
            (x, y), _ = cv2.minEnclosingCircle(contour)
            dot_centers.append((int(x), int(y)))
            contour_areas.append(area)  # Store the area

    dot_centers = np.array(dot_centers, dtype=np.int32)

    if len(dot_centers) < 2:
        print("Not enough dots for clustering.")
        return dot_centers, masked_region, {}, -1

    # **Step 1: Detect All Columns Iteratively**
    columns = []
    column_labels = {}
    column_areas = []  # Store areas per column
    column_x_positions = []  # Store leftmost X position

    while len(dot_centers) > 0:
        first_column, remaining_dots = find_first_column2(dot_centers, x_threshold)

        col_idx = len(columns)
        col_area_list = [contour_areas[i] for i, dot in enumerate(dot_centers) if tuple(dot) in first_column]
        column_areas.append(col_area_list)  # Store areas for each column

        if len(first_column) > 0:
            leftmost_x = min(first_column, key=lambda d: d[0])[0]  # Get leftmost X position
            column_x_positions.append(leftmost_x)

        for dot in first_column:
            column_labels[tuple(dot)] = col_idx

        columns.append(first_column)

        # Sort remaining dots again to prioritize leftmost dots first
        if remaining_dots:
            remaining_dots = np.array(remaining_dots)
            remaining_dots = remaining_dots[np.argsort(remaining_dots[:, 0])]
            dot_centers = remaining_dots
        else:
            dot_centers = np.array([])

    num_columns = len(columns)
    print(f"Total columns detected: {num_columns}")

    # **Step 2: Sort Columns from Left to Right**
    sorted_column_indices = np.argsort(column_x_positions)  # Sort by leftmost X position
    sorted_columns = [columns[i] for i in sorted_column_indices]  # Reorder columns
    sorted_column_areas = [column_areas[i] for i in sorted_column_indices]  # Reorder areas

    # Create a mapping from old indices to new sorted indices
    column_remap = {old_idx: new_idx for new_idx, old_idx in enumerate(sorted_column_indices)}

    # Update column labels based on the new sorted order
    new_column_labels = {}
    for dot, old_col_idx in column_labels.items():
        new_col_idx = column_remap[old_col_idx]
        new_column_labels[dot] = new_col_idx  # Assign new column index



    # **Step 5: Save All Columns to CSV (with Sorted Indices)**
    data = []
    for col_idx, column in enumerate(sorted_columns):
        for dot in column:
            data.append((dot[0], dot[1], col_idx))  # Keep the sorted column index

    dot_identifications = [row[2] for row in data]

    # Count occurrences of each dot identification
    dot_counts = Counter(dot_identifications)
    # print(dot_counts)

    df = pd.DataFrame(data, columns=['X', 'Y', 'Column'])
    df.to_csv('all_detected_columns_sorted.csv', index=False)
    # print("All detected columns saved to 'all_detected_columns_sorted.csv'.")

    # **Step 6: Annotate All Detected Columns (with Sorted Indices)**
    annotated_dots = cv2.cvtColor(cv2.resize(masked_region, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA),
                                  cv2.COLOR_GRAY2BGR)
    for dot, col_label in new_column_labels.items():
        color = (0, 255, 0)  # Green color for dots
        cv2.circle(annotated_dots, tuple(dot), 3, color, -1)  # Draw dot
        cv2.putText(annotated_dots, f"{col_label}", (dot[0] + 5, dot[1] - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    leng_last=len(globals.total_last_column_area)
    matching_dots = [dot_id for dot_id, count in dot_counts.items() if count == leng_last]


    # Extract areas of dots that belong to the matching columns (8, 9, 11)
    sorted_matching_dot_areas = []

    for col_idx in matching_dots:
        # Get all areas for this column
        column_areas = sorted_column_areas[col_idx]

        # Sort the areas in descending order within this column
        column_areas_sorted = sorted(column_areas, reverse=True)

        # Append sorted areas with the column index
        sorted_matching_dot_areas.extend([(col_idx, area) for area in column_areas_sorted])

    # Store results for max/area[1] for all dots in each matching column
    max_div_area1_results = []

    for col_idx in matching_dots:
        # Get all areas for this column
        column_areas = sorted_column_areas[col_idx]

        # Sort the areas in descending order (ensure the list is sorted)
        column_areas_sorted = sorted(column_areas, reverse=True)

        # Compute max/area[1] for each dot in the column (except the last one)
        for i in range(len(column_areas_sorted) - 1):  # Avoid last index to prevent out-of-range
            max_area = column_areas_sorted[i]  # Current max area in descending order
            area_1 = column_areas_sorted[i + 1]  # The next area in sorted order
            max_div_area1_results.append((col_idx, max_area / area_1))
    # Calculate the average area for each matching column
    column_average_areas = {}

    for col_idx in matching_dots:
        # Get all areas for this column
        column_areas = [area for col, area in sorted_matching_dot_areas if col == col_idx]

        # Compute average area
        if column_areas:
            column_average_areas[col_idx] = sum(column_areas) / len(column_areas)
        else:
            column_average_areas[col_idx] = 0  # Handle case where there are no areas
    sorted_last_column_area = sorted(globals.total_last_column_area, reverse=True)
    max_div_area2_results=[]
    # Compute max/area[1] for each dot in the last column (except the last one)
    for i in range(len(sorted_last_column_area) - 1):  # Avoid last index
        max_area = sorted_last_column_area[i]  # Current max area
        area_1 = sorted_last_column_area[i + 1]  # Next area in sorted order
        max_div_area2_results.append( max_area / area_1)
    # Convert max_div_area1_results into a dictionary for easy lookup
    max_div_area1_dict = {}
    for col_idx, ratio in max_div_area1_results:
        if col_idx not in max_div_area1_dict:
            max_div_area1_dict[col_idx] = []
        max_div_area1_dict[col_idx].append(ratio)

    # Convert last column ratios to numpy array
    last_column_ratios = np.array(max_div_area2_results)

    # Find the column with the **smallest difference** using Mean Squared Error (MSE)
    closest_col = None
    min_mse = float('inf')  # Initialize with a large value

    for col_idx, ratios in max_div_area1_dict.items():
        # Trim or pad the lists to match lengths
        n = min(len(ratios), len(last_column_ratios))
        ratios = np.array(ratios[:n])
        last_ratios = last_column_ratios[:n]

        # Calculate **Mean Squared Error (MSE)**
        mse = np.mean((ratios - last_ratios) ** 2)

        # Update the closest column if this one has a smaller MSE
        if mse < min_mse:
            min_mse = mse
            closest_col = col_idx

    best_match=1
    # Define the closest column obtained earlier

    starting_column = closest_col  # This is the closest column to the last column

    # Create an annotated image
    annotated_dots_sorted = cv2.cvtColor(cv2.resize(masked_region, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA),
                                         cv2.COLOR_GRAY2BGR)

    # Initialize label index starting from 49
    label_index = globals.last_column_idx+1

    # Iterate through columns starting from the closest column
    for col_idx in range(starting_column, len(sorted_columns)):  # Start from the closest column
        dots_to_annotate = sorted_columns[col_idx]

        # Annotate dots on the image
        for dot in dots_to_annotate:
            color = (0, 255, 0)  # Green color for visibility
            cv2.circle(annotated_dots_sorted, tuple(dot), 5, color, -1)  # Draw dot
            cv2.putText(annotated_dots_sorted, f"{label_index}", (dot[0] + 5, dot[1] - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Increment label index for the next column
        label_index += 1
    timestamp = time.strftime("%Y%m%d_%H%M%S")

        # Define the filename with timestamp
    filename = f"result_sidepizza_{timestamp}.jpg"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cv2.imwrite(os.path.join(script_dir, filename), annotated_dots_sorted)
    print("Annotated image saved as 'result_sidepizza.png'.")

    return dot_centers, annotated_dots, sorted_columns, best_match