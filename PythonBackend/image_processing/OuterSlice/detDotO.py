import os
import numpy as np
import cv2
import pandas as pd
import time
import matplotlib as plt

from GeneralProc.logger import logger


def eval_poly(coeffs, x):
    """Evaluate polynomial given its coefficients using Horner's method."""
    result = np.zeros_like(x)
    for c in coeffs:
        result = result * x + c
    return result
def fast_median(arr):
    n = len(arr)
    k = n // 2
    if n % 2 == 1:
        return np.partition(arr, k)[k]
    else:
        part = np.partition(arr, [k - 1, k])
        return 0.5 * (part[k - 1] + part[k])

def get_curve_deviation(coeffs, y_range, num_points=44):
    min_y, max_y = y_range
    y_vals = np.linspace(min_y, max_y, num_points)
    x_vals = eval_poly(coeffs, y_vals)

    y_mean = np.mean(y_vals)
    x_mean = np.mean(x_vals)
    dy = y_vals - y_mean
    dx = x_vals - x_mean
    slope = np.sum(dy * dx) / np.sum(dy ** 2)
    intercept = x_mean - slope * y_mean

    x_linear = slope * y_vals + intercept
    deviations = np.abs(x_vals - x_linear)
    return fast_median(deviations)

def check_curve_quality(coeffs, y_range, num_points=44, max_mean_dev=44):
    mean_deviation = get_curve_deviation(coeffs, y_range, num_points)
    return 10 < mean_deviation < max_mean_dev


def generate_gradient_colors(n):
    colormap = plt.cm.get_cmap('jet', n)
    return [(int(255 * r), int(255 * g), int(255 * b)) for r, g, b, _ in colormap(np.linspace(0, 1, n))]


def collect_column_from_seed(seed_dot, dots, y_thresh, x_thresh=25, direction_mode='both',
                             max_x_deviation=25, y_step=80):
    column = []
    original_dots = dots.copy()

    if direction_mode == 'both':
        directions = [-1, 1]
    elif direction_mode in [-1, 1]:
        directions = [direction_mode]
    else:
        raise ValueError("direction_mode must be 'both', -1, or 1")

    for direction in directions:
        current_dot = seed_dot
        local_column = []
        local_dots = dots.copy()

        while True:
            if len(local_dots) == 0:
                break

            y_relative = local_dots[:, 1] - current_dot[1]
            y_diff = np.abs(y_relative)
            x_diff = np.abs(local_dots[:, 0] - current_dot[0])

            if direction == -1:
                mask = (y_relative < 0) & (y_diff <= y_thresh) & (x_diff <= x_thresh)
            elif direction == 1:
                mask = (y_relative > 0) & (y_diff <= y_thresh) & (x_diff <= x_thresh)

            candidates = local_dots[mask]
            candidates = [p for p in candidates if not np.array_equal(p, current_dot)]

            if not candidates:
                break

            y_candidates = np.array([p[1] for p in candidates])
            y_diffs = np.abs(y_candidates - current_dot[1])
            next_dot = candidates[np.argmin(y_diffs)]
            local_column.append(next_dot)

            local_dots = np.array([p for p in local_dots if not np.array_equal(p, next_dot)])
            current_dot = next_dot

        # 🔄 Ha legalább 1 pont → függőleges egyenes mentén továbbkeresés (fix x)
        if len(local_column) >= 1:
            last_pt = np.array(local_column[-1])
            x_fixed = last_pt[0]  # ez lesz a függőleges egyenes (x konstans)
            y_pos = last_pt[1]
            used = set(tuple(p[:2]) for p in local_column + [seed_dot])
            extension_points = []

            steps_without_hit = 0
            max_steps = 10
            while steps_without_hit < 25 and len(extension_points) < max_steps:
                y_pos += direction * y_step

                x_all = original_dots[:, 0]
                y_all = original_dots[:, 1]
                x_diff = np.abs(x_all - x_fixed)
                y_diff = np.abs(y_all - y_pos)

                mask = (x_diff <= max_x_deviation) & (y_diff <= y_step)
                candidates = original_dots[mask]

                found = False
                for cand in candidates:
                    ct = tuple(cand[:2])
                    if ct not in used:
                        extension_points.append(cand)
                        used.add(ct)
                        y_pos = cand[1]  # frissítjük a következő kiinduló y-t
                        found = True
                        break

                if not found:
                    steps_without_hit += 1
                else:
                    steps_without_hit = 0

            local_column += extension_points

        column += local_column

    return [seed_dot] + column




