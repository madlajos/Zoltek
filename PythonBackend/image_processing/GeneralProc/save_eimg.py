import os
import cv2
from datetime import datetime

def save_image(image, filename="saved_error_image", ext=".jpg", timestamp=True, error_code=None):
    """
    Saves an image to a single shared 'error/' folder, with optional error-code-based filename.

    Args:
        image (np.ndarray): Image to save (grayscale or BGR).
        filename (str): Base filename (default: "saved_error_image").
        ext (str): File extension (".png", ".jpg", etc.).
        timestamp (bool): Whether to append a timestamp.
        error_code (str): Optional error code to use in filename (e.g., "E20").

    Returns:
        str or None: Path to saved image if successful, None otherwise.
    """
    try:
        if image is None or image.size == 0:
            print("Image is empty or invalid. Cannot save.")
            return None

        save_dir = "Error"
        os.makedirs(save_dir, exist_ok=True)

        # Use error code in filename if provided
        if error_code:
            filename = f"error_{error_code}"

        # Append timestamp
        if timestamp:
            time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{filename}_{time_str}"

        full_path = os.path.join(save_dir, filename + ext)

        if not cv2.imwrite(full_path, image):
            print("Failed to save image.")
            return None

        print(f"Image saved to: {full_path}")
        return None

    except Exception as e:
        print(f"Error saving image: {e}")
        return None
