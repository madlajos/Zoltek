from GeneralProc.logger import logger
import os
import numpy as np
import cv2



def imgin_check(image, error_prefix):
    """Validate that the input is a grayscale NumPy image and return unique error codes per caller."""
    if image is None:
        error_code = f"{error_prefix}00"
        logger.error(error_code)
        return None, error_code

    if not isinstance(image, np.ndarray):
        error_code = f"{error_prefix}02"
        logger.error(error_code)
        return None, error_code

    if len(image.shape) != 2:
        error_code = f"{error_prefix}03"
        logger.error(error_code)
        return None, error_code

    return image, None

def template_check(template_path, error_prefix):
    """Load and validate the template image with function-specific error codes."""
    try:
        if not os.path.isfile(template_path):
            raise FileNotFoundError(f"{error_prefix}04")

        if not os.access(template_path, os.R_OK):
            raise PermissionError(f"{error_prefix}05")

        template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
        if template is None:
            raise ValueError(f"{error_prefix}06")

        return template, None

    except FileNotFoundError as e:
        logger.error(e)
        return None, str(e)

    except PermissionError as e:
        logger.error(e)
        return None, str(e)

    except ValueError as e:
        logger.error(e)
        return None, str(e)

    except Exception as e:
        error_code = f"{error_prefix}07"
        logger.error(f"{error_prefix}07")
        return None, error_code



def img_ok_check(image, error_prefix='E00', downscale_factor=0.1, grid_size=(32, 32), dot_thresh=50, show=False):


    try:

        # 2. Downscale early
        h, w = image.shape
        small = cv2.resize(image, (int(w * downscale_factor), int(h * downscale_factor)), interpolation=cv2.INTER_AREA)

        # 3. Threshold to binary
        _, dot_mask = cv2.threshold(small, dot_thresh, 255, cv2.THRESH_BINARY)

        # 4. Resize dot mask to grid size directly
        resized = cv2.resize(dot_mask, grid_size, interpolation=cv2.INTER_AREA)

        # 5. Estimate dot counts
        heatmap = resized.astype(np.float32) / 255.0  # Normalize
        low_density_cells = np.sum(heatmap < 0.05)     # Cells with < 5% white
        total_cells = heatmap.size
        ratio = low_density_cells / total_cells

        print(f"Low-density region ratio: {ratio:.2%} of image")

        # 6. Optional heatmap overlay
        if show:
            heatmap_norm = cv2.normalize(heatmap, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
            heatmap_big = cv2.resize(heatmap_norm, (w, h), interpolation=cv2.INTER_NEAREST)
            heatmap_color = cv2.applyColorMap(heatmap_big, cv2.COLORMAP_JET)
            overlay = cv2.addWeighted(cv2.cvtColor(image, cv2.COLOR_GRAY2BGR), 0.7, heatmap_color, 0.6, 0)
            cv2.imshow("Dot Density Heatmap", cv2.resize(overlay, None, fx=0.1, fy=0.1))
            cv2.waitKey(0)
            cv2.destroyAllWindows()

        # 7. Decision logic
        if error_prefix in ('E20', 'E21', 'E22') and ratio > 0.35:
            error_code = f"{error_prefix}08"
            logger.error(f"{error_code}")
            return None, error_code
        elif ratio > 0.40:
            error_code = f"{error_prefix}08"
            logger.error(f"{error_code}")
            return None, error_code

        mean_brightness = np.mean(image.ravel())
        print(f"DEBUG: Mean brightness of image: {mean_brightness}")
        if error_prefix == 'E23':
            if mean_brightness > 30:  # Too bright
                error_code = f"{error_prefix}09"
                logger.error(error_code)
                return None, error_code
            else:
                return image, None
        else:
            if mean_brightness > 30:  # Too bright
                error_code = f"{error_prefix}09"
                logger.error(error_code)
                return None, error_code
            else:
                return image, None

    except Exception as e:
        logger.error(f"{error_prefix}10")
        return None, f"{error_prefix}10"



