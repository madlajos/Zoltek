import os
import numpy as np
import cv2
import pandas as pd
import time
import matplotlib.pyplot as plt

from GeneralProc.logger import logger


def eval_poly(coeffs, x):
    if np.isscalar(x):
        result = 0.0
        for c in coeffs:
            result = result * x + c
        return result
    else:
        result = np.zeros(x.shape, dtype=np.float64)
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



def collect_column_from_seed(seed_dot, dots, y_thresh, x_thresh=15, direction_mode='both',
                             max_x_deviation=25, y_step=10):
    #print('SEED DOT', seed_dot)
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
            else:  # direction == 1
                mask = (y_relative > 0) & (y_diff <= y_thresh) & (x_diff <= x_thresh)

            candidates = local_dots[mask]

            if len(candidates) == 0:
                break

            # Optimalizált kiválasztás
            y_candidates = candidates[:, 1]
            y_deltas = candidates[:, 1] - current_dot[1]

            if direction == 1:
                valid_mask = (y_deltas > 0) & (y_deltas <= y_thresh)
            else:
                valid_mask = (y_deltas < 0) & (np.abs(y_deltas) <= y_thresh)

            valid_candidates = candidates[valid_mask]

            if len(valid_candidates) == 0:
                break

            # Válaszd a legkisebb abszolút y lépést
            best_idx = np.argmin(np.abs(valid_candidates[:, 1] - current_dot[1]))
            next_dot = valid_candidates[best_idx]
            local_column.append(next_dot)

            # Vektoros eltávolítás a local_dots-ból
            keep_mask = ~np.all(local_dots == next_dot, axis=1)
            local_dots = local_dots[keep_mask]

            current_dot = next_dot

        # 🔄 Ha legalább 1 pont → függőleges egyenes mentén továbbkeresés (fix x)
        if len(local_column) >= 1:
            last_pt = np.array(local_column[-1])
            x_fixed = last_pt[0]  # ez lesz a függőleges egyenes (x konstans)
            y_pos = last_pt[1]
            used = set(tuple(p[:2]) for p in local_column + [seed_dot])
            extension_points = []

            steps_without_hit = 0
            max_steps = 5
            while steps_without_hit < 100 and len(extension_points) < max_steps:
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





