# src/siliv/app.py
# Manages the menu bar icon and VRAM logic using PyQt6.

import platform
import math # Needed for rounding/snapping

# PyQt6 Imports
from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QMessageBox,
    QWidgetAction
)
# Import QSettings
from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSignal, QSettings
from PyQt6.QtGui import QIcon, QCursor, QAction

# Local Imports
from siliv import config
from siliv import utils
from siliv.ui import widgets

# --- Settings Constants ---
ORGANIZATION_NAME = "Siliv.Project" # Or your preferred organization name
APPLICATION_NAME = "Siliv"
SAVED_VRAM_KEY = "user/savedVramMb"
# --------------------------

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
        self.is_operational = False
        self.preset_list_cache = []

        # --- UI Widget/Action References ---
        self.app_name_action = None
        self.ram_alloc_title_action = None
        self.ram_vram_bar_widget = None
        self.ram_vram_bar_widget_action = None
        self.total_ram_info_action = None
        self.reserved_ram_info_action = None
        self.allocated_vram_info_action = None
        self.default_action = None
        self.presets_menu = None
        self.preset_actions = {}
        self.custom_vram_title_action = None
        self.slider_widget = None
        self.slider_widget_action = None
        self.slider_value_action = None # The "Apply X GB" action
        self.refresh_action = None
        self.quit_action = None

        # --- Application Setup ---
        self.app = QApplication.instance()
        # --- Initialize QSettings ---
        self.settings = QSettings(ORGANIZATION_NAME, APPLICATION_NAME)
        # --------------------------

        self.is_operational = self.perform_initial_checks()
        if not self.is_operational:
            print("App is not operational due to failed initial checks.")

        # Fetch initial values *before* checking saved settings
        if self.total_ram_mb > 0: # Need total RAM to calculate things
             self.update_ram_values() # Fetches current VRAM
             self.target_vram_mb = self.current_vram_mb # Start with target = current
             self.calculate_slider_range()
             self.preset_list_cache = self.generate_presets_gb()
        else:
             # Handle critical failure case where RAM couldn't be determined
             print("[App Init] Critical: Could not determine total RAM. App state is limited.")
             # Set defaults to avoid errors later, though functionality is impaired
             self.current_vram_mb = 0
             self.target_vram_mb = 0
             self.min_vram_mb = config.SLIDER_MIN_MB
             self.max_vram_mb = config.SLIDER_MIN_MB

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

        self.update_menu_items() # Set initial UI state based on fetched/calculated values

        # --- Apply Saved VRAM on Startup ---
        # Moved here, after initial values are fetched and menu items created/updated once
        if self.total_ram_mb > 0:
            self.apply_saved_vram_on_startup()
        # ---------------------------------

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
            # Allow limited mode if we can still get RAM
            # return False
        else:
            print(f"Detected macOS Version: {self.macos_major_version}")

        self.vram_key = utils.get_vram_sysctl_key()
        can_set_vram = self.vram_key is not None

        self.total_ram_mb = utils.get_total_ram_mb()
        if not self.total_ram_mb or self.total_ram_mb <= 0:
            self._show_error("Error", "Could not retrieve total system RAM.\nApplication cannot function correctly.")
            return False # This is critical, cannot proceed

        print(f"Total System RAM: {self.total_ram_mb} MB")

        if not can_set_vram:
            # Show warning but allow app to continue in limited mode if RAM was read
            self._show_warning("Unsupported OS or Permissions", f"macOS {self.macos_major_version} might not support VRAM control with this tool, or permissions are insufficient.\nFunctionality will be limited to displaying information.")
            print(f"Using VRAM sysctl key: '{self.vram_key}' (or None)")
            return False # Mark as not fully operational if we can't set VRAM
        else:
             print(f"Using VRAM sysctl key: '{self.vram_key}'")
             print("Initial checks passed (VRAM control should be possible).")
             return True # Operational means we can try to set VRAM

    def calculate_slider_range(self):
        """Calculates the min/max allowable VRAM values for the slider."""
        if not self.total_ram_mb: return

        self.min_vram_mb = config.SLIDER_MIN_MB
        self.max_vram_mb = self.total_ram_mb - config.RESERVED_SYSTEM_RAM_MIN

        if self.max_vram_mb < self.min_vram_mb:
            self.max_vram_mb = max(self.min_vram_mb, self.total_ram_mb - 1024)
            print(f"Warning: Low total RAM ({self.total_ram_mb}MB) relative to reserve ({config.RESERVED_SYSTEM_RAM_MIN}MB). Adjusted max VRAM to {self.max_vram_mb}MB.")

        print(f"VRAM Setting Range Calculated: Min={self.min_vram_mb}MB, Max={self.max_vram_mb}MB")

    def generate_presets_gb(self):
        """Generates a list of sensible VRAM presets in GB tuples (GB, Label)."""
        presets = []
        if not self.total_ram_mb or self.max_vram_mb <= self.min_vram_mb: return []

        max_preset_mb = self.max_vram_mb
        calculated_default_mb = utils.calculate_default_vram_mb(self.total_ram_mb)

        potential_gbs = [4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128]
        labels = ["Basic", "Balanced", "More", "Gaming", "High", "Very High", "Extreme", "Insane"]
        label_idx = 0

        for gb in potential_gbs:
            mb = gb * 1024
            if self.min_vram_mb <= mb <= max_preset_mb:
                if abs(mb - calculated_default_mb) > 1024:
                    if not any(p[0] == gb for p in presets):
                         label = labels[label_idx] if label_idx < len(labels) else f"{gb}GB"
                         presets.append((gb, label))
                         label_idx += 1

        max_alloc_gb = int(max_preset_mb / 1024)
        if max_alloc_gb * 1024 >= self.min_vram_mb and abs(max_alloc_gb * 1024 - calculated_default_mb) > 1024:
             if not any(p[0] == max_alloc_gb for p in presets):
                 label = labels[min(label_idx, len(labels)-1)] if label_idx < len(labels) else "Max"
                 presets.append((max_alloc_gb, label))

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
        self.app_name_action.setEnabled(False)
        self.menu.addAction(self.app_name_action)
        self.menu.addSeparator()

        # --- RAM Allocation Info Section ---
        self.ram_alloc_title_action = QAction("RAM Allocation:")
        self.ram_alloc_title_action.setEnabled(False)
        self.menu.addAction(self.ram_alloc_title_action)

        self.ram_vram_bar_widget = widgets.RamVramBarWidget()
        self.ram_vram_bar_widget_action = QWidgetAction(self.menu)
        self.ram_vram_bar_widget_action.setDefaultWidget(self.ram_vram_bar_widget)
        self.menu.addAction(self.ram_vram_bar_widget_action)

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
        self.default_action = QAction("Allocate Default VRAM")
        self.default_action.triggered.connect(self.set_default_vram)
        self.default_action.setEnabled(self.is_operational)
        self.menu.addAction(self.default_action)

        self.presets_menu = self.menu.addMenu("Presets")
        self.presets_menu.setEnabled(self.is_operational and bool(self.preset_list_cache))
        if not self.preset_list_cache:
            no_presets_action = QAction("No presets available")
            no_presets_action.setEnabled(False)
            self.presets_menu.addAction(no_presets_action)
        else:
            for gb, label_suffix in self.preset_list_cache:
                mb = gb * 1024
                action = QAction(f"Allocate {gb} GB VRAM ({label_suffix})")
                action.triggered.connect(lambda checked=False, m=mb: self.set_preset_vram(m))
                action.setEnabled(self.is_operational)
                self.presets_menu.addAction(action)
                self.preset_actions[mb] = action

        self.menu.addSeparator()

        # --- Custom Allocation Section ---
        self.custom_vram_title_action = QAction("Custom VRAM Allocation:")
        self.custom_vram_title_action.setEnabled(False)
        self.menu.addAction(self.custom_vram_title_action)

        self.slider_widget = widgets.SliderWidget(min_val=self.min_vram_mb, max_val=self.max_vram_mb)
        self.slider_widget.setObjectName("SliderWidget")
        self.slider_widget.setEnabled(self.is_operational)

        self.slider_widget.valueChanged.connect(self.handle_slider_value_changed)
        self.slider_widget.sliderReleased.connect(self.handle_slider_snap_applied)

        self.slider_widget_action = QWidgetAction(self.menu)
        self.slider_widget_action.setDefaultWidget(self.slider_widget)
        self.menu.addAction(self.slider_widget_action)

        self.slider_value_action = QAction("Allocate ... GB VRAM")
        self.slider_value_action.setEnabled(False)
        self.slider_value_action.triggered.connect(self.apply_slider_value_from_action)
        self.menu.addAction(self.slider_value_action)
        self.menu.addSeparator()

        # --- Other Actions ---
        self.refresh_action = QAction("Refresh Info")
        self.refresh_action.triggered.connect(self._refresh_data_and_update_menu)
        self.refresh_action.setEnabled(True)
        self.menu.addAction(self.refresh_action)

        self.menu.addSeparator()
        self.quit_action = QAction("Quit Siliv")
        self.quit_action.triggered.connect(self.quit_app)
        self.menu.addAction(self.quit_action)

    def update_ram_values(self):
        """Fetches current VRAM using utils, recalculates reserved RAM. Returns True if VRAM changed."""
        if self.total_ram_mb <= 0: return False

        old_vram = self.current_vram_mb
        self.current_vram_mb = utils.get_current_vram_mb(self.total_ram_mb)

        if self.current_vram_mb > self.total_ram_mb:
            print(f"Warning: Reported current VRAM ({self.current_vram_mb}MB) exceeds total RAM ({self.total_ram_mb}MB). Clamping to total RAM.")
            self.current_vram_mb = self.total_ram_mb

        self.reserved_ram_mb = self.total_ram_mb - self.current_vram_mb
        if self.reserved_ram_mb < 0: self.reserved_ram_mb = 0

        vram_changed = (self.current_vram_mb != old_vram)
        if vram_changed:
            print(f"Current VRAM updated: {old_vram}MB -> {self.current_vram_mb}MB")

        return vram_changed

    def update_menu_items(self):
        """Updates the text and enabled state of all menu items based on current state."""
        if self.total_ram_mb <= 0:
            print("Cannot update menu items: Total RAM unknown.")
            # Disable most actions if RAM is unknown
            if self.default_action: self.default_action.setEnabled(False)
            if self.presets_menu: self.presets_menu.setEnabled(False)
            if self.slider_widget: self.slider_widget.setEnabled(False)
            if self.slider_value_action: self.slider_value_action.setEnabled(False)
            # Allow refresh and quit
            return

        # --- Update RAM Allocation Section ---
        if self.ram_vram_bar_widget:
            self.ram_vram_bar_widget.update_values(self.total_ram_mb, self.current_vram_mb, self.target_vram_mb)

        total_ram_gb = self.total_ram_mb / 1024.0
        current_vram_gb = self.current_vram_mb / 1024.0
        current_reserved_ram_gb = (self.total_ram_mb - self.current_vram_mb) / 1024.0

        if self.total_ram_info_action: self.total_ram_info_action.setText(f"Total System RAM: {total_ram_gb:.1f} GB")
        if self.reserved_ram_info_action: self.reserved_ram_info_action.setText(f"Reserved System RAM: {current_reserved_ram_gb:.1f} GB")
        if self.allocated_vram_info_action: self.allocated_vram_info_action.setText(f"Allocated VRAM: {current_vram_gb:.1f} GB ({self.current_vram_mb} MB)")

        # --- Update Control Actions ---
        calculated_default_mb = utils.calculate_default_vram_mb(self.total_ram_mb)
        is_current_default = (self.current_vram_mb == calculated_default_mb)

        if self.default_action:
            self.default_action.setEnabled(self.is_operational and not is_current_default)
            self.default_action.setText(f"Allocate Default VRAM{' (Current)' if is_current_default else ''}")

        if self.presets_menu:
            self.presets_menu.setEnabled(self.is_operational and bool(self.preset_actions))
            for mb_key, action in self.preset_actions.items():
                is_current_preset = (self.current_vram_mb == mb_key)
                action.setEnabled(self.is_operational and not is_current_preset)
                original_text = action.text().split(" (Current)")[0]
                action.setText(f"{original_text}{' (Current)' if is_current_preset else ''}")

        # --- Update Custom Allocation Section ---
        if self.slider_widget:
             self.slider_widget.setEnabled(self.is_operational)
             if self.is_operational:
                 # Set slider position based on the *target* value
                 self.slider_widget.set_value(self.target_vram_mb)

        if self.slider_value_action:
            target_gb = self.target_vram_mb / 1024.0
            self.slider_value_action.setText(f"Allocate {target_gb:.1f} GB VRAM")
            can_apply_slider = (self.target_vram_mb != self.current_vram_mb)
            self.slider_value_action.setEnabled(self.is_operational and can_apply_slider)


    def _refresh_data_and_update_menu(self):
        """Refreshes RAM values and updates the menu display. Does NOT reset target."""
        print("[App] Refresh triggered...")
        vram_changed = self.update_ram_values()
        # Keep target as is during auto-refresh, only reset when menu is opened
        self.update_menu_items() # Update UI based on new current values and existing target
        if vram_changed:
             print("VRAM value changed since last check.")


    def handle_slider_value_changed(self, value_mb):
        """Updates ONLY the internal target VRAM state when slider moves (before release/snap)."""
        self.target_vram_mb = value_mb
        # Update the 'Apply X GB' button text immediately as the slider moves
        if self.slider_value_action:
            target_gb = self.target_vram_mb / 1024.0
            self.slider_value_action.setText(f"Allocate {target_gb:.1f} GB VRAM")
            can_apply_slider = (self.target_vram_mb != self.current_vram_mb)
            self.slider_value_action.setEnabled(self.is_operational and can_apply_slider)
        # Also update the bar display immediately to show the target changing
        if self.ram_vram_bar_widget:
            self.ram_vram_bar_widget.update_values(self.total_ram_mb, self.current_vram_mb, self.target_vram_mb)


    def handle_slider_snap_applied(self):
        """Called AFTER slider release and snapping logic. Updates UI to final snapped value."""
        print("[App] Slider snap applied (or release handled). Updating UI to final target.")
        final_snapped_value = self.slider_widget.get_value()

        if final_snapped_value != self.target_vram_mb:
             print(f"Aligning internal target ({self.target_vram_mb}) with final slider value ({final_snapped_value}) after snap.")
             self.target_vram_mb = final_snapped_value

        # Update all menu items based on the final target value
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

        try:
            target_mb = int(value_mb)
        except (ValueError, TypeError):
             print(f"Error: Invalid value provided to _set_vram_and_update: {value_mb}")
             self._show_error("Error", f"Invalid VRAM value: {value_mb}")
             return

        clamped_mb = target_mb
        # Clamp the requested value (unless it's 0 for default) before sending to set_vram_mb
        if target_mb != 0:
             clamped_mb = max(self.min_vram_mb, min(target_mb, self.max_vram_mb))
             if clamped_mb != target_mb:
                 print(f"Requested VRAM {target_mb}MB clamped to range [{self.min_vram_mb}-{self.max_vram_mb}]: {clamped_mb}MB")
        else:
            print("Requesting reset to system default VRAM (passing 0 to sysctl).")
            # When resetting to default, the actual value will be calculated by the system.
            # We use the calculated default for immediate UI feedback, but save 0.
            calculated_default_mb = utils.calculate_default_vram_mb(self.total_ram_mb)
            self.target_vram_mb = calculated_default_mb # Update target for UI
            self.update_menu_items()


        print(f"Calling utils.set_vram_mb with target: {clamped_mb}")
        success, message = utils.set_vram_mb(clamped_mb) # Pass the clamped value

        if success:
            print(f"VRAM set command reported success via utils. Saving {clamped_mb} MB to settings.")
            # --- SAVE TO SETTINGS ---
            self.settings.setValue(SAVED_VRAM_KEY, clamped_mb) # Save the value that was successfully set
            self.settings.sync() # Ensure it's written to disk
            # ------------------------
            # Schedule a refresh after a short delay
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
        if reason == QSystemTrayIcon.ActivationReason.Trigger or reason == QSystemTrayIcon.ActivationReason.Context:
            print(f"[App] Tray icon activated (Reason: {reason}), showing menu.")
            # Refresh current values *before* showing the menu
            vram_changed = self.update_ram_values()
            # Reset target to current when menu is opened, ensures slider starts at current value
            self.target_vram_mb = self.current_vram_mb
            # Update all menu item states based on refreshed data and reset target
            self.update_menu_items()
            # Position and show the menu
            self.menu.popup(QCursor.pos())


    # --- Slot Methods for Actions ---
    def set_default_vram(self):
        """Sets VRAM to the system default (by setting the key to 0)."""
        print(f"[App] User requested setting VRAM to System Default.")
        # We pass 0 to the utility, which handles the OS default logic.
        # Update target immediately for UI feedback before applying
        # Show the *calculated* default in the UI, but apply 0
        calculated_default_mb = utils.calculate_default_vram_mb(self.total_ram_mb)
        self.target_vram_mb = calculated_default_mb
        self.update_menu_items()
        # Trigger the actual setting process (which passes 0 to the utility)
        self._set_vram_and_update(0) # Pass 0 to signify default

    def set_preset_vram(self, value_mb):
        """Sets VRAM to a specific preset value."""
        print(f"[App] User requested setting VRAM to Preset: {value_mb} MB")
        # Update target immediately for UI feedback
        self.target_vram_mb = value_mb
        self.update_menu_items()
        # Trigger the actual setting process
        self._set_vram_and_update(value_mb)

    # --- New Method for Startup Application ---
    def apply_saved_vram_on_startup(self):
        """Loads saved VRAM from settings and applies if different from current."""
        if not self.is_operational:
            print("[Startup Apply] Not operational, skipping saved VRAM check.")
            return

        saved_vram_mb_variant = self.settings.value(SAVED_VRAM_KEY, defaultValue=None)
        saved_vram_mb = None
        if saved_vram_mb_variant is not None:
            try:
                saved_vram_mb = int(saved_vram_mb_variant)
            except (ValueError, TypeError):
                print(f"[Startup Apply] Warning: Could not parse saved VRAM value '{saved_vram_mb_variant}'. Ignoring.")
                saved_vram_mb = None

        if saved_vram_mb is not None:
            print(f"[Startup Apply] Found saved VRAM setting: {saved_vram_mb} MB")
            # Ensure current_vram_mb is up-to-date (should be from init sequence)
            print(f"[Startup Apply] Current VRAM setting is: {self.current_vram_mb} MB")

            if saved_vram_mb != self.current_vram_mb:
                print(f"[Startup Apply] Saved VRAM ({saved_vram_mb} MB) differs from current ({self.current_vram_mb} MB). Applying saved value.")

                # Clamp saved value to current valid range before applying
                clamped_saved_vram = max(self.min_vram_mb, min(saved_vram_mb, self.max_vram_mb))
                if clamped_saved_vram != saved_vram_mb:
                     print(f"[Startup Apply] Warning: Clamping saved VRAM {saved_vram_mb}MB to current valid range [{self.min_vram_mb}-{self.max_vram_mb}]: {clamped_saved_vram}MB")

                # IMPORTANT: Decide on user experience for password prompt
                # Option 1: Apply directly (will prompt immediately)
                self.target_vram_mb = clamped_saved_vram # Set target for consistency
                self.update_menu_items() # Update UI elements state
                self._set_vram_and_update(clamped_saved_vram)

                # Option 2: Ask user first (comment out the direct apply above and uncomment below)
                # reply = QMessageBox.question(None, 'Apply Saved VRAM?',
                #              f"Apply saved VRAM setting of {clamped_saved_vram} MB?\n"
                #              f"(Current is {self.current_vram_mb} MB)",
                #              QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                #              QMessageBox.StandardButton.No)
                # if reply == QMessageBox.StandardButton.Yes:
                #     print("[Startup Apply] User chose to apply saved setting.")
                #     self.target_vram_mb = clamped_saved_vram
                #     self.update_menu_items()
                #     self._set_vram_and_update(clamped_saved_vram)
                # else:
                #     print("[Startup Apply] User chose not to apply saved setting.")

            else:
                print("[Startup Apply] Saved VRAM matches current setting. No action needed.")
        else:
            print("[Startup Apply] No saved VRAM setting found.")


    # --- Utility Methods for User Feedback (remain in App class) ---
    def _show_message(self, title, message):
        """Shows an informational message via the system tray."""
        if self.tray_icon.isVisible():
            self.tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 3000)
        else:
            print(f"INFO [{title}]: {message}") # Fallback if tray not visible

    def _show_warning(self, title, message):
        """Shows a warning message dialog."""
        QMessageBox.warning(None, title, message)

    def _show_error(self, title, message):
        """Shows a critical error message dialog."""
        QMessageBox.critical(None, title, message)

    # --- Application Exit ---
    def quit_app(self):
        """Stops timers, hides tray icon, and quits the application."""
        print("[App] Quitting application...")
        self.refresh_timer.stop()
        self.tray_icon.hide()
        self.app.quit()