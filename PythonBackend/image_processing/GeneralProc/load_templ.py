import os
from GeneralProc.handle_exc import template_check

def load_template(template_name, error_prefix):
    """Load the template image dynamically and validate."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, ".."))
    template_folder = os.path.join(project_root, "Templates")  # Ensure correct folder name
    template_path = os.path.join(template_folder, template_name)
    is_ok, emsg = template_check(template_path, error_prefix)
    return is_ok, emsg