# src/siliv/main.py
# Main entry point for the Siliv VRAM application.

import sys
import os
# Use PyQt6 imports
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

# Local Imports
from .app import MenuBarApp                      # Import the main application class
from .ui.styles import DARK_MENU_STYLESHEET    # Import the stylesheet
from .assets_helper import resource_path       # Import the asset path helper

def main():
    """Main function to initialize and run the application."""
    app = QApplication(sys.argv)

    # Apply the dark stylesheet globally
    app.setStyleSheet(DARK_MENU_STYLESHEET)

    # Prevent app from closing when a dialog (like error message) is closed
    app.setQuitOnLastWindowClosed(False)

    # --- Set Application Icon ---
    # Use resource_path to find icon in dev and bundled app
    icon_relative_path = 'assets/icons/icon.icns'
    icon_file_path = resource_path(icon_relative_path)
    app_icon = None

    if os.path.exists(icon_file_path):
        app_icon = QIcon(icon_file_path)
        app.setWindowIcon(app_icon) # Set for potential future windows/dialogs
        print(f"Using application icon: {icon_file_path}")
    else:
        print(f"Warning: Application icon not found at '{icon_file_path}'. Using default icon.")
        # icon_file_path will remain None or path won't exist

    # --- Create and Run the Menu Bar App ---
    # Pass the icon path (or None if not found) to MenuBarApp
    # MenuBarApp handles creating the QSystemTrayIcon with the QIcon object or a default one.
    menu_app = MenuBarApp(icon_path=icon_file_path)

    # MenuBarApp constructor handles showing initial errors if is_operational is False.
    # We can let it run in a limited state (showing info only) even if VRAM setting isn't possible.
    if not menu_app.total_ram_mb > 0:
         print("Critical error during initialization (could not get total RAM). Exiting.")
         # Show a final error message if the app couldn't even start properly
         QMessageBox.critical(None, "Initialization Failed", "Could not retrieve essential system information (Total RAM).\nThe application cannot continue.")
         sys.exit(1) # Exit if core info is missing

    # Start the Qt event loop
    sys.exit(app.exec()) # Use exec() in PyQt6

if __name__ == '__main__':
    main()