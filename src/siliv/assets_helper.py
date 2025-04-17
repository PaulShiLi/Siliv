# src/siliv/assets_helper.py
# Helper function to locate application assets.

import os
import sys

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        # Adjust base path calculation if assets are bundled differently
        base_path = getattr(sys, '_MEIPASS', os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
    except Exception:
        # Fallback for safety, assuming script is run from project root in dev
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)