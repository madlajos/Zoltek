import json
import os

class ErrorCode:
    TURNTABLE_NOT_FOUND = "E1201"
    TURNTABLE_UNRESPONSIVE = "E1202"
    TURNTABLE_CONNECTION_FAILED = "E1203"
    BARCODE_DISCONNECTED = "E2001"
    GENERIC = "GENERIC"

def load_error_messages():
    file_path = os.path.join(os.path.dirname(__file__), "error_messages.json")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

ERROR_MESSAGES = load_error_messages()