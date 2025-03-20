import cv2
import numpy as np

import cv2
import numpy as np

def redraw_from_data_on_original(data, original_image):
    """
    Redraws detected dots from `data` onto the original color image.

    Parameters:
        data (list of tuples): List containing (X, Y, Column, Area) for each detected dot.
        original_image (numpy array): The original color image.

    Returns:
        annotated_img (numpy array): The redrawn image with colored dots.
    """

    # Make a copy of the original image to draw on
    annotated_img = original_image.copy()

    # Get image dimensions (height and width)
    height, width = original_image.shape[:2]
    print(f"Image dimensions (height, width): ({height}, {width})")

    # Generate distinct colors for each unique column
    unique_columns = sorted(set(dot[2] for dot in data))
    num_cols = len(unique_columns)
    colors = np.random.randint(0, 255, (num_cols, 3), dtype=np.uint8)  # Random unique colors

    # Map column index to colors
    column_colors = {col: tuple(map(int, colors[i])) for i, col in enumerate(unique_columns)}

    # Draw each dot with its corresponding column color
    for (x, y, col_label, area) in data:
        color = column_colors.get(col_label, (0, 255, 255))  # Default to yellow if missing

        # Adjust Y-coordinate if using a bottom-left origin system (invert Y)
        y_adjusted = height - int(y)  # Invert the Y coordinate to fit OpenCV's top-left origin
        print(f"Original Y: {y}, Adjusted Y: {y_adjusted}")

        # Draw the detected dot
        cv2.circle(annotated_img, (int(x), y_adjusted), 3, color, -1)

        # Draw the enclosing circle (size visualization)
        cv2.circle(annotated_img, (int(x), y_adjusted), int(np.sqrt(area / np.pi)), (0, 255, 0), 1)

        # Display column number near the dot
        cv2.putText(annotated_img, f"Col {int(col_label)}", (int(x) - 10, y_adjusted + 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

    # Display using OpenCV
    cv2.imshow("Redrawn Image with Colored Dots", annotated_img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    # Save the image
    cv2.imwrite("redrawn_dots_on_original.jpg", annotated_img)
    print("Redrawn image saved as 'redrawn_dots_on_original.jpg'.")

    return annotated_img