def find_first_column_with_visual(dot_centers, image, tolerance_x=5, initial_step_y=40, delay=500, show_debug=True):
    try:
      #  debug_image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        sorted_dots = dot_centers[np.lexsort((dot_centers[:, 0], dot_centers[:, 1]))]
        remaining_dots = sorted_dots.copy()

        first_dot = remaining_dots[0]
        x0 = first_dot[0]
        same_col_mask = np.abs(remaining_dots[:, 0] - x0) <= 50
        same_col_dots = remaining_dots[same_col_mask]
        last_dot = same_col_dots[np.argmax(same_col_dots[:, 1])] if len(same_col_dots) > 0 else None

        left_candidates = remaining_dots[remaining_dots[:, 0] < x0]
        leftmost_dot = left_candidates[np.argmin(left_candidates[:, 0])] if len(left_candidates) > 0 else None

        if leftmost_dot is not None:
            if tuple(leftmost_dot) in [tuple(first_dot), tuple(last_dot) if last_dot is not None else ()]:
                leftmost_dot = None

        def fit_and_check(f_dot, l_dot, lm_dot):
            y_vals = np.array([f_dot[1], l_dot[1], lm_dot[1]])
            x_vals = np.array([f_dot[0], l_dot[0], lm_dot[0]])
            coeffs = np.polyfit(y_vals, x_vals, deg=2)
            return coeffs, int(min(y_vals)), int(max(y_vals))

        final_selected_column = []
        used_dots = []
        coeffs = None
        min_y, max_y = 0, 0

        max_attempts = 5
        attempt = 0
        unique_poly_coeffs = set()

        if last_dot is not None and first_dot is not None:
            temp_remaining = remaining_dots.copy()
            temp_first = first_dot
            temp_last = last_dot
            temp_leftmost = leftmost_dot

            prev_first, prev_last = None, None

            while attempt < max_attempts:
                attempt += 1

                if leftmost_dot is None:
                    final_selected_column = [first_dot, last_dot]
                    used_dots.extend(final_selected_column)
                    coeffs = None
                    break

                coeffs, min_y, max_y = fit_and_check(temp_first, temp_last, temp_leftmost)
                rounded_coeffs = tuple(np.round(coeffs, 2))
                unique_poly_coeffs.add(rounded_coeffs)

                if attempt == 1:
                    deviation = get_curve_deviation(coeffs, (min_y, max_y), num_points=3)
                    if deviation < 6:
                        final_selected_column = [temp_first, temp_last]
                        used_dots.extend(final_selected_column)
                        coeffs = None
                        break

                if not check_curve_quality(coeffs, (min_y, max_y)):
                    break

                y_all = temp_remaining[:, 1]
                x_all = temp_remaining[:, 0]
                x_pred_all = eval_poly(coeffs, y_all)

                y_thresh_bot = 0.8 * max_y + 0.2 * min_y
                bottom_mask = (y_all > y_thresh_bot) & (x_all < x_pred_all - 10) & (np.abs(x_all - x_pred_all) < 100)
                bottom_candidates = temp_remaining[bottom_mask]
                if len(bottom_candidates) > 0:
                    temp_last = bottom_candidates[np.argmax(bottom_candidates[:, 1])]

                y_thresh_top = 0.2 * max_y + 0.8 * min_y
                top_mask = (y_all < y_thresh_top) & (x_all < x_pred_all - 10) & (np.abs(x_all - x_pred_all) < 100)
                top_candidates = temp_remaining[top_mask]
                if len(top_candidates) > 0:
                    temp_first = top_candidates[np.argmin(top_candidates[:, 1])]

                if (prev_first is not None and
                        np.allclose(prev_first, temp_first, atol=1) and
                        np.allclose(prev_last, temp_last, atol=1)):
                    break

                prev_first = temp_first
                prev_last = temp_last
            seed_column_used = False
            fit_did_not_change = len(unique_poly_coeffs) == 1
            deviation = None
            skip_first_last_append = False
            if coeffs is not None:
                deviation = get_curve_deviation(coeffs, (min_y, max_y))

                if deviation is not None and deviation > 200:
                    return None, None, "2399"

                if deviation > 19 and temp_leftmost is not None:
                    final_selected_column = [temp_leftmost]
                    used_dots = [temp_leftmost]
                    y_thresh=1000
                    extra = collect_column_from_seed(temp_leftmost, temp_remaining, y_thresh)
                    final_selected_column += extra
                    used_dots += extra
                    coeffs = None
                    seed_column_used = True
                    skip_first_last_append = True  # ⛔ Ne rakjunk vissza first/last pontokat

                # 💡 Ha a first és last X-ben túl messze → inkább seedből indulunk
                x_dist_first_last = abs(temp_first[0] - temp_last[0])
                x_dist_thresh = 40  # vagy lazább: 30–40, ha ívesek az oszlopok
                # print(x_dist_first_last)
                # print(coeffs)
                # print(deviation)
                if x_dist_first_last >= x_dist_thresh and deviation < 19:
                  #  print('ok')
                    if deviation<10:
                        y_thresh=1000
                    else:
                        y_thresh=100
                    # --- 🔒 Szűrés: csak a görbe bal oldalán levő pontokat hagyjuk meg ---
                    # --- 🔒 Szűrés: csak a görbe bal oldalán levő pontokat hagyjuk meg ---
                    x_margin = 100  # vagy finomhangolható, pl. 5
                    y_vals_curve = temp_remaining[:, 1]
                    x_vals_curve = eval_poly(coeffs, y_vals_curve)
                    keep_mask = temp_remaining[:, 0] <= (x_vals_curve + x_margin)
                    filtered_temp_remaining = temp_remaining[keep_mask]

                    # 🚫 Kizárjuk a temp_first és temp_last pontokat (de majd visszatehetjük, ha közeliek y-ban)
                    filtered_temp_remaining = np.array([
                        p for p in filtered_temp_remaining
                        if not (np.array_equal(p, temp_first) or np.array_equal(p, temp_last))
                    ])

                    final_selected_column = [temp_leftmost]
                    used_dots = [temp_leftmost]

                    # Első gyűjtés (középről)
                    extra = collect_column_from_seed(temp_leftmost, filtered_temp_remaining, y_thresh)
                    final_selected_column += extra
                    used_dots += extra
                    if len(final_selected_column) >= 3:
                        y_vals = np.array([p[1] for p in final_selected_column])
                        x_vals = np.array([p[0] for p in final_selected_column])
                        coeffs = np.polyfit(y_vals, x_vals, deg=2)

                        threshold_distance = 15  # x-távolság
                        max_y_deviation = 80  # y-távolság a legtetejéhez/aljához képest

                        y_min_column = np.min(y_vals)
                        y_max_column = np.max(y_vals)

                        for dot in [temp_first, temp_last]:
                            if dot is None:
                                continue

                            y_dot = dot[1]
                            x_expected = eval_poly(coeffs, y_dot)
                            x_actual = dot[0]
                            dist_x = abs(x_actual - x_expected)

                            y_close_enough = (
                                    abs(y_dot - y_min_column) <= max_y_deviation or
                                    abs(y_dot - y_max_column) <= max_y_deviation
                            )

                            # print(
                            #     f"Checking dot {dot}, expected x: {x_expected}, actual x: {x_actual}, diff_x: {dist_x}, y_close: {y_close_enough}")

                            if dist_x < threshold_distance and y_close_enough:
                                if not any(np.array_equal(dot, p) for p in final_selected_column):
                                    final_selected_column.append(dot)
                                if not any(np.array_equal(dot, p) for p in used_dots):
                                    used_dots.append(dot)

                    coeffs = None
                    seed_column_used = True
                    skip_first_last_append = False

            if coeffs is not None:
                column_set = set(tuple(p) for p in final_selected_column)
                y_vals = range(min_y, max_y + 1, initial_step_y)
                y_all = temp_remaining[:, 1]
                x_all = temp_remaining[:, 0]

                for y in y_vals:
                    x_pred = eval_poly(coeffs, y)
                    y_diff = np.abs(y_all - y)
                    x_diff = np.abs(x_all - x_pred)
                    mask = (y_diff <= initial_step_y) & (x_diff <= tolerance_x + 10)
                    if np.any(mask):
                        candidates = temp_remaining[mask]
                        distances = y_diff[mask]
                        closest = candidates[np.argmin(distances)]
                        closest_t = tuple(np.round(closest, 2))
                        if closest_t not in column_set:
                            final_selected_column.append(closest)
                            used_dots.append(closest)
                            column_set.add(closest_t)

            if not seed_column_used and not skip_first_last_append:
                for dot in [temp_first, temp_last]:
                    if not any(np.array_equal(dot, sc) for sc in final_selected_column):
                        final_selected_column.append(dot)
                    if not any(np.array_equal(dot, sc) for sc in used_dots):
                        used_dots.append(dot)
        # === 🔍 DEBUG VIZUALIZÁCIÓ ===
        # if show_debug:
        #     window_name = "Column Debug View"
        #     if not hasattr(find_first_column_with_visual, "_window_initialized"):
        #         cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        #         setattr(find_first_column_with_visual, "_window_initialized", True)
        #
        #     debug_img = debug_image.copy()
        #     for dot in final_selected_column:
        #         cv2.circle(debug_img, (int(dot[0]), int(dot[1])), 5, (0, 0, 255), -1)
        #
        #     if coeffs is not None:
        #         for y in range(min_y, max_y + 1, 5):
        #             x = int(eval_poly(coeffs, y))
        #             cv2.circle(debug_img, (x, y), 1, (255, 255, 0), -1)

            # # === VONALAK: y_thresh_bot és y_thresh_top ===
            # y_thresh_bot = int(0.8 * max_y + 0.2 * min_y)
            # y_thresh_top = int(0.2 * max_y + 0.8 * min_y)
            # height, width = debug_img.shape[:2]
            #
            # cv2.line(debug_img, (0, y_thresh_bot), (width, y_thresh_bot), (0, 255, 0), 1)
            # cv2.line(debug_img, (0, y_thresh_top), (width, y_thresh_top), (255, 0, 0), 1)

            # # Info szöveg
            # cv2.putText(debug_img, f"Detected column points: {len(final_selected_column)}", (10, 25),
            #             cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
            #
            # resized = cv2.resize(debug_img, None, fx=0.3, fy=0.3)
            # cv2.imshow(window_name, resized)
            # cv2.waitKey(delay)

        # === 🧹 Maradék pontok szűrése ===
        if remaining_dots.shape[1] == 3:
            dtype = np.dtype([('x', remaining_dots.dtype),
                              ('y', remaining_dots.dtype),
                              ('area', remaining_dots.dtype)])
        elif remaining_dots.shape[1] == 2:
            dtype = np.dtype([('x', remaining_dots.dtype),
                              ('y', remaining_dots.dtype)])
        else:
            raise ValueError("Unsupported shape")

        structured_remaining = remaining_dots.view(dtype).squeeze()
        structured_used = np.array(used_dots).view(dtype).squeeze()
        mask = ~np.isin(structured_remaining, structured_used)
        remaining_dots = remaining_dots[mask]

        return np.array(final_selected_column), remaining_dots, None

    except Exception as e:

        return None, None, "E2323"



