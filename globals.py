# globals.py
from flask import Flask
import threading

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
