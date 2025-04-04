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

# Image Analysis Results
x_end = 2814
dot_id_counter = 1  # Used for stable IDs, incremented each time we add a dot
measurement_data = []  # Will store [dot_id, x, y, col, area]
locked_class1_count = 0  # Once a dot is deemed class 1, or missing, it’s locked in
result_counts = [0,0,0]  # optional, if you want to store the last result
dot_results = []

last_blob_counts = {
    "center_circle": 0,
    "center_slice": 0,
    "outer_slice": 0
}

latest_image = None

size_limits = {
    "class1": 0,
    "class2": 0
}