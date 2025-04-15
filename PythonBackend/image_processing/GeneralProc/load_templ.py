import os
import sys
from GeneralProc.handle_exc import template_check

def load_template(template_name, error_prefix):
    """Load the template image dynamically and validate."""
    try:
        # Get path to the current file (even inside a PyInstaller .exe)
        if getattr(sys, 'frozen', False):
            # Running as bundled .exe
            script_dir = sys._MEIPASS  # PyInstaller's temp directory
        else:
            # Running as .py
            script_dir = os.path.dirname(os.path.abspath(__file__))
            
        template_folder = os.path.join(script_dir, "Templates")
        template_path = os.path.join(template_folder, template_name)

        is_ok, emsg = template_check(template_path, error_prefix)
        return is_ok, emsg
    except Exception as e:
        return None, f"{error_prefix}: Failed to load template - {str(e)}"