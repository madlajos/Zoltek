import cv2
import numpy as np
import matplotlib.pyplot as plt
import os
import time
import pandas as pd
from collections import defaultdict


def generate_gradient_colors(n):
    colormap = plt.cm.get_cmap('jet', n)
    return [(int(255 * r), int(255 * g), int(255 * b)) for r, g, b, _ in colormap(np.linspace(0, 1, n))]


import cv2
import numpy as np


def det_sort_dots(masked_region, merge_distance=20):
    try:
        _, thresh = cv2.threshold(masked_region, 50, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    except cv2.error as e:
        print("E2223")  # Use logging if needed
        return None, None, "E2223"  # Error during thresholding or contour detection

    dot_centers = []
    dot_areas = []
    spatial_map = {}  # Hash map for fast spatial merging

    for contour in contours:
        area = cv2.contourArea(contour)
        if area > 1:  # Ignore zero-area dots
            (x, y), _ = cv2.minEnclosingCircle(contour)
            x, y = int(x), int(y)

            # **Find existing dot in spatial grid for merging**
            key = (x // merge_distance, y // merge_distance)  # Grid key
            if key in spatial_map:
                i = spatial_map[key]  # Get index of existing dot
                total_area = dot_areas[i] + area
                new_x = int((dot_areas[i] * dot_centers[i][0] + area * x) / total_area)  # Weighted centroid
                new_y = int((dot_areas[i] * dot_centers[i][1] + area * y) / total_area)
                dot_centers[i] = (new_x, new_y)
                dot_areas[i] = total_area
            else:
                # New dot, store in list and hash map
                dot_centers.append((x, y))
                dot_areas.append(area)
                spatial_map[key] = len(dot_centers) - 1  # Store index in spatial grid

    dot_centers = np.array(dot_centers, dtype=np.int32)
    dot_areas = np.array(dot_areas)

    if len(dot_centers) < 2:
        print("E2224")  # Use logging if needed
        return None, None, "E2224"  # Not enough dots for clustering

    # **Sort by X then Y**
    sorted_indices = np.lexsort((-dot_centers[:, 1], -dot_centers[:, 0]))  # Reverse sorting
    dot_centers = dot_centers[sorted_indices]
    dot_areas = dot_areas[sorted_indices]

    # **Exclude Last Two Rows**
    unique_y_values = np.unique(dot_centers[:, 1])
    if len(unique_y_values) > 2:
        excluded_rows = unique_y_values[-2:]
        mask = ~np.isin(dot_centers[:, 1], excluded_rows)
        dot_centers = dot_centers[mask]
        dot_areas = dot_areas[mask]

    return dot_centers, dot_areas, masked_region


def det_cols(dot_centers, dot_areas, x_threshold=42):
    try:
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
        return dot_area_column_mapping, columns, column_labels
    except Exception as e:

        return None, None, "E2226"  # Error during column detection


def sort_cols(columns, dot_area_column_mapping):
    try:
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
        column_x_positions.sort()
        return column_x_positions, filtered_dot_area_column_mapping, num_columns, column_mapping, valid_column_indices
    except Exception as e:

        return None, None, None, "E2227"  # Error during column sorting


def shift_column_labels_for_missing(missing_columns, x_to_col_number, filtered_dot_area_column_mapping):
    # Step 1: Collect (missing_x, after_col) pairs
    missing_info = []
    for missing_x in missing_columns:
        # Find the nearest X to the left that exists in the column map
        left_xs = [x for x in x_to_col_number.keys() if x < missing_x]
        if not left_xs:
            continue  # no valid left anchor
        left_x = max(left_xs)
        after_col = x_to_col_number[left_x]
        missing_info.append((missing_x, after_col - 1))

    # Sort by after_col so we apply shifts in order
    missing_info.sort(key=lambda m: m[1])

    updated_mapping = []
    for x, y, col, area in filtered_dot_area_column_mapping:
        # Shift by counting how many missing columns are after this column index
        shift = sum(1 for _, after_col in missing_info if col > after_col)
        updated_mapping.append((x, y, col + shift, area))

    return updated_mapping


def islice_detect_small_dots_and_contours(masked_region, drawtf, offset):
    try:
        dot_centers, dot_areas, masked_region = det_sort_dots(masked_region)
        if dot_centers is None:
            return None, None, "E2225"  # Error in dot detection

        dot_area_column_mapping, columns, column_labels = det_cols(dot_centers, dot_areas, x_threshold=40)
        if dot_area_column_mapping is None:
            return None, None, "E2226"  # Error in column detection

        column_x_positions, filtered_dot_area_column_mapping, num_columns, column_mapping, valid_column_indices = sort_cols(
            columns, dot_area_column_mapping)
        if column_x_positions is None:
            return None, None, "E2227"  # Error in sorting columns

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
                    for j in range(1, num_missing + 1):
                        estimated_x = column_x_positions[i] + int(j * median_spacing)
                        missing_columns.append(estimated_x)
                        missing_column_pairs.append((column_x_positions[i], column_x_positions[i + 1]))

                        missing_column_labels[(
                            estimated_x,
                            -1)] = f"Missing between {column_x_positions[i]} and {column_x_positions[i + 1]}"

        if missing_columns:
            x_to_col_number = {x: col for x, y, col, area in filtered_dot_area_column_mapping}
            for missing_x, (left_col, right_col) in zip(missing_columns, missing_column_pairs):
                left_col_number = x_to_col_number.get(left_col, f"Unknown Col at {left_col}")
                right_col_number = x_to_col_number.get(right_col, f"Unknown Col at {right_col}")
                print(
                    f"Missing column at X={missing_x} is between column {left_col_number} (X={left_col}) and column {right_col_number} (X={right_col})")

            filtered_dot_area_column_mapping = shift_column_labels_for_missing(
                missing_columns, x_to_col_number, filtered_dot_area_column_mapping
            )
        # no_missing = len(missing_columns)
        # next_column_number = max(column_mapping.values(), default=0) + 1
        #
        # for missing_x, (left_col, right_col) in zip(missing_columns, missing_column_pairs):
        #     left_col_number = x_to_col_number[left_col]
        #     right_col_number = x_to_col_number[right_col]
        #
        #     if missing_x not in x_to_col_number:
        #         x_to_col_number[missing_x] = next_column_number
        #         column_mapping[missing_x] = next_column_number
        #         next_column_number += 1
        #
        #     filtered_dot_area_column_mapping.append((missing_x, -1, x_to_col_number[missing_x], 0))

        filtered_dot_area_column_mapping = [
            (x, y, col, area) for x, y, col, area in filtered_dot_area_column_mapping if 1 <= col <= 50
        ]
        filtered_dot_area_column_mapping_fin = [
            (x + offset[0], y + offset[1], col, area)
            for x, y, col, area in filtered_dot_area_column_mapping
        ]

        annotated_dots = cv2.cvtColor(masked_region, cv2.COLOR_GRAY2BGR)

        if drawtf == True:
            valid_column_indices2 = set(range(min(51, num_columns)))
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
                            cv2.line(annotated_dots, (x_missing, y), (x_missing, y + 10), (0, 0, 255),
                                     2)  # Red dashed line

                    # Label the missing column
                    cv2.putText(annotated_dots, "MISSING", (x_missing - 20, 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)  # Red text for missing columns
                # **Step 9: Save dot areas with column numbers (excluding last two columns)**
                # Define the column names
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"result_pizza_{timestamp}.jpg"
            results_dir = os.path.join(os.getcwd(), "Results")
            os.makedirs(results_dir, exist_ok=True)  # Make sure the folder exists
            cv2.imwrite(os.path.join(results_dir, filename), annotated_dots)

        column_counts = {}
        expected_counts = [
            3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 6, 6, 7, 7, 7,
            8, 8, 8, 9, 9, 9, 9, 10, 10, 10, 11, 11, 11,
            12, 12, 12, 12, 13, 13, 13, 14, 14, 14, 15, 15, 15, 15,
            16, 16, 16, 17, 17, 17, 18
        ]
        for i, col in enumerate(columns):
            if 0 <= i < len(expected_counts):  # csak az 1–50. oszlopra (index szerint 0–49)
                expected = expected_counts[i]
                if (len(col) - expected) > 0:
                    return None, None, "E2230"

        # # Count occurrences of each column
        # for entry in filtered_dot_area_column_mapping:
        #     column_label = entry[2]  # Third value in the tuple
        #     column_counts[column_label] = column_counts.get(column_label, 0) + 1
        # output = "\n".join([f"Col {col}: {count} dots" for col, count in column_counts.items()])
        # print(output)
        a = 510 - len(filtered_dot_area_column_mapping_fin)
        if a < 0:
            return None, None, "E2229"
        # # Count occurrences of each column
        # for entry in filtered_dot_area_column_mapping:
        #     column_label = entry[2]  # Third value in the tuple
        #     column_counts[column_label] = column_counts.get(column_label, 0) + 1
        # output = "\n".join([f"Col {col}: {count} dots" for col, count in column_counts.items()])
        # print(output)
        return filtered_dot_area_column_mapping_fin, annotated_dots, None

    except Exception as e:

        return None, None, "E2228"  # General error during processing