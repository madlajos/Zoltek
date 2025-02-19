import numpy as np
import os
import cv2
import time
import globals

def calculate_statistics(dot_list, expected_counts=None):
    """
    dot_list = [ [dot_id, x, y, col, area], ... ] from globals.measurement_data.
    
    We classify each dot into 1,2,3 based on area ratio.
    If a dot is class 1 => remove it from measurement_data, increment locked_class1_count.

    The final class 1 = newly found in this pass + locked_class1_count.
    Returns a dict: {
      "result_counts": [class1, class2, class3],
      "classified_dots": [ (dot_id, x, y, col, area, cls), ... ]
    }
    """
    from collections import defaultdict

    try:
        # 1) Build a list of (dot_id, x, y, col, area)
        data = []
        for item in dot_list:
            dot_id, x, y, col, area = item
            data.append((dot_id, int(x), int(y), int(col), float(area)))

        # Default or provided expected counts
        default_expected_counts = {
            "center_circle": 360,
            "center_slice": 510,
            "outer_slice": 2248
        }
        if not expected_counts:
            expected_counts = default_expected_counts

        # 2) Group by column
        columns = defaultdict(list)
        for (dot_id, x, y, col, area) in data:
            columns[col].append((dot_id, x, y, col, area))

        # Compute column averages
        column_averages = {}
        if 0 in columns:
            column_averages[0] = np.mean([d[4] for d in columns[0]])

        combined_areas = []
        for c in range(1, 11):
            if c in columns:
                combined_areas += [d[4] for d in columns[c]]
        if combined_areas:
            column_averages["1-10"] = np.mean(combined_areas)

        for c in range(11, 128):
            if c in columns:
                column_averages[c] = np.mean([d[4] for d in columns[c]])

        # 3) Classify
        class_counts = {1: 0, 2: 0, 3: 0}
        classified_with_id = []  # (dot_id, x, y, col, area, cls)

        for col_val, dots_in_col in columns.items():
            avg_area = column_averages.get(col_val, 1.0)
            min_thresh = 0.1 * avg_area
            max_thresh = 0.95 * avg_area

            for (dot_id, x, y, col, area) in dots_in_col:
                ratio = (area / avg_area) if avg_area > 0 else 1
                if ratio < 0.1:
                    ccls = 1
                elif ratio <= 0.95:
                    ccls = 2
                else:
                    ccls = 3

                class_counts[ccls] += 1
                classified_with_id.append((dot_id, x, y, col, area, ccls))

        # Sort by dot_id if you like stable output
        classified_with_id.sort(key=lambda item: item[0])

        # 4) Remove newly discovered Class 1 from measurement_data
        class1_ids = {item[0] for item in classified_with_id if item[5] == 1}
        if class1_ids:
            removed_count = remove_class1_from_data(class1_ids)
            globals.locked_class1_count += removed_count

        # 5) Final class1 = newly found + locked_class1_count
        final_class1 = class_counts[1] + globals.locked_class1_count
        final_counts = [final_class1, class_counts[2], class_counts[3]]

        # Convert to final list for "classified_dots"
        # Keep dot_id so the route can filter out newly added ones
        classified_dots = classified_with_id  # (dot_id,x,y,col,area,ccls)

        return {
            "result_counts": final_counts,
            "classified_dots": classified_dots
        }

    except Exception as e:
        return {"error": str(e)}
    
    
def remove_class1_from_data(class1_ids):
    """
    From globals.measurement_data ([dot_id, x, y, col, area]),
    remove any item whose dot_id is in class1_ids.
    Returns how many were removed.
    """
    new_list = []
    removed_count = 0
    for item in globals.measurement_data:
        dot_id = item[0]
        if dot_id in class1_ids:
            removed_count += 1
        else:
            new_list.append(item)
    globals.measurement_data = new_list
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