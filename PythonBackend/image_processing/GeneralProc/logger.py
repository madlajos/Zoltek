import logging

# Configure logging
LOG_FILE = "ImageAnalysis.log"  # Change this to your preferred log filename

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode='a'),  # Append logs to file
        logging.StreamHandler()  # Still show logs in console
    ]
)

logger = logging.getLogger(__name__)