def find_first_column_with_visual(dot_centers, image, tolerance_x=5, initial_step_y=20, delay=500, show_debug=True):
    try:
        debug_image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        sorted_dots = dot_centers[np.lexsort((dot_centers[:, 0], dot_centers[:, 1]))]
        remaining_dots = sorted_dots.copy()

        first_dot = remaining_dots[0]
        x0 = first_dot[0]
        same_col_mask = np.abs(remaining_dots[:, 0] - x0) <= 25
        same_col_dots = remaining_dots[same_col_mask]
        last_dot = same_col_dots[np.argmax(same_col_dots[:, 1])] if len(same_col_dots) >= 0 else None

        left_candidates = remaining_dots[remaining_dots[:, 0] < x0]
        leftmost_dot = left_candidates[np.argmin(left_candidates[:, 0])] if len(left_candidates) > 0 else None
       # print('FIRST', first_dot, leftmost_dot, last_dot)
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
          #  print('last dot and first dot is not none')
            temp_remaining = remaining_dots.copy()
            temp_first = first_dot
            temp_last = last_dot
            temp_leftmost = leftmost_dot

            prev_first, prev_last = None, None

            while attempt < max_attempts:
                attempt += 1

                if leftmost_dot is None:
                   # print('leftmost_dot is not none')
                    # 🔁 Próbáljuk meg a first_dot-ból seed alapján építeni az oszlopot
                    y_thresh = 100  # vagy 1000, ha kevés pont van
                    extra = collect_column_from_seed(first_dot, remaining_dots, y_thresh=y_thresh)
                    if len(extra) >= 3:
                        final_selected_column = extra
                        used_dots = extra
                        coeffs = None
                        seed_column_used = True
                    else:
                        final_selected_column = [first_dot, last_dot]
                        used_dots.extend(final_selected_column)
                        coeffs = None
                    break
                coeffs, min_y, max_y = fit_and_check(temp_first, temp_last, temp_leftmost)

                rounded_coeffs = tuple(np.round(coeffs, 2))
                unique_poly_coeffs.add(rounded_coeffs)

                if not check_curve_quality(coeffs, (min_y, max_y)):
                    break

                y_all = temp_remaining[:, 1]
                x_all = temp_remaining[:, 0]
                x_pred_all = eval_poly(coeffs, y_all)

                y_thresh_bot = 0.8 * max_y + 0.2 * min_y
                bottom_mask = (y_all > y_thresh_bot) & (x_all < x_pred_all - 10) & (np.abs(x_all - x_pred_all) < 100)
                bottom_candidates = temp_remaining[bottom_mask]
                #print('BOTT CAND', bottom_candidates)
                if len(bottom_candidates) > 0:
                    temp_last = bottom_candidates[np.argmax(bottom_candidates[:, 1])]

                y_thresh_top = 0.2 * max_y + 0.8 * min_y
                top_mask = (y_all < y_thresh_top) & (x_all < x_pred_all - 10) & (np.abs(x_all - x_pred_all) < 100)
                top_candidates = temp_remaining[top_mask]
                #print('TOP CAN', top_candidates)
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
               # print('DEV', deviation)
                if deviation is not None and deviation > 5000:

                    return None, None, "2299"


                if (deviation > 14 and temp_leftmost is not None) or deviation<0.99:
                   # print('DEV<10 and temp_left not None')
                    y_thresh=1000
                   # print('TEMP_REM', len(temp_remaining))
                    extra = collect_column_from_seed(temp_leftmost, temp_remaining, y_thresh)
                    final_selected_column = extra
                    used_dots = extra
                    coeffs = None
                    seed_column_used = True
                    skip_first_last_append = True  # ⛔ Ne rakjunk vissza first/last pontokat

                # 💡 Ha a first és last X-ben túl messze → inkább seedből indulunk
                x_dist_first_last = abs(temp_first[0] - temp_last[0])
                x_dist_thresh = 5  # vagy lazább: 30–40, ha ívesek az oszlopok
              #  print('X_DIST', x_dist_first_last)
                # print(coeffs)

                if x_dist_first_last >= x_dist_thresh or x_dist_first_last<=1:
                   # print('X_DIST and deviation')
                    if deviation<10:
                        y_thresh=1000
                    else:
                        y_thresh=1000

                    # --- 🔒 Szűrés: csak a görbe bal oldalán levő pontokat hagyjuk meg ---
                    # --- 🔒 Szűrés: csak a görbe bal oldalán levő pontokat hagyjuk meg ---
                    x_margin = 50  # vagy finomhangolható, pl. 5
                    y_vals_curve = temp_remaining[:, 1]
                    #print('Y_vals_curve', y_vals_curve)
                    #x_vals_curve = eval_poly(coeffs, y_vals_curve)

                    #print('OK3')
                    #keep_mask = temp_remaining[:, 0] <= (x_vals_curve + x_margin)
                    filtered_temp_remaining = temp_remaining#[keep_mask]
                   # print('FILTERED REM', filtered_temp_remaining)
                   # 🚫 Kizárjuk a temp_first és temp_last pontokat (de majd visszatehetjük, ha közeliek y-ban)
                   #  filtered_temp_remaining = np.array([
                   #      p for p in filtered_temp_remaining
                   #      if not (np.array_equal(p, temp_first) or np.array_equal(p, temp_last))
                   #  ])

                    final_selected_column = [temp_leftmost]
                    used_dots = [temp_leftmost]

                    # Első gyűjtés (középről)
                    extra = collect_column_from_seed(temp_leftmost, filtered_temp_remaining, y_thresh)
                    final_selected_column = extra
                    used_dots = extra
                    if len(final_selected_column) >= 3:
                        y_vals = np.array([p[1] for p in final_selected_column])
                        x_vals = np.array([p[0] for p in final_selected_column])
                        coeffs = np.polyfit(y_vals, x_vals, deg=2)

                        threshold_distance = 20  # x-távolság
                        max_y_deviation = 300  # y-távolság a legtetejéhez/aljához képest

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

           # print(temp_first, temp_last, temp_leftmost)
            if not seed_column_used and not skip_first_last_append:
                for dot in [temp_first, temp_last]:
                  #  print(temp_first,temp_last, temp_leftmost)
                    if not any(np.array_equal(dot, sc) for sc in final_selected_column):
                        final_selected_column.append(dot)
                    if not any(np.array_equal(dot, sc) for sc in used_dots):
                        used_dots.append(dot)

        # # 🔍 Görbeillesztés a végleges pontokra – csak ha seed-ből épült az oszlop
        # if seed_column_used and len(final_selected_column) >= 10:
        #     y_vals = np.array([p[1] for p in final_selected_column])
        #     x_vals = np.array([p[0] for p in final_selected_column])
        #     coeffs = np.polyfit(y_vals, x_vals, deg=2)
        #
        #     for dot in remaining_dots:
        #         y = dot[1]
        #         x_pred = eval_poly(coeffs, y)
        #         if abs(dot[0] - x_pred) < 10:
        #             if not any(np.array_equal(dot, d) for d in final_selected_column):
        # #                 final_selected_column.append(dot)
        # # === 🔍 DEBUG VIZUALIZÁCIÓ ===
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
        #
        #
        #     # Info szöveg
        #     cv2.putText(debug_img, f"Detected column points: {len(final_selected_column)}", (10, 25),
        #                 cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        #
        #     resized = cv2.resize(debug_img, None, fx=0.3, fy=0.3)
        #     cv2.imshow(window_name, resized)
        #     cv2.waitKey(0)

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

        return None, None, "E2223"




