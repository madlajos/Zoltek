import cv2
import numpy as np
from GeneralProc.logger import logger

def template_match_with_polygon(cropped_image, template, scale_factor=0.1):

        try:
            if template is None or cropped_image is None:
                #logger.error("E2311")
                return None, None, None, "E2311"

            # ✅ **Step 1: Downscale Images for Faster Matching**
            small_cropped = cv2.resize(cropped_image, None, fx=scale_factor, fy=scale_factor,
                                       interpolation=cv2.INTER_AREA)
            small_template = cv2.resize(template, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_AREA)

            if small_cropped.size == 0 or small_template.size == 0:
              #  logger.error("E2312")
                return None, None, None, "E2312"

            # ✅ **Step 2: Run Template Matching on Smaller Images**
            result = cv2.matchTemplate(small_cropped, small_template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            best_top_left = (int(max_loc[0] / scale_factor), int(max_loc[1] / scale_factor))  # Upscale match location

            # ✅ **Step 3: Extract Matched Region from Original Image**
            best_template_height, best_template_width = template.shape
            top_left = best_top_left
            bottom_right = (top_left[0] + best_template_width, top_left[1] + best_template_height)

            if bottom_right[0] > cropped_image.shape[1] or bottom_right[1] > cropped_image.shape[0]:
                #logger.error("E2313")
                return None, None, None, "E2313"

            matched_region = cropped_image[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]]

            # ✅ **Step 4: Create Binary Mask**
            original_mask = np.zeros_like(template, dtype=np.uint8)
            original_mask[template > 10] = 1  # Threshold the mask, NOT the image

            if original_mask.sum() == 0:
              #  logger.error("E2314")
                return None, None, None, "E2314"
            # ✅ **Find the first white pixel from the left across the entire mask**

            # ✅ **Find the first white pixel from the left using np.argmax (FAST)**
            first_dot_x = np.argmax(original_mask.any(axis=0))  # Finds the first column with a white pixel

            # ✅ **Crop all relevant images from the left**
            original_mask = original_mask[:, first_dot_x:]
            matched_region = matched_region[:, first_dot_x:]
            top_left2 = (top_left[0] + first_dot_x, top_left[1])
            # ✅ **Now Apply Dilation After Cropping**
            # Get dimensions of the original mask
            h, w = original_mask.shape

            # Define scale factor (you can adjust this!)
            kernel_scale = 0.20  # 10% of mask height

            # Calculate kernel dimensions
            kernel_height = max(1, int(h * kernel_scale))
            kernel_width = max(1, int(h * kernel_scale * 0.5))  # narrower kernel for less horizontal spread

            # Create the kernel
            kernel = np.ones((kernel_height, kernel_width), np.uint8)
            expanded_mask = cv2.dilate(original_mask, kernel, iterations=1)

            # ✅ Resize mask to match `matched_region`
            expanded_mask_resized = cv2.resize(expanded_mask, (matched_region.shape[1], matched_region.shape[0]),
                                               interpolation=cv2.INTER_NEAREST)

            # ✅ Ensure the mask is binary (0 or 255) for OpenCV compatibility
            expanded_mask_resized = (expanded_mask_resized > 0).astype(np.uint8) * 255

            # ✅ Check if the mask is empty after processing
            if expanded_mask_resized.sum() == 0:
              #  logger.error("E2315")
                return None, None, None, "E2315"

            # ✅ Apply resized mask to `matched_region`
            masked_polygon_region = cv2.bitwise_and(matched_region, matched_region, mask=expanded_mask_resized)

            if masked_polygon_region.sum() == 0:
              #  logger.error("E2316")
                return None, None, None, "E2316"

            # ✅ **Annotate the matched polygon on the cropped image**
            annotated_image = cv2.cvtColor(cropped_image, cv2.COLOR_GRAY2BGR)
            cv2.rectangle(annotated_image, top_left, bottom_right, (0, 255, 0), 2)
            cv2.putText(annotated_image, f"Scale: {scale_factor:.2f}", (top_left[0], top_left[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

            return masked_polygon_region, annotated_image, expanded_mask_resized, (top_left2, bottom_right), None

        except FileNotFoundError as e:
         #   logger.error("E2317")
            return None, None, None, "E2317"

        except ValueError as e:
         #   logger.error("E2318")
            return None, None, None, "E2318"

        except IndexError as e:
         #   logger.error("E2319")
            return None, None, None, "E2319"

        except Exception as e:
         #   logger.error("E2320")
            return None, None, None, "E2320"  # General unknown error