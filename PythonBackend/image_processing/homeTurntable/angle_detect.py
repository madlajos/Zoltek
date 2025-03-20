from concurrent.futures import ThreadPoolExecutor
import numpy as np
from homeTurntable.home_tempmatch import find_best_match_and_angle
from GeneralProc import logger  # Ensure the centralized logger is used

def angle_det(rotated_templates, image_rescaled):
    """Determine the best matching angle between the rotated templates and the input image."""

    # Check if inputs are valid
    if not rotated_templates or not isinstance(rotated_templates, dict):
        logger.error("E2012")
        return None, "E2012"

    if image_rescaled is None:
        logger.error("E2013")
        return None, "E2013"

    try:
        # Run `find_best_match_and_angle()` in parallel for all templates
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(
                lambda t: (t[0], *find_best_match_and_angle(image_rescaled, t[1])),
                rotated_templates.items()
            ))

        # Find the best match
        results = [(rotation, angle, score) for rotation, angle, score in results if angle is not None]

        if not results:
            logger.error("E2024")
            return None, "E2024"

        # Find the best score and corresponding angle
        best_rotation, best_angle, _ = max(results, key=lambda x: x[2])

        # Final angle calculation
        final_angle = (best_angle + best_rotation) % 360  # Normalize angle to [0, 360)
        normalized_angle = ((final_angle + 180) % 360) - 180  # Convert to [-180, 180]

        return normalized_angle, None

    except Exception as e:
        logger.error("E2025")
        return None, "E2025"