def islice_detect_small_dots_and_contours (masked_region, drawtf=True):
     try:
        if masked_region is None or masked_region.size == 0:
            return None, None, "E2221"

        _, thresh = cv2.threshold(cv2.resize(masked_region, None, fx=1, fy=1, interpolation=cv2.INTER_AREA),
                                  50, 255, cv2.THRESH_BINARY)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None, None,  "E2222"

        dot_areas = np.array([cv2.contourArea(cnt) for cnt in contours])
        valid_contours = dot_areas > 1

        centers = np.array([cv2.minEnclosingCircle(cnt)[0] for cnt in contours], dtype=np.int32)
        dot_centers = np.column_stack((centers[valid_contours], dot_areas[valid_contours]))
        # Szűrés: töröljük a bal szélhez közeli pöttyöket (10 pixelen belül)

        # --- Dinamikus vonalillesztés pöttyök alapján ---

        # 1. Képméret és koordináták
        height, width = thresh.shape
        x = dot_centers[:, 0]
        y = dot_centers[:, 1]

        # 2. Legbaloldalibb és legjobboldalibb pötty alapján sávmeghatározás
        x_min = np.min(x)
        x_max = np.max(x)

        left_start = x_min + 0.0 * (x_max - x_min)
        left_end   = x_min + 0.10 * (x_max - x_min)
        mid_start  = x_min + 0.25 * (x_max - x_min)
        mid_end    = x_min + 0.35 * (x_max - x_min)

        left_band = (x >= left_start) & (x <= left_end)
        mid_band  = (x >= mid_start) & (x <= mid_end)

        left = dot_centers[left_band]
        mid  = dot_centers[mid_band]

        if len(left) == 0 or len(mid) == 0:
            return None, None, "E2223"

        # 3. Robusztus referenciapontok
        top_left = np.array([np.median(left[:, 0]), np.min(left[:, 1])])
        bottom_left = np.array([np.median(left[:, 0]), np.max(left[:, 1])])
        top_mid = np.array([np.median(mid[:, 0]), np.min(mid[:, 1])])
        bottom_mid = np.array([np.median(mid[:, 0]), np.max(mid[:, 1])])

        # 4. Egyenesek definíciója
        def line_y(x, p1, p2):
            m = (p2[1] - p1[1]) / (p2[0] - p1[0] + 1e-9)
            b = p1[1] - m * p1[0]
            return m * x + b

        # 5. Maszkolás pixel szinten
        tolerance = 30
        mask = np.ones_like(masked_region, dtype=np.uint8) * 255
        for xi in range(width):
            y_top = int(line_y(xi, top_left, top_mid) - tolerance)
            y_bottom = int(line_y(xi, bottom_left, bottom_mid) + tolerance)

            if y_top > 0:
                mask[:y_top, xi] = 0
            if y_bottom < height:
                mask[y_bottom:, xi] = 0

        # 6. Maszk alkalmazása
        masked_region = cv2.bitwise_and(masked_region, masked_region, mask=mask)


        # 7. Új küszöbölés és kontúrkeresés
        _, thresh = cv2.threshold(masked_region, 50, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return None, None, "E2224"

        dot_areas = np.array([cv2.contourArea(cnt) for cnt in contours])
        valid_contours = dot_areas > 1

        centers = np.array([cv2.minEnclosingCircle(cnt)[0] for cnt in contours], dtype=np.int32)
        dot_centers = np.column_stack((centers[valid_contours], dot_areas[valid_contours]))
        # Szűrés: töröljük a bal szélhez közeli pöttyöket (10 pixelen belül)
        edge_threshold = 10
        dot_centers = dot_centers[dot_centers[:, 0] > edge_threshold]

        if len(dot_centers) < 2:
            return None, None,  "E2225"

        columns = []
        column_labels = {}
        column_x_positions = []

        max_columns = 100
        column_index = 0
        expected_counts = [
            18, 17, 17, 17,
            16, 16, 16,
            15, 15, 15, 15,
            14, 14, 14,
            13, 13, 13,
            12, 12, 12, 12,
            11, 11, 11,
            10, 10, 10,
            9, 9, 9, 9,
            8, 8, 8,
            7, 7, 7,
            6, 6, 6, 6,
            5, 5, 5,
            4, 4, 4,
            3, 3, 3
        ]
        expected_counts = expected_counts[::-1]
        while len(dot_centers) > 0 and len(columns) < max_columns:
            first_column, remaining_dots, emsg = find_first_column_with_visual(dot_centers, masked_region)
            if first_column is None or len(first_column) == 0:
                return None, None, "E2227"
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


        columns = columns[-50:]
        column_x_positions = column_x_positions [-50:]
        columns=columns[::-1]


       # print(len(columns[0]))
       # print(len(columns[49]))
        # --- Ellenőrzések az első oszlopra ---
        image_width = masked_region.shape[1]
        right_edge_threshold = 10  # px

        # 1) Túl sok pötty az első oszlopban
        if len(columns[0]) > 3:
            return None, None, 'E2291'
        #print((image_width - column_x_positions[49]))
        # 2) Túl közel a jobb széléhez
        if (image_width - column_x_positions[49]) < right_edge_threshold:
            #print('OK5')
            return None, None, 'E2292'
        num_missing_total=0
        # ⬇️ Ellenőrzés: túl sok pötty a 3. oszlopban? (és shift valószínű)
        try:
            expected_3rd = expected_counts[2]
            actual_3rd = len(columns[2])

            if actual_3rd > expected_3rd:
                #print("📌 Feltételezés: az első oszlop hiányzik, mert a 3. oszlopban túl sok pötty van.")

                image_width = masked_region.shape[1]  # teljes kép szélessége
                right_edge_threshold = 30  # px, ennyinél közelebb a jobb szélhez → hiba

                # 🛑 Ellenőrzés: a 2. oszlop közel van a jobb széléhez?
                second_col_x = column_x_positions[1]

                if (image_width - second_col_x) < right_edge_threshold:
                 #   print('tul közeli pötty')
                    return None, None, 'E2290'  # túl közel van → hiba

                # Becsült oszloptáv
                if len(column_x_positions) >= 2:
                    estimated_unit = column_x_positions[1] - column_x_positions[0]
                else:
                    estimated_unit = 20  # fallback

                # ➕ Üres oszlop beszúrása az elejére
                columns.insert(0, [])
                column_x_positions.insert(0, column_x_positions[0] - estimated_unit)

                # 🔻 Levágás a végéről, hogy pontosan 50 maradjon
                if len(columns) > 50:
                    columns.pop()
                    column_x_positions.pop()

                num_missing_total = 1

        except IndexError:
            return None, None, '2280'

        shift_map = {0: 0}
        shift = 0

        # minimum oszloptáv amit még érvényesnek tekintünk (pl. képpontban)
        MIN_VALID_GAP = 15

        i = 0
        while i < len(column_x_positions) - 2:
            x0 = column_x_positions[i]
            x1 = column_x_positions[i + 1]
            x2 = column_x_positions[i + 2]

            left_gap = x1 - x0
            right_gap = x2 - x1

            if left_gap == 0 or right_gap == 0:
                i += 1
                continue  # oszlopok ugyanott? kihagyjuk

            ratio = max(left_gap, right_gap) / min(left_gap, right_gap)

            # Ha túl kicsi a kisebbik gap, lehet hogy összevont oszlop volt -> kihagyjuk
            if min(left_gap, right_gap) < MIN_VALID_GAP:

                return None, None, 'E2240'
            ratio = max(left_gap, right_gap) / min(left_gap, right_gap)
            if ratio > 2.5:
                # Hiányzó oszlop a nagyobbik gap oldalán van
                big_gap = max(left_gap, right_gap)
                small_gap = min(left_gap, right_gap)
                estimated_unit = small_gap  # feltételezzük, hogy a kisebbik a helyes oszloptáv

                num_missing = int(round(big_gap / estimated_unit)) - 1
                shift += num_missing
                shift_map[i + 2] = shift  # i+2-től kezdve shiftelünk

                for j in range(i + 3, len(column_x_positions)):
                    shift_map[j] = shift - (num_missing - 1)

                break  # csak az első gyanús résen dolgozunk
            else:
                shift_map[i + 1] = shift
            i += 1
        #print(shift, shift_map)
        num_missing_total = shift
        #print('num', num_missing_total)
        # # 🔻 Vágás: a jobb oldalról a túlcsúszott oszlopokat levágjuk
        if num_missing_total > 0 and len(columns) > num_missing_total:
            shift_map = {k: 1 - v for k, v in shift_map.items()}
           # print(shift_map)



        annotated_dots = cv2.cvtColor(cv2.resize(masked_region, None, fx=1, fy=1, interpolation=cv2.INTER_AREA),
                                     cv2.COLOR_GRAY2BGR)


       # print(len(columns))
      #   print('a', len(columns)-num_missing_total)
        # Extra logikák, ha pont 2248, de mégis gyanús

        # if len(columns)+num_missing_total  != 50:
        #     print("Suspicious column count:", len(columns))
        #     return None, None, "E2328"
        missing_list = []
        missing_columns = set()

        keys = sorted(shift_map.keys())

        for prev, curr in zip(keys, keys[1:]):
            if curr - prev > 1:
                # kimaradt index(ek) a kulcsok között
                for i in range(prev + 1, curr):
                    missing_columns.add(i)

       # print("Hiányzó oszlopok:", missing_columns)

        # Kiszámolni 50 - érték minden hiányzó oszlopra
        missing_columns = [50 - col for col in missing_columns]

        offset = 0  # ennyivel tolódik el az index a columns-ban
        for i in range(50):
            if i in missing_columns:
                offset += 1
                continue

            col_idx = i - offset
            if col_idx < 0 or col_idx >= len(columns):
                #print(f"❗ Hiba: col_idx={col_idx} kívül esik a columns tartományán")
                continue

            actual = len(columns[col_idx])
            expected = expected_counts[i]
            missing_list2 = expected-actual
          #  print(missing_list2)
            missing_list.append(missing_list2)
            # print(f"i={i + 1}, act={actual}, exp={expected}")

            if actual > expected:
                if i in (2, 3):  # ezeknél megengedett a torlódás
                    #print(f"⚠️ Túl sok pötty az oszlopban {i + 1}, de ez engedélyezett: {actual} > {expected}")
                    return None, None, "E22EO"
                else:
                    #print(f"❗ Túl sok pötty az oszlopban {i + 1}: {actual} > {expected}")
                    return None, None, "E2228"
       # print(missing_list)
        # # --- VALIDÁCIÓ az expected_counts alapján, immár a missing column kezelés UTÁN ---
        # for i, col in enumerate(columns):
        #     expected = expected_counts[i] if i < len(expected_counts) else expected_counts[-1]
        #     print(len(col) - expected)
        #    # if (len(col) - expected) > 0:
        #         # return None, None, "E2328"


        min_streak_length = 10
        min_repeats_for_dominant = 10


        # 2. Szakaszokra bontás (ahol missing != 0)
        start = None
        for i, m in enumerate(missing_list + [0]):  # extra 0 a végén, hogy lezárjuk a streaket
            if m != 0:
                if start is None:
                    start = i
            else:
                if start is not None:
                    streak = missing_list[start:i]
                    if len(streak) >= min_streak_length:
                        # Számoljuk, melyik érték szerepel legtöbbször
                        from collections import Counter
                        counts = Counter(streak)
                        most_common_val, freq = counts.most_common(1)[0]

                        if freq >= min_repeats_for_dominant:
                          #  print(
                           #    f"[E2327] Suspicious missing streak from col {start} to {i - 1} → {most_common_val} occurred {freq}×")
                            return None, None,  "E2229"
                    start = None
        if num_missing_total == 0:
            # Extra logikák, ha pont 2248, de mégis gyanús
            if len(columns) + num_missing_total != 50:
                # print("Suspicious column count:", len(columns))
                return None, None,"E2228"
            # --- VALIDÁCIÓ az expected_counts alapján, immár a missing column kezelés UTÁN ---
            for i, col in enumerate(columns):
                expected = expected_counts[i] if i < len(expected_counts) else expected_counts[-1]
                #  print(len(col) - expected)
                if (len(col) - expected) > 0:
                    return None, None, "E2228"

        best_match = 1
        starting_label = 1


        columns = columns[::-1]
        columns = columns[-len(columns) + num_missing_total:]
        data = []

        total_cols = len(columns)
        for col_idx, column_array in enumerate(columns):
            reversed_idx = total_cols - col_idx - 1
            label = starting_label + reversed_idx + shift_map.get(col_idx, 0)
          #  print(label)
            for row in column_array:
                x, y, area = row
                data.append((x, y, label, area))

        colors = generate_gradient_colors(50 + num_missing_total)


        column_colors = {
            50 + num_missing_total - col_idx - shift_map.get(col_idx, 0): colors[col_idx]
            for col_idx in range(len(columns))
                }

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
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1) # Új vizualizáció: fekete háttéren, ismétlődő pontok kiemelve



        # 1. Megszámoljuk, hányszor szerepel egy (x, y) pozíció

        # point_counts = {}
        # for x, y, *_ in data:
        #     key = (int(x), int(y))
        #     point_counts[key] = point_counts.get(key, 0) + 1
        #
        # # 2. Rajzolás: méret az area alapján, szín a duplikáció alapján
        # debug_img2 = np.zeros((height, width, 3), dtype=np.uint8)
        #
        # for x, y, col_label, area in data:
        #     pt = (int(x), int(y))
        #     radius = max(2, int(np.sqrt(area / np.pi)))  # legalább 2 pixel, de arányos az area-val
        #
        #     if point_counts[pt] > 1:
        #         color = (0, 0, 255)  # piros: többször szerepel
        #     else:
        #         color = (0, 255, 0)  # zöld: egyedi
        #
        #     cv2.circle(debug_img2, pt, radius, color, -1)
        # cv2.imshow('debug', cv2.resize(debug_img2, None, fy=0.3, fx=0.3, interpolation=cv2.INTER_AREA))
        #
        # cv2.waitKey(0)

        if drawtf:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"result_pizza_{timestamp}.jpg"
            results_dir = os.path.join(os.getcwd(), "Results")
            os.makedirs(results_dir, exist_ok=True)
            cv2.imwrite(os.path.join(results_dir, filename), annotated_dots_sorted)

        # for i, col in enumerate(columns):
        #     col_label = starting_label + i + shift_map.get(i, 0)  # vagy ami nálad a pontos label logika
        #     expected_index = col_label - 1  # mert expected_counts[0] → col 1
        #     expected = expected_counts[expected_index] if expected_index < len(expected_counts) else expected_counts[-1]
        #
        #     print(len(col) - expected)
        #     if (len(col) - expected) > 0:
        #         return None, None, "E2328"
        # Offset (bal-felső sarok az eredeti képen)


        # # Eredeti kép megjelölése
        # for x, y, label, area in adjusted_dot_data:
        #     cv2.circle(full_image, (int(x), int(y)), 4, (0, 255, 0), -1)
        #     cv2.putText(full_image, str(label), (int(x) + 6, int(y)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        #
        # cv2.imshow("Dots on full image", cv2.resize(full_image, None, fx=0.2, fy=0.2))
        # cv2.waitKey(0)


        a = 510 - len(data)
        data = data[::-1]
        # print(len(data))
       # print(data)
        if a < 0:

            return None, None, "E2230"

        #print(adjusted_dot_data)
        return data, annotated_dots, None

     except Exception as e:
        return None, None,  "E2231"