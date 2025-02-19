import numpy as np
import os
import cv2
import time

def calculate_statistics(dot_contours, expected_counts=None):
    """
    Classifies all detected blobs but preserves their original order by storing an index.
    If a blob is classified into class 1, it's "locked" there permanently:
      - We remove it from `measurement_data` so it won't reappear in future classifications.
      - We increment `globals.locked_class1_count`.
    """
    from collections import defaultdict
    try:
        # Build a list of (orig_index, x, y, col, area)
        data = []
        for i, dot in enumerate(dot_contours):
            x, y, col, area = dot
            data.append((i, int(x), int(y), int(col), float(area)))

        default_expected_counts = {
            "center_circle": 360,
            "center_slice": 510,
            "outer_slice": 2248
        }
        expected_counts = expected_counts if expected_counts else default_expected_counts

        # Group by column, but keep the original index
        columns = defaultdict(list)
        for (orig_idx, x, y, col, area) in data:
            columns[col].append((orig_idx, x, y, col, area))

        # Compute average areas per column
        column_averages = {}
        if 0 in columns:
            column_averages[0] = np.mean([dot[4] for dot in columns[0]])

        combined_areas = []
        for col_num in range(1, 11):
            if col_num in columns:
                combined_areas += [dot[4] for dot in columns[col_num]]
        if combined_areas:
            column_averages["1-10"] = np.mean(combined_areas)

        for col_num in range(11, 128):
            if col_num in columns:
                column_averages[col_num] = np.mean([dot[4] for dot in columns[col_num]])

        class_counts = {1: 0, 2: 0, 3: 0}
        classified_with_index = []

        # Classify each dot
        for col, dots_in_col in columns.items():
            avg_area = column_averages.get(col, 1.0)
            min_thresh = 0.1 * avg_area
            max_thresh = 0.95 * avg_area

            for (orig_idx, x, y, col, area) in dots_in_col:
                area_ratio = area / avg_area if avg_area > 0 else 1

                if area_ratio < 0.1:
                    blob_class = 1
                elif area_ratio <= 0.95:
                    blob_class = 2
                else:
                    blob_class = 3

                class_counts[blob_class] += 1

                classified_with_index.append(
                    (orig_idx, x, y, col, area, blob_class)
                )

        # (1) Sort by original index so final list matches append order
        classified_with_index.sort(key=lambda t: t[0])

        # (2) Convert to final dot format: (x, y, col, area, class)
        classified_dots = [
            (x, y, col, area, blob_class)
            for (orig_idx, x, y, col, area, blob_class) in classified_with_index
        ]

        # (3) Identify newly discovered Class-1 indices
        class1_indices = {
            orig_idx
            for (orig_idx, x, y, col, area, blob_class) in classified_with_index
            if blob_class == 1
        }

        # (4) Remove them from measurement_data so they won't be reclassified
        #     We'll also increment `globals.locked_class1_count`.
        if class1_indices:
            removed_count = remove_class1_from_data(class1_indices)
            globals.locked_class1_count += removed_count
            # Adjust current "class 1" count: we are effectively removing them
            # so they won't appear again, but we still want to reflect they
            # were discovered in *this* classification pass.
            # So class_counts[1] remains the same for "this pass."
            # We'll just add locked_class1_count at the end.

        # Final reported class1 = newly found (class_counts[1]) 
        #                         + all historically locked
        final_class1 = class_counts[1] + globals.locked_class1_count
        final_counts = [final_class1, class_counts[2], class_counts[3]]

        return {
            "result_counts": final_counts,       # [class1, class2, class3]
            "classified_dots": classified_dots   # only the current pass
        }

    except Exception as e:
        return {"error": str(e)}
    
    
def remove_class1_from_data(class1_indices):
    """
    Removes any dot from globals.measurement_data whose enumerated index is in class1_indices.
    Returns the count of removed items.
    """
    # We rebuild measurement_data but skip the ones in class1_indices
    # We'll keep a local copy, then reassign
    new_data = []
    removed_count = 0
    for i, dot in enumerate(globals.measurement_data):
        if i in class1_indices:
            removed_count += 1
        else:
            new_data.append(dot)
    globals.measurement_data = new_data
    return removed_count


def save_annotated_image(image, classified_dots, output_dir="output_images"):
    """
    Draws classified blobs on the original image and saves it.

    Args:
        image (numpy.ndarray): The original grayscale image.
        classified_dots (list): List of newly detected blobs with classification: [x, y, column, area, class]
        output_dir (str): Directory to save the images.
    """
    if image is None:
        print("No image available to annotate.")
        return None

    os.makedirs(output_dir, exist_ok=True)  # Ensure directory exists

    # Convert grayscale image to color for annotations
    annotated_img = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

    # Define colors for classification
    colors = {
        1: (0, 0, 255),    # Red for Class 1
        2: (0, 255, 255),  # Yellow for Class 2
        3: (0, 255, 0)     # Green for Class 3
    }

    # Draw circles based on classification
    print(f"Starting to draw {len(classified_dots)} dots!")
    i = 0
    for dot in classified_dots:
        x, y, col, area, cls = dot
        radius = max(1, int(np.sqrt(area / np.pi)))  # Ensure minimum size
        cv2.circle(annotated_img, (x, y), radius, colors.get(cls, (255, 255, 255)), 1)
        i = i+1


    # Save the image
    filename = os.path.join(output_dir, f"annotated_{int(time.time())}.png")
    cv2.imwrite(filename, annotated_img)
    print(f"Annotated image saved: {filename}")
    return filename