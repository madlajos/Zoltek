import os
import numpy as np
import cv2
import pandas as pd
import time
import matplotlib as plt

from GeneralProc.logger import logger


def generate_gradient_colors(n):
    colormap = plt.cm.get_cmap('jet', n)
    return [(int(255 * r), int(255 * g), int(255 * b)) for r, g, b, _ in colormap(np.linspace(0, 1, n))]


def find_first_column(dot_centers, x_threshold=0):
    """
    Finds the first column by identifying the leftmost dots and moving downward,
    ensuring all dots in the first column belong to the same X range.
    Optimized for speed while keeping np.delete().
    """
    try:
        # **Sort dots by X first, then Y (ensures left-to-right processing)**
        sorted_indices = np.lexsort((dot_centers[:, 0], dot_centers[:, 1]))
        sorted_dots = dot_centers[sorted_indices]

        # **Initialize first column**
        first_dot = sorted_dots[0]
        first_column = [first_dot]

        # **Convert to NumPy array for optimized filtering**
        remaining_dots = sorted_dots[1:]

        # **Determine column X width dynamically**
        x_values = sorted_dots[:, 0]
        x_diffs = np.diff(np.sort(x_values))

        if len(x_diffs) > 0:
            median_x_gap = np.median(x_diffs[x_diffs > 0])  # Ignore zero gaps
            separation_threshold = max(15, min(median_x_gap * 2, 60))  # Dynamic threshold
        else:
            separation_threshold = 30  # Fallback value

        separation_threshold_neg = -separation_threshold

        # **Store indices to delete in batch**
        delete_indices = []

        # **Create a dictionary for quick lookup of dot indices**
        dot_index_map = {tuple(dot): i for i, dot in enumerate(remaining_dots)}

        while remaining_dots.shape[0] > 0:
            last_dot = first_column[-1]

            # **NumPy optimized filtering for possible dots**
            x_min, x_max = last_dot[0] + separation_threshold_neg, last_dot[0] + separation_threshold
            mask = (remaining_dots[:, 1] - last_dot[1] > 0) & (remaining_dots[:, 1] - last_dot[1] <= 3000) & \
                   (remaining_dots[:, 0] >= x_min) & (remaining_dots[:, 0] <= x_max)

            possible_dots = remaining_dots[mask]

            if possible_dots.shape[0] == 0:
                break  # No more dots to add

            # **Find the closest dot in Y direction using np.min() instead of np.argmin()**
            y_diffs = possible_dots[:, 1] - last_dot[1]
            next_dot = possible_dots[np.argmin(y_diffs)]

            first_column.append(next_dot)

            # **Find the index of next_dot in remaining_dots using the dictionary**
            delete_index = dot_index_map.pop(tuple(next_dot), None)

            if delete_index is not None:
                delete_indices.append(delete_index)

            # **Delete in batch after processing**
            if len(delete_indices) >= 100:  # Every 100 iterations, delete in bulk
                remaining_dots = np.delete(remaining_dots, delete_indices, axis=0)
                delete_indices = []
                # **Rebuild dot index map after bulk delete**
                dot_index_map = {tuple(dot): i for i, dot in enumerate(remaining_dots)}

        # **Final batch deletion**
        if delete_indices:
            remaining_dots = np.delete(remaining_dots, delete_indices, axis=0)

        return np.array(first_column), remaining_dots, None
    except:
        logger.logger('E2323')
        return None, None, 'E2323'



