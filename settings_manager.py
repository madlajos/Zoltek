import json
import os
import threading
import logging

DEFAULT_SETTINGS_PATH = os.path.join(os.path.dirname(__file__), 'settings.json')

# In case multiple threads read/write settings at once:
_settings_lock = threading.Lock()

# This variable will hold our settings after we load from JSON
_cached_settings = {}

def load_settings(settings_path=DEFAULT_SETTINGS_PATH):
    global _cached_settings
    with _settings_lock:
        try:
            with open(settings_path, 'r') as file:
                _cached_settings = json.load(file)
            logging.info(f"Settings loaded from {settings_path}")
        except FileNotFoundError:
            logging.error(f"Settings file not found at {settings_path}")
            _cached_settings = {}
        except json.JSONDecodeError:
            logging.error("Invalid JSON format in settings file.")
            _cached_settings = {}
        except Exception as e:
            logging.error(f"Failed to load settings: {e}")
            _cached_settings = {}

    return _cached_settings

def save_settings(settings_path=DEFAULT_SETTINGS_PATH):
    global _cached_settings
    with _settings_lock:
        try:
            with open(settings_path, 'w') as file:
                json.dump(_cached_settings, file, indent=4)
            logging.info("Settings saved successfully.")
        except Exception as e:
            logging.error(f"Failed to save settings: {e}")

def get_settings() -> dict:
    """
    Returns the current in-memory settings dict.
    Make sure to call load_settings() at least once on startup.
    """
    # We do NOT do any locking here because the caller might already hold the lock,
    # but if you prefer, you can do so.
    return _cached_settings

def set_settings(new_settings: dict):
    """
    Replaces the entire settings dictionary in memory.
    """
    global _cached_settings
    with _settings_lock:
        _cached_settings = new_settings
