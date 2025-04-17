# src/siliv/app.py
# Manages the menu bar icon and VRAM logic using PyQt6.

import platform
import math # Needed for rounding/snapping

# PyQt6 Imports
from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QMessageBox,
    QWidgetAction
)
from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSignal
from PyQt6.QtGui import QIcon, QCursor, QAction

# Local Imports
from . import config
from . import utils
from .ui import widgets # Import the widgets module

class MenuBarApp(QObject):
    def __init__(self, icon_path, parent=None):
        super().__init__(parent)
        # --- State Variables ---
        self.total_ram_mb = 0
        self.current_vram_mb = 0
        self.reserved_ram_mb = 0
        self.target_vram_mb = 0 # Represents the value the slider/user wants
        self.macos_major_version = 0
        self.vram_key = None
        self.min_vram_mb = config.SLIDER_MIN_MB
        self.max_vram_mb = config.SLIDER_MIN_MB # Will be calculated
        self.is_operational = False # Can the app perform VRAM actions?
        self.preset_list_cache = []

        # --- UI Widget/Action References ---
        self.app_name_action = None
        self.ram_alloc_title_action = None
        self.ram_vram_bar_widget = None # Will be widgets.RamVramBarWidget
        self.ram_vram_bar_widget_action = None
        self.total_ram_info_action = None
        self.reserved_ram_info_action = None
        self.allocated_vram_info_action = None
        self.default_action = None
        self.presets_menu = None
        self.preset_actions = {}
        self.custom_vram_title_action = None
        self.slider_widget = None # Will be widgets.SliderWidget
        self.slider_widget_action = None
        self.slider_value_action = None # The "Apply X GB" action
        self.refresh_action = None
        self.quit_action = None

        # --- Application Setup ---
        self.app = QApplication.instance()

        self.is_operational = self.perform_initial_checks()
        if not self.is_operational:
            print("App is not operational due to failed initial checks.")
            # Error message already shown in perform_initial_checks via _show_error

        if self.is_operational:
            self.update_ram_values()
            self.target_vram_mb = self.current_vram_mb # Start with target = current
            self.calculate_slider_range()
            self.preset_list_cache = self.generate_presets_gb()

        # --- Tray Icon ---
        self.tray_icon = QSystemTrayIcon(QIcon(icon_path) if icon_path else QIcon(), self.app)
        self.tray_icon.setToolTip("Siliv VRAM Tool")
        self.tray_icon.activated.connect(self.handle_tray_activation)

        # --- Menu ---
        self.menu = QMenu()
        self.create_menu_actions() # Creates actions and connects signals

        # Show Tray Icon only if initialization was somewhat successful
        if self.total_ram_mb > 0: # Basic check if we got RAM info
            self.tray_icon.show()
            print("[App] Tray icon created and shown.")
        else:
            print("[App] Tray icon not shown due to critical initialization failure.")
            # Consider exiting if it's completely unusable:
            # self.quit_app()
            # return

        self.update_menu_items() # Set initial UI state

        # --- Refresh Timer ---
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._refresh_data_and_update_menu)
        self.refresh_timer.start(config.REFRESH_INTERVAL_MS)

    # --- Methods for setup, checks, calculations ---

    def perform_initial_checks(self):
        """Checks OS compatibility, retrieves RAM, and finds VRAM key."""
        print("Performing initial checks...")
        if platform.system() != "Darwin":
            self._show_error("Compatibility Error", "Siliv requires macOS.")
            return False

        self.macos_major_version = utils.get_macos_version()
        if self.macos_major_version == 0:
            self._show_error("Error", "Could not determine macOS version.")
            return False
        print(f"Detected macOS Version: {self.macos_major_version}")

        self.vram_key = utils.get_vram_sysctl_key()
        if self.vram_key is None:
            # Show warning but allow app to continue in limited mode
            self._show_warning("Unsupported OS", f"macOS {self.macos_major_version} might not support VRAM control with this tool.\nFunctionality will be limited.")
            # Don't return False here, allow it to run read-only
        else:
             print(f"Using VRAM sysctl key: '{self.vram_key}'")

        self.total_ram_mb = utils.get_total_ram_mb()
        if not self.total_ram_mb or self.total_ram_mb <= 0:
            self._show_error("Error", "Could not retrieve total system RAM.")
            return False # This is critical, cannot proceed
        print(f"Total System RAM: {self.total_ram_mb} MB")

        print("Initial checks passed.")
        # Operational means we can *try* to set VRAM
        return self.vram_key is not None

    def calculate_slider_range(self):
        """Calculates the min/max allowable VRAM values for the slider."""
        if not self.total_ram_mb: return

        # Min VRAM from config
        self.min_vram_mb = config.SLIDER_MIN_MB
        # Max VRAM is total RAM minus the minimum system reserve
        self.max_vram_mb = self.total_ram_mb - config.RESERVED_SYSTEM_RAM_MIN

        # Ensure max is not less than min, adjust if necessary (low RAM systems)
        if self.max_vram_mb < self.min_vram_mb:
            # Fallback: allow setting up to total RAM minus 1GB if reserve is too high
            self.max_vram_mb = max(self.min_vram_mb, self.total_ram_mb - 1024)
            print(f"Warning: Low total RAM ({self.total_ram_mb}MB) relative to reserve ({config.RESERVED_SYSTEM_RAM_MIN}MB). Adjusted max VRAM to {self.max_vram_mb}MB.")

        print(f"VRAM Setting Range Calculated: Min={self.min_vram_mb}MB, Max={self.max_vram_mb}MB")

    def generate_presets_gb(self):
        """Generates a list of sensible VRAM presets in GB tuples (GB, Label)."""
        presets = []
        if not self.total_ram_mb or self.max_vram_mb <= self.min_vram_mb: return []

        max_preset_mb = self.max_vram_mb
        # Use the utility function to get the calculated default
        calculated_default_mb = utils.calculate_default_vram_mb(self.total_ram_mb)

        # Define potential preset points in GB and corresponding labels
        # Adjust these based on typical use cases or user feedback
        potential_gbs = [4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128]
        labels = ["Basic", "Balanced", "More", "Gaming", "High", "Very High", "Extreme", "Insane"]
        label_idx = 0

        # Add presets that fall within the calculated min/max range
        for gb in potential_gbs:
            mb = gb * 1024
            # Check if within valid range and significantly different from default
            if self.min_vram_mb <= mb <= max_preset_mb:
                # Only add if it's not too close to the calculated default (e.g., > 1GB away)
                if abs(mb - calculated_default_mb) > 1024:
                    # Avoid duplicate GB values if potential_gbs has repeats
                    if not any(p[0] == gb for p in presets):
                         # Assign labels sequentially
                         label = labels[label_idx] if label_idx < len(labels) else f"{gb}GB" # Fallback label
                         presets.append((gb, label))
                         label_idx += 1

        # Consider adding the calculated maximum allocatable VRAM as a preset
        max_alloc_gb = int(max_preset_mb / 1024)
        # Check if max is valid, different from default, and not already added
        if max_alloc_gb * 1024 >= self.min_vram_mb and abs(max_alloc_gb * 1024 - calculated_default_mb) > 1024:
             if not any(p[0] == max_alloc_gb for p in presets):
                 # Use the next available label or "Max"
                 label = labels[min(label_idx, len(labels)-1)] if label_idx < len(labels) else "Max"
                 presets.append((max_alloc_gb, label))

        # Sort presets by GB value
        presets.sort(key=lambda x: x[0])
        print(f"Generated Presets: {presets}")
        return presets


    def create_menu_actions(self):
        """Creates and adds actions and widgets to the menu."""
        self.menu.clear()
        self.preset_actions.clear() # Clear previous preset actions

        # --- App Title ---
        self.app_name_action = QAction("Siliv VRAM Tool")
        font = self.app_name_action.font(); font.setBold(True); self.app_name_action.setFont(font)
        self.app_name_action.setEnabled(False) # Non-interactive title
        self.menu.addAction(self.app_name_action)
        self.menu.addSeparator()

        # --- RAM Allocation Info Section ---
        self.ram_alloc_title_action = QAction("RAM Allocation:")
        self.ram_alloc_title_action.setEnabled(False)
        self.menu.addAction(self.ram_alloc_title_action)

        # Bar Widget (from ui.widgets)
        self.ram_vram_bar_widget = widgets.RamVramBarWidget()
        self.ram_vram_bar_widget_action = QWidgetAction(self.menu)
        self.ram_vram_bar_widget_action.setDefaultWidget(self.ram_vram_bar_widget)
        # self.ram_vram_bar_widget_action.setEnabled(False) # Widget itself isn't interactive
        self.menu.addAction(self.ram_vram_bar_widget_action)

        # Info Text Actions
        self.total_ram_info_action = QAction("Total System RAM: ...")
        self.total_ram_info_action.setEnabled(False)
        self.menu.addAction(self.total_ram_info_action)
        self.reserved_ram_info_action = QAction("Reserved System RAM: ...")
        self.reserved_ram_info_action.setEnabled(False)
        self.menu.addAction(self.reserved_ram_info_action)
        self.allocated_vram_info_action = QAction("Allocated VRAM: ...")
        self.allocated_vram_info_action.setEnabled(False)
        self.menu.addAction(self.allocated_vram_info_action)
        self.menu.addSeparator()

        # --- Control Actions ---
        # Default VRAM Action
        self.default_action = QAction("Allocate Default VRAM")
        self.default_action.triggered.connect(self.set_default_vram)
        self.default_action.setEnabled(self.is_operational) # Enable only if we can set VRAM
        self.menu.addAction(self.default_action)

        # Presets Submenu
        self.presets_menu = self.menu.addMenu("Presets")
        self.presets_menu.setEnabled(self.is_operational and bool(self.preset_list_cache)) # Enable if operational and presets exist
        if not self.preset_list_cache:
            no_presets_action = QAction("No presets available")
            no_presets_action.setEnabled(False)
            self.presets_menu.addAction(no_presets_action)
        else:
            for gb, label_suffix in self.preset_list_cache:
                mb = gb * 1024
                action = QAction(f"Allocate {gb} GB VRAM ({label_suffix})")
                # Use lambda to capture the correct mb value for each action
                action.triggered.connect(lambda checked=False, m=mb: self.set_preset_vram(m))
                action.setEnabled(self.is_operational) # Presets only work if operational
                self.presets_menu.addAction(action)
                self.preset_actions[mb] = action # Store action reference

        self.menu.addSeparator()

        # --- Custom Allocation Section ---
        self.custom_vram_title_action = QAction("Custom VRAM Allocation:")
        self.custom_vram_title_action.setEnabled(False)
        self.menu.addAction(self.custom_vram_title_action)

        # Slider Widget Action (from ui.widgets)
        # Initialize slider with calculated range, default to min value initially
        self.slider_widget = widgets.SliderWidget(min_val=self.min_vram_mb, max_val=self.max_vram_mb)
        self.slider_widget.setObjectName("SliderWidget") # For potential styling
        self.slider_widget.setEnabled(self.is_operational) # Enable slider only if operational

        # Connect signals:
        # valueChanged updates the *target* VRAM state internally
        self.slider_widget.valueChanged.connect(self.handle_slider_value_changed)
        # sliderReleased handles snapping and updates the UI to the *final* target value
        self.slider_widget.sliderReleased.connect(self.handle_slider_snap_applied)

        self.slider_widget_action = QWidgetAction(self.menu)
        self.slider_widget_action.setDefaultWidget(self.slider_widget)
        self.menu.addAction(self.slider_widget_action)

        # Clickable Text Action to Apply Slider Value
        self.slider_value_action = QAction("Allocate ... GB VRAM")
        self.slider_value_action.setEnabled(False) # Initially disabled until slider moves
        self.slider_value_action.triggered.connect(self.apply_slider_value_from_action)
        self.menu.addAction(self.slider_value_action)
        self.menu.addSeparator()

        # --- Other Actions ---
        self.refresh_action = QAction("Refresh Info")
        self.refresh_action.triggered.connect(self._refresh_data_and_update_menu)
        # Enable refresh even if not operational, to re-check values
        self.refresh_action.setEnabled(True)
        self.menu.addAction(self.refresh_action)

        self.menu.addSeparator()
        self.quit_action = QAction("Quit Siliv")
        self.quit_action.triggered.connect(self.quit_app)
        self.menu.addAction(self.quit_action)

    def update_ram_values(self):
        """Fetches current VRAM using utils, recalculates reserved RAM. Returns True if VRAM changed."""
        # No need to check is_operational here, getting info should always work if RAM was read initially
        if self.total_ram_mb <= 0: return False # Can't proceed without total RAM

        old_vram = self.current_vram_mb
        # Use the utility function to get current VRAM
        self.current_vram_mb = utils.get_current_vram_mb(self.total_ram_mb)

        # Basic sanity check: VRAM cannot exceed Total RAM
        if self.current_vram_mb > self.total_ram_mb:
            print(f"Warning: Reported current VRAM ({self.current_vram_mb}MB) exceeds total RAM ({self.total_ram_mb}MB). Clamping to total RAM.")
            self.current_vram_mb = self.total_ram_mb

        # Calculate reserved RAM based on *current* VRAM
        self.reserved_ram_mb = self.total_ram_mb - self.current_vram_mb
        if self.reserved_ram_mb < 0: self.reserved_ram_mb = 0 # Cannot be negative

        vram_changed = (self.current_vram_mb != old_vram)
        if vram_changed:
            print(f"Current VRAM updated: {old_vram}MB -> {self.current_vram_mb}MB")

        return vram_changed

    def update_menu_items(self):
        """Updates the text and enabled state of all menu items based on current state."""
        if self.total_ram_mb <= 0: # If initial RAM check failed, disable most things
            print("Cannot update menu items: Total RAM unknown.")
            # Optionally disable all actions if needed
            return

        # --- Update RAM Allocation Section ---
        if self.ram_vram_bar_widget:
            # Bar shows current vs target
            self.ram_vram_bar_widget.update_values(self.total_ram_mb, self.current_vram_mb, self.target_vram_mb)

        total_ram_gb = self.total_ram_mb / 1024.0
        # Display *current* allocation values in the text labels
        current_vram_gb = self.current_vram_mb / 1024.0
        current_reserved_ram_gb = (self.total_ram_mb - self.current_vram_mb) / 1024.0

        self.total_ram_info_action.setText(f"Total System RAM: {total_ram_gb:.1f} GB")
        self.reserved_ram_info_action.setText(f"Reserved System RAM: {current_reserved_ram_gb:.1f} GB")
        self.allocated_vram_info_action.setText(f"Allocated VRAM: {current_vram_gb:.1f} GB ({self.current_vram_mb} MB)")

        # --- Update Control Actions ---
        calculated_default_mb = utils.calculate_default_vram_mb(self.total_ram_mb)
        is_current_default = (self.current_vram_mb == calculated_default_mb)

        # Default Action: Enable if operational AND current is not already default
        self.default_action.setEnabled(self.is_operational and not is_current_default)
        self.default_action.setText(f"Allocate Default VRAM{' (Current)' if is_current_default else ''}")

        # Preset Actions: Enable if operational AND current is not this preset
        self.presets_menu.setEnabled(self.is_operational and bool(self.preset_actions))
        for mb_key, action in self.preset_actions.items():
            is_current_preset = (self.current_vram_mb == mb_key)
            action.setEnabled(self.is_operational and not is_current_preset)
            # Remove "(Current)" before adding it back if needed
            original_text = action.text().split(" (Current)")[0]
            action.setText(f"{original_text}{' (Current)' if is_current_preset else ''}")

        # --- Update Custom Allocation Section ---
        if self.slider_widget:
             self.slider_widget.setEnabled(self.is_operational)
             if self.is_operational:
                 # Ensure slider range is correct (in case total RAM changes?)
                 # self.slider_widget.set_range(self.min_vram_mb, self.max_vram_mb) # Usually not needed unless RAM changes
                 # Set slider position based on the *target* value
                 self.slider_widget.set_value(self.target_vram_mb)

        # Apply Button (Slider Value Action): Enable if operational AND target differs from current
        if self.slider_value_action:
            target_gb = self.target_vram_mb / 1024.0 # Uses target_vram_mb
            self.slider_value_action.setText(f"Allocate {target_gb:.1f} GB VRAM")
            can_apply_slider = (self.target_vram_mb != self.current_vram_mb)
            self.slider_value_action.setEnabled(self.is_operational and can_apply_slider)

        # Refresh action is always enabled (as set in create_menu_actions)

    def _refresh_data_and_update_menu(self):
        """Refreshes RAM values and updates the menu display. Resets target to current."""
        print("[App] Refresh triggered...")
        vram_changed = self.update_ram_values()
        # When refreshing manually, reset the target to match the actual current state
        self.target_vram_mb = self.current_vram_mb
        self.update_menu_items() # Update UI based on new current values and reset target
        if vram_changed:
             print("VRAM value changed since last check.")
             # Optionally notify user if value changed externally?
             # self._show_message("VRAM Changed", f"System VRAM setting updated to {self.current_vram_mb} MB.")


    def handle_slider_value_changed(self, value_mb):
        """Updates ONLY the internal target VRAM state when slider moves (before release/snap)."""
        # Only update the internal target value. UI updates happen on snap/release.
        self.target_vram_mb = value_mb
        # print(f"Slider value changed (intermediate): target_vram_mb set to {self.target_vram_mb}") # Debug


    def handle_slider_snap_applied(self):
        """Called AFTER slider release and snapping logic. Updates UI to final snapped value."""
        print("[App] Slider snap applied (or release handled). Updating UI to final target.")
        # Snapping logic in SliderWidget already called slider.setValue()
        # which should have emitted valueChanged, updating self.target_vram_mb
        # Get the final value from the slider widget itself after snapping
        final_snapped_value = self.slider_widget.get_value()

        # Ensure internal target matches the final slider value
        if final_snapped_value != self.target_vram_mb:
             print(f"Aligning internal target ({self.target_vram_mb}) with final slider value ({final_snapped_value}) after snap.")
             self.target_vram_mb = final_snapped_value

        # Now, update the UI elements that depend on the final target value
        self.update_menu_items()


    def apply_slider_value_from_action(self):
        """Applies the VRAM value currently targeted by the slider via the text action."""
        target_mb_to_apply = self.target_vram_mb
        print(f"Applying slider target value via text action: {target_mb_to_apply} MB")
        if target_mb_to_apply != self.current_vram_mb:
            self._set_vram_and_update(target_mb_to_apply)
        else:
            print("Target value matches current VRAM, no change needed.")
            self._show_message("Info", "Selected VRAM matches current setting.")


    def _set_vram_and_update(self, value_mb):
        """Internal helper to attempt setting VRAM using utils.set_vram_mb and refresh menu."""
        if not self.is_operational:
            self._show_error("Error", "Cannot set VRAM: Application is not operational (check macOS version or permissions).")
            return

        target_mb = int(value_mb)
        # Clamp the requested value (unless it's 0 for default) before sending to set_vram_mb
        if target_mb != 0: # 0 means "set to default" and shouldn't be clamped by us
             clamped_mb = max(self.min_vram_mb, min(target_mb, self.max_vram_mb))
             if clamped_mb != target_mb:
                 print(f"Requested VRAM {target_mb}MB clamped to range [{self.min_vram_mb}-{self.max_vram_mb}]: {clamped_mb}MB")
                 target_mb = clamped_mb
        else:
            print("Requesting reset to system default VRAM (passing 0 to sysctl).")

        print(f"Calling utils.set_vram_mb with target: {target_mb}")
        # Use the utility function to set VRAM
        success, message = utils.set_vram_mb(target_mb)

        if success:
            print("VRAM set command reported success via utils. Refreshing menu shortly...")
            # Schedule a refresh after a short delay to allow the system value to update
            QTimer.singleShot(1500, self._refresh_data_and_update_menu)
        else:
            # Error/Warning should have been shown by utils.set_vram_mb if it failed
            print(f"Failed to set VRAM or action cancelled. Message from utils: {message}")
            # If setting failed, refresh UI immediately and reset target to current
            self.target_vram_mb = self.current_vram_mb
            self.update_menu_items()


    # --- Tray Icon Interaction ---
    def handle_tray_activation(self, reason):
        """Shows the menu when the tray icon is clicked (Trigger or Context)."""
        # Show menu on left click (Trigger) or right click (Context)
        if reason == QSystemTrayIcon.ActivationReason.Trigger or reason == QSystemTrayIcon.ActivationReason.Context:
            print(f"[App] Tray icon activated (Reason: {reason}), showing menu.")
            # Refresh current values *before* showing the menu
            self.update_ram_values()
            # Reset target to current when menu is opened
            self.target_vram_mb = self.current_vram_mb
            # Update all menu item states based on refreshed data
            self.update_menu_items()
            # Position and show the menu
            self.menu.popup(QCursor.pos())


    # --- Slot Methods for Actions ---
    def set_default_vram(self):
        """Sets VRAM to the system default (by setting the key to 0)."""
        print(f"[App] User requested setting VRAM to System Default.")
        calculated_default_mb = utils.calculate_default_vram_mb(self.total_ram_mb)
        # Update target immediately for UI feedback before applying
        self.target_vram_mb = calculated_default_mb
        self.update_menu_items()
        # Trigger the actual setting process (which passes 0 to the utility)
        self._set_vram_and_update(0)

    def set_preset_vram(self, value_mb):
        """Sets VRAM to a specific preset value."""
        print(f"[App] User requested setting VRAM to Preset: {value_mb} MB")
        # Update target immediately for UI feedback
        self.target_vram_mb = value_mb
        self.update_menu_items()
        # Trigger the actual setting process
        self._set_vram_and_update(value_mb)

    # --- Utility Methods for User Feedback (remain in App class) ---
    def _show_message(self, title, message):
        """Shows an informational message via the system tray."""
        if self.tray_icon.isVisible():
            self.tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 3000)
        else:
            print(f"INFO [{title}]: {message}") # Fallback if tray not visible

    def _show_warning(self, title, message):
        """Shows a warning message dialog."""
        # No parent needed for a simple warning dialog
        QMessageBox.warning(None, title, message)

    def _show_error(self, title, message):
        """Shows a critical error message dialog."""
        # No parent needed for a simple error dialog
        QMessageBox.critical(None, title, message)

    # --- Application Exit ---
    def quit_app(self):
        """Stops timers, hides tray icon, and quits the application."""
        print("[App] Quitting application...")
        self.refresh_timer.stop()
        self.tray_icon.hide() # Hide icon before quitting
        # Disconnect signals? (Usually not necessary if app is quitting)
        self.app.quit()