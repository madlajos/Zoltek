import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)


def islice_template_match_with_polygon(cropped_image, template, start_x=0, start_y=0, scale_factor=0.1):
    """Performs template matching with polygon masking and error handling."""

    try:
        # Validate Input
        if cropped_image is None or template is None:
          #  logger.error("E2212")  # Error Code for None input
            return None, "E2212"

        #  **Step 1: Downscale Images for Faster Matching**
        try:
            small_cropped = cv2.resize(cropped_image, None, fx=scale_factor, fy=scale_factor,
                                       interpolation=cv2.INTER_AREA)
            small_template = cv2.resize(template, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_AREA)
        except cv2.error as e:
          #  logger.error("E2213")  # Error Code for resize failure
            return None, "E2213"

        # ✅ **Step 2: Run Template Matching on Smaller Images**
        try:
            result = cv2.matchTemplate(small_cropped, small_template, cv2.TM_CCOEFF_NORMED)
            if result is None or result.size == 0:
                raise ValueError("Template matching failed. No result returned.")
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
        except cv2.error as e:
           # logger.error("E2214")  # Error Code for template matching failure
            return None, "E2214"
        except ValueError as ve:
            #logger.error("E2215")  # Error Code for no matching result
            return None, "E2215"

        best_match = template  # Keep original template reference
        best_top_left = (
        int(max_loc[0] / scale_factor) + start_x, int(max_loc[1] / scale_factor) + start_y)  # Upscale match location

        # **Step 3: Extract Matched Region from Original Image (Not Downscaled)**
        try:
            best_template_height, best_template_width = best_match.shape
            top_left = best_top_left
            bottom_right = (top_left[0] + best_template_width, top_left[1] + best_template_height)

            if bottom_right[0] > cropped_image.shape[1] or bottom_right[1] > cropped_image.shape[0]:
          #      logger.error("E2216")  # Error Code for exceeding image bounds
                return None, "E2216"

            matched_region = cropped_image[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]]
        except Exception as e:
           # logger.error("E2217")  # Error Code for error in extracting matched region
            return None, "E2217"

        #  **Step 4: Create Binary Mask**
        try:
            original_mask = np.zeros_like(best_match, dtype=np.uint8)
            original_mask[best_match > 10] = 1  # Threshold the mask, NOT the image
        except Exception as e:
          #  logger.error("E2218")  # Error Code for creating mask failure
            return None, "E2218"

        # ✅ **Step 5: Expand the Mask by 15 Pixels**
        try:
            # Dynamically size the kernel based on mask height
            h, w = original_mask.shape
            kernel_scale = 0.2  # 20% of mask height
            kernel_height = max(1, int(h * kernel_scale))
            kernel_width = max(1, int(h * kernel_scale * 0.5))  # narrower width

            kernel = np.ones((kernel_height, kernel_width), np.uint8)

            expanded_mask = cv2.dilate(original_mask, kernel, iterations=1)
        except cv2.error as e:
           # logger.error("E2219")  # Error Code for dilation failure
            return None, "E2219"

        #  Resize mask to match `matched_region`
        try:
            expanded_mask_resized = cv2.resize(expanded_mask, (matched_region.shape[1], matched_region.shape[0]),
                                               interpolation=cv2.INTER_NEAREST)

            # Ensure the mask is binary (0 or 255) for OpenCV compatibility
            expanded_mask_resized = (expanded_mask_resized > 0).astype(np.uint8) * 255
        except cv2.error as e:
          #  logger.error("E2220")  # Error Code for resizing failure
            return None, "E2220"

        # ✅ Apply resized mask to `matched_region`
        try:
            masked_polygon_region = cv2.bitwise_and(matched_region, matched_region, mask=expanded_mask_resized)
        except cv2.error as e:
           # logger.error("E2221")  # Error Code for bitwise operation failure
            return None, "E2221"

        return masked_polygon_region, best_top_left, None  # Success

    except Exception as e:
        # logger.error("E2222")  # General error code for unexpected failure
        return None, "E2222"