# def detect_small_dots_and_contours(masked_region, x_threshold=40):
#     """
#     Detects small dots and extracts their contour areas efficiently.
#     Optimized for speed while maintaining logical consistency.
#     """
#
#     # **Step 1: Apply Fixed Binary Threshold**
#     if len(masked_region.shape) == 3:
#         gray = cv2.cvtColor(masked_region, cv2.COLOR_BGR2GRAY)  # Convert if needed
#     else:
#         gray = masked_region
#
#     _, thresh = cv2.threshold(gray, 130, 255, cv2.THRESH_BINARY)  # Fixed threshold
#
#     # **Step 2: Find Contours Efficiently**
#     contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
#
#     if not contours:
#         print("No contours found.")
#         return np.array([]), masked_region, {}, -1
#
#     # **Step 3: Extract Dot Centers & Areas in Parallel**
#     moments = [cv2.moments(cnt) for cnt in contours]
#     areas = np.array([M["m00"] for M in moments])
#
#     valid_mask = areas > 1  # Filter out noise
#     if not np.any(valid_mask):
#         print("No valid dots found.")
#         return np.array([]), masked_region, {}, -1
#
#     centers = np.array([(
#         int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])
#     ) if M["m00"] != 0 else (0, 0) for M in moments], dtype=np.int32)
#
#     dot_centers = np.column_stack((centers[valid_mask], areas[valid_mask]))  # X, Y, Area
#
#     # **Step 4: Detect Columns Efficiently**
#     columns = []
#     column_labels = {}
#     column_x_positions = []
#
#     while dot_centers.shape[0] > 0:
#         first_column, remaining_dots = find_first_column(dot_centers, x_threshold)
#
#         if first_column.size == 0:
#             break  # No valid columns found
#
#         col_idx = len(columns)
#         column_x_positions.append(np.min(first_column[:, 0]))  # Faster than min()
#
#         for dot in first_column:
#             column_labels[tuple(dot[:2])] = col_idx
#
#         columns.append(first_column)
#         dot_centers = remaining_dots
#
#     # **Step 5: Sort Columns from Right to Left**
#     sorted_indices = np.argsort(column_x_positions)[::-1]
#     sorted_columns = [columns[i] for i in sorted_indices]
#
#     column_remap = {old_idx: new_idx for new_idx, old_idx in enumerate(sorted_indices)}
#     new_column_labels = {dot: column_remap[col_idx] for dot, col_idx in column_labels.items()}
#
#     # **Step 6: Preserve Output Order**
#     num_columns = len(columns)
#     print(f"Total columns detected: {num_columns}")
#     all_columns = 77
#     starting_column = num_columns - all_columns
#     valid_column_indices2 = set(range(starting_column, num_columns))
#
#     data = []
#
#     # **Step 7: Assign Column Numbers & Preserve Print Order**
#     starting_label = 53
#     for new_col_idx, (col_idx, column_array) in enumerate(
#             [(idx, sorted_columns[idx]) for idx in valid_column_indices2]
#     ):
#         new_label = starting_label + new_col_idx
#         for row in column_array:
#             x, y, area = row
#             data.append((x, y, new_label, area))  # Store x, y, new column label, and area
#
#     # **Step 8: Print Data (MUST STAY UNCHANGED)**
#     for i, dot in enumerate(data):
#         print(f"Dot {i + 1}: X = {dot[0]}, Y = {dot[1]}, Column = {dot[2]}, Area = {dot[3]}")
#
#     return data, masked_region, sorted_columns, -1
#









def detect_small_dots_and_contours(masked_region, drawtf, x_threshold=40):
    try:
        # Apply threshold to find dots

        if masked_region is None or masked_region.size == 0:
            logger.error("E2321")
            return None, "E2321"

        _, thresh = cv2.threshold(cv2.resize(masked_region, None, fx=1, fy=1, interpolation=cv2.INTER_AREA),
                                  50, 255, cv2.THRESH_BINARY)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            logger.error("E2322")
            return None, "E2322"

        dot_areas = np.array([cv2.contourArea(cnt) for cnt in contours])
        valid_contours = dot_areas > 1  # Boolean mask for filtering valid contours

        centers = np.array([cv2.minEnclosingCircle(cnt)[0] for cnt in contours], dtype=np.int32)
        dot_centers = np.column_stack((centers[valid_contours], dot_areas[valid_contours]))

        if len(dot_centers) < 2:
            logger.error("E2323")
            return None, "E2323"

        # **Step 1: Detect All Columns Iteratively**
        columns = []
        column_labels = {}
        column_areas = []  # Store areas per column
        column_x_positions = []  # Store leftmost X position

        while len(dot_centers) > 0:
            first_column, remaining_dots, emsg = find_first_column(dot_centers, x_threshold)

            col_idx = len(columns)
            dot_centers_arr = np.array(dot_centers)
            first_column_set = set(map(tuple, first_column))  # Convert to set for fast lookup
            mask = np.array([tuple(dot) in first_column_set for dot in dot_centers_arr])

            col_area_list = dot_areas[:mask.shape[0]][mask]
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

        # **Sort Columns from Right to Left**
        sorted_column_indices = np.argsort(column_x_positions)[::-1]  # Reverse the order
        sorted_columns = [columns[i] for i in sorted_column_indices]  # Reorder columns



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

                cv2.circle(annotated_dots_sorted, (int(x), int(y)), 3, color, -1)
                cv2.circle(annotated_dots_sorted, (int(x), int(y)), int(np.sqrt(area / np.pi)), (0, 255, 0), 1)

                # Display dot area near the dot
                cv2.putText(annotated_dots_sorted, f"{int(area)}", (int(x) + 10, int(y) - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)

                # Display column number near the dot
                cv2.putText(annotated_dots_sorted, f"Col {int(col_label + add_factor)}",
                            (int(x) - 10, int(y) + 10),
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

        #print("Filtered & Renumbered Processed Data:", data)

        # Save the filtered data to a CSV file
       # df = pd.DataFrame(data, columns=["X", "Y", "Column_Index", "Area"])
        #df.to_csv("filtered_columns_data.csv", index=False)


        if drawtf == True:

            # **Step 8.1: Highlight Missing Columns**
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            # Define the filename with timestamp
            filename = f"result_sidepizza_{timestamp}.jpg"
            
            results_dir = os.path.join(os.getcwd(), "Results")
            os.makedirs(results_dir, exist_ok=True)  # Make sure the folder exists

            cv2.imwrite(os.path.join(results_dir, filename), annotated_dots_sorted)

        return data, annotated_dots, sorted_columns, best_match, None
    except Exception as e:
        logger.error('E2327')
        return None, None, None, None, "E2327"