def detect_small_dots_and_contours(masked_region, drawtf, x_threshold=40):
    try:
        if masked_region is None or masked_region.size == 0:
            return None, "E2321"

        _, thresh = cv2.threshold(cv2.resize(masked_region, None, fx=1, fy=1, interpolation=cv2.INTER_AREA),
                                  50, 255, cv2.THRESH_BINARY)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None, "E2322"

        dot_areas = np.array([cv2.contourArea(cnt) for cnt in contours])
        valid_contours = dot_areas > 1

        centers = np.array([cv2.minEnclosingCircle(cnt)[0] for cnt in contours], dtype=np.int32)
        dot_centers = np.column_stack((centers[valid_contours], dot_areas[valid_contours]))

        if len(dot_centers) < 2:
            return None, "E2323"

        columns = []
        column_labels = {}
        column_x_positions = []

        max_columns = 77
        column_index = 0

        while len(dot_centers) > 0 and len(columns) < max_columns:
            first_column, remaining_dots, emsg = find_first_column_with_visual(dot_centers, masked_region)

            if first_column is None:
                break

            for dot in first_column:
                column_labels[tuple(dot)] = column_index

            columns.append(first_column)
            leftmost_x = min(first_column, key=lambda d: d[0])[0]
            column_x_positions.append(leftmost_x)
            column_index += 1

            if remaining_dots.size > 0:
                remaining_dots = np.array(remaining_dots)
                remaining_dots = remaining_dots[np.argsort(remaining_dots[:, 0])]
                dot_centers = remaining_dots
            else:
                dot_centers = np.array([])

        # Detect missing columns based on large gaps in X positions
        sorted_x_positions = sorted(column_x_positions)
        x_diffs = np.diff(sorted_x_positions)
        median_diff = np.mean(x_diffs)
        missing_column_indices = set()

        missing_column_indices = sorted(missing_column_indices)

        shift_map = {0: 0}
        shift = 0
        i = 0

        while i < len(column_x_positions) - 1:
            x1 = column_x_positions[i]
            x2 = column_x_positions[i + 1]
            diff = x2 - x1

            if diff > 1.7 * median_diff:
                # mennyi oszlopnyi helyet ugrottunk át?
                num_missing = int(round(diff / median_diff)) - 1
                shift += num_missing
                shift_map[i + 1] = shift
                # utána minden másik oszlop már csak 1-gyel shiftel (mintha egyetlen oszlop hiányzott volna)
                for j in range(i + 2, len(column_x_positions)):
                    shift_map[j] = shift - (num_missing - 1)
                break  # csak az első nagy hézag érdekel
            else:
                shift_map[i + 1] = shift
            i += 1

        annotated_dots = cv2.cvtColor(cv2.resize(masked_region, None, fx=1, fy=1, interpolation=cv2.INTER_AREA),
                                      cv2.COLOR_GRAY2BGR)

        # Számoljuk meg, hány oszlopot ugrottunk át
        num_missing_total = shift

        # Levágás: a jobb oldalról (végéről) ennyi oszlopot dobunk el
        if num_missing_total > 0 and len(columns) > num_missing_total:
            columns = columns[:-num_missing_total]

        best_match = 1
        starting_label = 127
        data = []
        # Teljes data tömb: (x, y) duplikáció-ellenőrzés
        seen_coords = set()
        duplicates = set()



        for col_idx, column_array in enumerate(columns):
            label = starting_label - col_idx - shift_map.get(col_idx, 0)
            for row in column_array:
                x, y, area = row
                data.append((x, y, label, area))
        colors = generate_gradient_colors(len(columns) + len(set(missing_column_indices)))
        column_colors = {127 - col_idx - shift_map[col_idx]: colors[col_idx] for col_idx in range(len(columns))}

        annotated_dots_sorted = cv2.cvtColor(cv2.resize(masked_region, None, fx=1, fy=1, interpolation=cv2.INTER_AREA),
                                             cv2.COLOR_GRAY2BGR)

        for (x, y, col_label, area) in data:
            color = column_colors.get(col_label, (255, 255, 255))
            cv2.circle(annotated_dots_sorted, (int(x), int(y)), 3, color, -1)
            cv2.circle(annotated_dots_sorted, (int(x), int(y)), int(np.sqrt(area / np.pi)), (0, 255, 0), 1)
            cv2.putText(annotated_dots_sorted, f"Col {int(col_label)}", (int(x) - 10, int(y) + 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            # Display dot area near the dot
            cv2.putText(annotated_dots_sorted, f"{int(area)}", (int(x) + 10, int(y) - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)

        if drawtf:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"result_sidepizza_{timestamp}.jpg"
            results_dir = os.path.join(os.getcwd(), "Results")
            os.makedirs(results_dir, exist_ok=True)
            cv2.imwrite(os.path.join(results_dir, filename), annotated_dots_sorted)
      #  print(data)
        return data, annotated_dots, columns, best_match, None

    except Exception as e:
        return None, None, None, None, "E2327"
