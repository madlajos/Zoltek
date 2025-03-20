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



def img_ok_check(image, error_prefix):
    try:
        mean_brightness = np.mean(image.ravel())
        #print(f"DEBUG: Mean brightness of image: {mean_brightness}")
        if error_prefix=='E23':
            if mean_brightness < 0:  # Too dark
                error_code = f"{error_prefix}08"
                logger.error(error_code)
                return None, error_code
            elif mean_brightness > 25:  # Too bright
                error_code = f"{error_prefix}09"
                logger.error(error_code)
                return None, error_code
            else:
                return image, None
        else:
            if mean_brightness < 11:  # Too dark
                error_code = f"{error_prefix}08"
                logger.error(error_code)
                return None, error_code
            elif mean_brightness > 25:  # Too bright
                error_code = f"{error_prefix}09"
                logger.error(error_code)
                return None, error_code
            else:
                return image, None

    except:
        logger.error("E2010")
        return None, "E2010"


