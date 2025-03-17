import json
import os

class ErrorCode:
    TURNTABLE_DISCONNECTED = "E1201"
    BARCODE_DISCONNECTED = "E1301"
    GENERIC = "GENERIC"

def load_error_messages():
    file_path = os.path.join(os.path.dirname(__file__), "error_messages.json")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

ERROR_MESSAGES = load_error_messages()