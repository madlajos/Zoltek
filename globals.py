import threading
from flask import Flask
turntable_position = "?"
turntable_homed = False 
latest_barcode = ""

app = Flask(__name__)

barcode_scanner = None

cameras = {
    'main': None,
    'side': None
}

stream_running = {
    'main': False,
    'side': False
}

stream_threads = {
    'main': None,
    'side': None
}

grab_locks = {
    'main': threading.Lock(),
    'side': threading.Lock()
}

measurement_data = []
result_counts = [0, 0, 0]

# Image Analysis Results
x_end = 0
total_last_column_area = []
last_column_idx = 0