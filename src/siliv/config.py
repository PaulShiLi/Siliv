# src/siliv/config.py
# Configuration constants for the Siliv application.

from PyQt6.QtGui import QColor

# --- Configuration ---
RESERVED_SYSTEM_RAM_MIN = 4096 # Minimum RAM (MB) to reserve for the system

# --- Color Constants ---
RESERVED_RAM_COLOR = QColor("#3B82F6") # Blue-ish for reserved RAM bar segment
VRAM_COLOR = QColor("#22C55E")         # Green-ish for VRAM bar segment
FADED_VRAM_COLOR = QColor(VRAM_COLOR.red(), VRAM_COLOR.green(), VRAM_COLOR.blue(), 100) # Faded VRAM for bar transitions
TEXT_COLOR_DIM = "#888888"             # Dim text color for labels

# --- Slider Configuration ---
SLIDER_MIN_MB = 1024           # Minimum VRAM the slider can select (1GB)
SLIDER_TICK_INTERVAL_MB = 5120 # Tick interval for slider (5GB)
SLIDER_SINGLE_STEP_MB = 1024   # Single step for slider (1GB)

# --- Refresh Rate ---
REFRESH_INTERVAL_MS = 30000 # 30 seconds