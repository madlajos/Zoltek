import cv2
import numpy as np
import matplotlib.pyplot as plt
import random

# Load the image
image_path = "D:\\source\\Zoltek\\dots_image.png"
image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

# Threshold the image
_, binary_image = cv2.threshold(image, 190, 255, cv2.THRESH_BINARY)

# Find contours of the white dots
contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# Filter contours to keep only circular ones
dots = []
dot_radii = []  # To store radii of each dot
for contour in contours:
    area = cv2.contourArea(contour)
    perimeter = cv2.arcLength(contour, True)
    if perimeter > 0:
        circularity = 4 * np.pi * (area / (perimeter * perimeter))
        if 0.1 < circularity < 1.2:  # Adjust circularity range
            ((x, y), radius) = cv2.minEnclosingCircle(contour)
            dots.append((int(x), int(y)))
            dot_radii.append(radius)  # Save the radius

# Known number of dots in each radial row
row_counts = [3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 6, 6, 7, 7, 7, 8, 8, 8, 9, 9, 9, 9,
              10, 10, 10, 11, 11, 11, 12, 12, 12, 12, 13, 13, 13, 14, 14, 14, 15, 15, 15,
              15, 16, 16, 16, 17, 17, 17, 18, 18, 18, 18, 19, 19, 19, 20, 20, 20, 21, 21,
              21, 21, 22, 22, 22, 23, 23, 23, 24, 24, 24, 24, 25, 25, 25, 26, 26, 26, 27,
              27, 27, 27, 28, 28, 28, 29, 29, 29, 30, 30, 30, 30, 31, 31, 31, 32, 32, 32,
              32, 33, 33, 33, 34, 34, 34, 35, 35, 35, 35, 36, 36, 36, 37, 37, 37, 38, 38,
              38, 38, 39, 39, 39, 40, 40, 40, 40]

# Define tolerances
horizontal_tolerance = 15  # Allowable horizontal distance
vertical_tolerance = 40  # Allowable vertical distance

# Always start each row from the bottom-left corner
rows = []
row_radii = []
used_dots = set()

# Define a function to find the bottom-left dot in a given set of dots
def find_bottom_left(dots):
    return min(dots, key=lambda d: (d[0], -d[1]))  # Bottom-left: smallest x, largest y

# Iterate through row counts and connect dots
for count in row_counts:
    available_dots = [d for d in dots if d not in used_dots]
    if not available_dots:
        break  # No more dots available

    # Start the row with the bottom-left dot
    current_row = [find_bottom_left(available_dots)]
    current_row_radii = [dot_radii[dots.index(current_row[0])]]
    used_dots.add(current_row[0])

    # Connect the remaining dots for the current row using tolerances
    for _ in range(count - 1):  # Already have the first dot
        available_dots = [d for d in dots if d not in used_dots]
        if not available_dots:
            break  # No more dots to add
        last_dot = current_row[-1]

        # Find the nearest dot, prioritizing vertical alignment
        valid_dots = [
            d for d in available_dots
            if abs(d[0] - last_dot[0]) <= horizontal_tolerance and abs(d[1] - last_dot[1]) <= vertical_tolerance
        ]
        if not valid_dots:
            break  # No valid dots within tolerances
        # Sort by vertical proximity first, then horizontal proximity
        next_dot = min(
            valid_dots,
            key=lambda d: (abs(d[1] - last_dot[1]), abs(d[0] - last_dot[0]))
        )
        current_row.append(next_dot)
        current_row_radii.append(dot_radii[dots.index(next_dot)])
        used_dots.add(next_dot)

    # Add the completed row to the rows list
    rows.append(current_row)
    row_radii.append(current_row_radii)

# Initialize an output image
output_image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

# Draw arcs for each circular row with random colors and annotate row numbers
for idx, (row, radii) in enumerate(zip(rows, row_radii)):
    if len(row) > 1:
        pts = np.array(row, dtype=np.int32)
        color = [random.randint(0, 255) for _ in range(3)]  # Generate random RGB color
        cv2.polylines(output_image, [pts], isClosed=False, color=color, thickness=2)

        # Annotate the row number at the starting point
        start_x, start_y = row[0]
        cv2.putText(output_image, f"Row {idx + 1}", (start_x + 5, start_y - 5),
                    fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=0.5, color=(255, 255, 255), thickness=1)

        # Detect anomalies (outliers) in the row
        median_radius = np.median(radii)  # Determine the "normal" size
        for (dot, radius) in zip(row, radii):
            if radius < 0.7 * median_radius:  # Anomaly: smaller than 70% of the normal size
                x, y = dot
                cv2.circle(output_image, (x, y), 10, (0, 0, 255), 2)  # Highlight anomaly in red

# Display the result
plt.imshow(cv2.cvtColor(output_image, cv2.COLOR_BGR2RGB))
plt.title("Anomaly Detection in Rows")
plt.axis("off")
plt.show()
