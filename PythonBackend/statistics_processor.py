import numpy as np
import os
import cv2
import time
import globals
from collections import defaultdict
from settings_manager import get_settings


def calculate_statistics(dot_list, expected_counts=None):
    """
    dot_list = [ [dot_id, x, y, col, area, locked?], ... ] from globals.measurement_data.
    
    We classify each dot into 1, 2, or 3 based on area ratio.
    If a dot is classified as 1, we mark it as locked (locked = True) so that it won't be re‑classified later.
    
    The final class1 count = newly found in this pass plus any previously locked ones.
    
    Returns a dict:
       {
         "result_counts": [class1, class2, class3],
         "classified_dots": [ (dot_id, x, y, col, area, cls, locked), ... ]
       }
    """
    # Get size limits for classification.
    settings_data = get_settings()
    size_limits = settings_data.get("size_limits", {})
    class1_limit = size_limits.get("class1", 0) / 100
    class2_limit = size_limits.get("class2", 0) / 100

    # Define mapping for expected counts.
    expected_counts_map = {
        "full": {"center_circle": 360, "center_slice": 510, "outer_slice": 2248},
        "center_circle": {"center_circle": 360, "center_slice": 0, "outer_slice": 0},
        "center_slice": {"center_circle": 0, "center_slice": 510, "outer_slice": 0},
        "outer_slice": {"center_circle": 0, "center_slice": 0, "outer_slice": 2248},
        "slices": {"center_circle": 0, "center_slice": 510, "outer_slice": 2248},
    }
    if expected_counts is None:
        expected_counts = expected_counts_map["full"]
    elif isinstance(expected_counts, str):
        expected_counts = expected_counts_map.get(expected_counts, expected_counts_map["full"])

    try:
        # 1) Build a list of (dot_id, x, y, col, area, locked) tuples.
        data = []
        for item in dot_list:
            # If the item already has a locked flag (6 elements), use it; otherwise default to False.
            if len(item) >= 6:
                dot_id, x, y, col, area, locked = item[:6]
            else:
                dot_id, x, y, col, area = item
                locked = False
            data.append((dot_id, int(x), int(y), int(col), float(area), locked))

        # 2) Group by column.
        columns = defaultdict(list)
        for (dot_id, x, y, col, area, locked) in data:
            columns[col].append((dot_id, x, y, col, area, locked))

        # Compute column max as denominator.
        column_reference = {}
        if 0 in columns:
            column_reference[0] = np.max([d[4] for d in columns[0]])
        combined_areas = []
        for c in range(1, 11):
            if c in columns:
                combined_areas += [d[4] for d in columns[c]]
        if combined_areas:
            column_reference["1-10"] = np.max(combined_areas)
        for c in range(11, 128):
            if c in columns:
                column_reference[c] = np.max([d[4] for d in columns[c]])

        # 3) Classify dots.
        class_counts = {1: 0, 2: 0, 3: 0}
        classified_with_id = []  # Will hold tuples: (dot_id, x, y, col, area, cls, locked)
        for col_val, dots_in_col in columns.items():
            ref_value = column_reference.get(col_val, 1.0)
            for (dot_id, x, y, col, area, locked) in dots_in_col:
                # Compute ratio using the column max.
                ratio = (area / ref_value) if ref_value > 0 else 1
                # Reclassify even if not locked, then lock if class 1.
                if ratio < class1_limit:
                    ccls = 1
                    locked = True  # Mark as locked
                elif ratio <= class2_limit:
                    ccls = 2
                else:
                    ccls = 3
                class_counts[ccls] += 1
                classified_with_id.append((dot_id, x, y, col, area, ccls, locked))
        classified_with_id.sort(key=lambda item: item[0])

        # 4) Instead of removing class 1 dots from globals.measurement_data,
        # we update globals.measurement_data with the new classified results.
        globals.measurement_data = classified_with_id.copy()

        # 5) Final counts.
        final_class1 = class_counts[1] + globals.locked_class1_count
        final_counts = [final_class1, class_counts[2], class_counts[3]]
        globals.dot_results = classified_with_id  # Save the full classification for CSV export.
        
        return {
            "result_counts": final_counts,
            "classified_dots": classified_with_id
        }

    except Exception as e:
        return {"error": str(e)}
    

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
        dot_id, x, y, col, area, ccls, locked = dot
        radius = max(1, int(np.sqrt(area / np.pi)))  # Ensure minimum size
        cv2.circle(annotated_img, (x, y), radius, colors.get(ccls, (255, 255, 255)), 1)
        i = i + 1

    # Save the image
    filename = os.path.join(output_dir, f"annotated_{int(time.time())}.png")
    cv2.imwrite(filename, annotated_img)
    print(f"Annotated image saved: {filename}")
    return filename