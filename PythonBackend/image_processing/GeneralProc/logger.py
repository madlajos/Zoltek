import os
import logging

# Resolve path to project root or any consistent directory
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))  # directory where logger.py is
LOG_FILE = os.path.join(ROOT_DIR, "ImageAnalysis.log")  # force log to save near logger.py

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode='a'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
