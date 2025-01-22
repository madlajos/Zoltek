import threading
from flask import Flask
turntable_position = 0

app = Flask(__name__)

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
