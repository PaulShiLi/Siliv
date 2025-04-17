# src/siliv/ui/widgets.py
# Custom PyQt6 widgets for the Siliv application UI.

import math
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QFrame, QSizePolicy, QMessageBox # Import QMessageBox here if needed, but better in app.py
)
from PyQt6.QtCore import Qt, pyqtSignal, QRectF
from PyQt6.QtGui import QPainter, QBrush, QColor, QPainterPath, QPen

# Import config for colors and constants
from siliv import config

# --- Custom Widget for RAM/VRAM Bar ---
# BarDisplayWidget remains unchanged...
class BarDisplayWidget(QWidget):
    """Widget responsible for drawing the RAM/VRAM bar, showing difference."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.total_mb = 1
        self.current_vram_mb = 0
        self.target_vram_mb = 0
        self.bar_height = 14
        self.setMinimumHeight(self.bar_height)
        self.setMaximumHeight(self.bar_height)

    def set_values(self, total_mb, current_vram_mb, target_vram_mb):
        self.total_mb = max(1, total_mb)
        self.current_vram_mb = max(0, min(current_vram_mb, self.total_mb))
        self.target_vram_mb = max(0, min(target_vram_mb, self.total_mb))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        total_width = float(self.width())
        bar_height = float(self.height())
        radius = bar_height / 2.0
        if self.total_mb <= 0 or total_width <= 0:
            painter.end()
            return
        path = QPainterPath()
        path.addRoundedRect(QRectF(0.0, 0.0, total_width, bar_height), radius, radius)
        painter.setClipPath(path)
        painter.setPen(Qt.PenStyle.NoPen)
        target_vram_pos = total_width * (self.target_vram_mb / self.total_mb)
        current_vram_pos = total_width * (self.current_vram_mb / self.total_mb)
        if self.target_vram_mb < self.current_vram_mb:
            diff_pos = current_vram_pos - target_vram_pos
            if target_vram_pos > 0:
                painter.fillRect(QRectF(0.0, 0.0, target_vram_pos, bar_height), config.VRAM_COLOR)
            if diff_pos > 0:
                painter.fillRect(QRectF(target_vram_pos, 0.0, diff_pos, bar_height), config.FADED_VRAM_COLOR)
            reserved_start_pos = current_vram_pos
            reserved_width = total_width - reserved_start_pos
            if reserved_width > 0:
                painter.fillRect(QRectF(reserved_start_pos, 0.0, reserved_width, bar_height), config.RESERVED_RAM_COLOR)
        else:
            reserved_start_pos = target_vram_pos
            reserved_width = total_width - reserved_start_pos
            if target_vram_pos > 0:
                painter.fillRect(QRectF(0.0, 0.0, target_vram_pos, bar_height), config.VRAM_COLOR)
            if reserved_width > 0:
                painter.fillRect(QRectF(reserved_start_pos, 0.0, reserved_width, bar_height), config.RESERVED_RAM_COLOR)
        painter.end()

# RamVramBarWidget remains unchanged...
class RamVramBarWidget(QWidget):
    """Widget combining the BarDisplayWidget and legend labels."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bar_display = BarDisplayWidget(self)
        self.reserved_label = QLabel("Reserved: --- GB")
        self.vram_label = QLabel("VRAM: --- GB")
        label_style = f"color: {config.TEXT_COLOR_DIM}; font-size: 10pt; background-color: transparent;"
        self.reserved_label.setStyleSheet(label_style)
        self.vram_label.setStyleSheet(label_style)
        legend_layout = QHBoxLayout()
        legend_layout.setContentsMargins(0, 2, 0, 0)
        legend_layout.setSpacing(10)
        legend_layout.addWidget(self.vram_label)
        legend_layout.addWidget(self.reserved_label)
        legend_layout.addStretch()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 5, 10, 5)
        main_layout.setSpacing(3)
        main_layout.addWidget(self.bar_display)
        main_layout.addLayout(legend_layout)
        self.setLayout(main_layout)
        self.setStyleSheet("RamVramBarWidget { background-color: transparent; }")

    def update_values(self, total_mb, current_vram_mb, target_vram_mb):
        self.bar_display.set_values(total_mb, current_vram_mb, target_vram_mb)
        # Calculate reserved based on TARGET vram for the labels
        target_reserved_mb = max(0, total_mb - target_vram_mb)
        target_reserved_gb = target_reserved_mb / 1024.0
        target_vram_gb = target_vram_mb / 1024.0
        self.reserved_label.setText(f"Reserved: {target_reserved_gb:.1f} GB")
        self.vram_label.setText(f"VRAM: {target_vram_gb:.1f} GB")


# --- Slider Widget with Mapped Ticks ---
class SliderWidget(QWidget):
    """
    A widget containing a slider where tick positions (1 to N) are mapped
    to specific VRAM values (1GB, 5GB, 10GB, ..., MaxGB).
    """
    valueChanged = pyqtSignal(int)
    sliderReleased = pyqtSignal()

    def __init__(self, min_val=config.SLIDER_MIN_MB, max_val=4096, parent=None):
        super().__init__(parent)
        self._actual_min_mb = min_val
        self._actual_max_mb = max_val # Will be updated by set_range if needed
        self._num_ticks = 1
        self._tick_to_mb_map = {}
        self._mb_to_tick_map = {}

        layout = QHBoxLayout()
        layout.setContentsMargins(10, 3, 10, 3)
        layout.setSpacing(0)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setObjectName("MenuSlider")
        self.slider.setSingleStep(1)
        self.slider.setPageStep(1)
        self.slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider.setTickInterval(1)

        # Set initial range using the provided (potentially updated) max_val
        self.set_range(self._actual_min_mb, self._actual_max_mb)

        self.slider.valueChanged.connect(self._handle_internal_value_change)
        self.slider.sliderReleased.connect(self.sliderReleased.emit)

        layout.addWidget(self.slider)
        self.setLayout(layout)

    def _generate_mapping(self, min_mb, max_mb):
        """Generates the mapping between tick indices (1..N) and MB values."""
        self._tick_to_mb_map.clear()
        self._mb_to_tick_map.clear()
        points_mb = []

        # Tick 1: Usually 1GB (config.SLIDER_MIN_MB)
        tick_1_mb = config.SLIDER_MIN_MB
        if tick_1_mb >= min_mb and tick_1_mb <= max_mb: # Ensure it's within the allowed range
            points_mb.append(tick_1_mb)
        elif min_mb <= max_mb: # If 1GB is outside range, start with min_mb
             points_mb.append(min_mb)


        # Ticks 2 to N-1: 5GB multiples
        five_gb_interval = 5 * 1024
        # Start checking from the first 5GB multiple *after* the first point
        start_5gb = five_gb_interval * math.ceil( (points_mb[0] if points_mb else min_mb) / five_gb_interval)
        if start_5gb <= (points_mb[0] if points_mb else min_mb): # Adjust if first point is already a multiple
             start_5gb += five_gb_interval

        current_5gb_multiple = start_5gb
        while current_5gb_multiple < max_mb: # Use < max_mb to avoid duplicating max value later
            if current_5gb_multiple >= min_mb:
                 if not points_mb or current_5gb_multiple > points_mb[-1]:
                     points_mb.append(current_5gb_multiple)
            current_5gb_multiple += five_gb_interval

        # Tick N: Actual max value (if > last point added and >= min_mb)
        # Ensures the maximum possible value is always an option
        if max_mb >= min_mb:
             if not points_mb or max_mb > points_mb[-1]:
                 points_mb.append(max_mb)

        # Ensure points_mb is not empty if min/max were valid
        if not points_mb and min_mb <= max_mb:
             points_mb.append(min_mb) # Fallback

        # --- Create the maps ---
        self._num_ticks = len(points_mb)
        for i, mb_value in enumerate(points_mb):
            tick_index = i + 1
            self._tick_to_mb_map[tick_index] = mb_value
            if mb_value not in self._mb_to_tick_map:
                self._mb_to_tick_map[mb_value] = tick_index

        # print(f"Num Ticks (N): {self._num_ticks}")
        # print(f"Tick->MB Map: {self._tick_to_mb_map}")
        # print(f"MB->Tick Map: {self._mb_to_tick_map}")


    def _map_tick_to_mb(self, tick_index):
        """Maps a tick index (1 to N) to the corresponding VRAM MB value."""
        # Ensure tick_index is valid before lookup
        valid_tick_index = max(1, min(tick_index, self._num_ticks))
        # Use the valid index, default to min_mb if map somehow fails
        return self._tick_to_mb_map.get(valid_tick_index, self._actual_min_mb)


    def _map_mb_to_tick(self, mb_value):
        """Finds the tick index closest to the given VRAM MB value."""
        if not self._tick_to_mb_map: return 1

        closest_tick = 1
        # Handle case where only one tick exists
        if self._num_ticks == 1: return 1

        # Initialize min_diff with the difference to the first tick's value
        first_tick_val = self._tick_to_mb_map.get(1, self._actual_min_mb)
        min_diff = abs(mb_value - first_tick_val)

        for tick_index, mapped_mb in self._tick_to_mb_map.items():
            diff = abs(mb_value - mapped_mb)
            if diff < min_diff:
                min_diff = diff
                closest_tick = tick_index
            elif diff == min_diff: # Prefer lower tick on ties
                closest_tick = min(closest_tick, tick_index)

        return closest_tick

    def set_range(self, min_val, max_val):
        """
        Set the underlying VRAM min/max, regenerate mapping, and set slider range (1 to N).
        """
        # --- Ensure internal min/max are updated ---
        self._actual_min_mb = min_val
        self._actual_max_mb = max_val
        # ------------------------------------------

        self._generate_mapping(self._actual_min_mb, self._actual_max_mb)

        # Set slider range (1 to N ticks) only if ticks were generated
        if self._num_ticks > 0:
             self.slider.setMinimum(1)
             self.slider.setMaximum(self._num_ticks)
             # print(f"Slider range set: Min=1, Max={self._num_ticks}")
        else:
             # Handle edge case: no valid ticks generated (e.g., min > max)
             self.slider.setMinimum(1)
             self.slider.setMaximum(1)
             self.slider.setEnabled(False) # Disable slider if range is invalid
             print(f"Warning: Invalid VRAM range [{min_val}-{max_val}] resulted in 0 ticks. Disabling slider.")


    def set_value(self, value_mb):
        """
        Sets the slider position to the tick closest to the given VRAM MB value.
        """
        if not self.isEnabled() or self._num_ticks <= 0: return # Don't set if disabled or no ticks

        self.slider.blockSignals(True)
        tick_index = self._map_mb_to_tick(value_mb)
        # Clamp tick_index to the slider's actual range (1 to N)
        clamped_tick_index = max(self.slider.minimum(), min(tick_index, self.slider.maximum()))
        self.slider.setValue(clamped_tick_index)
        # print(f"Set MB {value_mb} -> Tick {clamped_tick_index}")
        self.slider.blockSignals(False)

    def get_value(self):
        """
        Get the VRAM MB value corresponding to the slider's current tick position.
        """
        if not self.isEnabled() or self._num_ticks <= 0: return self._actual_min_mb # Return min if disabled

        current_tick_index = self.slider.value()
        return self._map_tick_to_mb(current_tick_index)

    def _handle_internal_value_change(self, tick_index):
        """
        Handles the slider's internal valueChanged signal (which emits tick index).
        Maps the tick index to MB and emits the public valueChanged signal.
        """
        mapped_mb_value = self._map_tick_to_mb(tick_index)
        # print(f"Internal change: Tick {tick_index} -> MB {mapped_mb_value}")
        self.valueChanged.emit(mapped_mb_value) # Emit the MB value