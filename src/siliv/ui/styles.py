# src/siliv/ui/styles.py
# Stylesheet for the Siliv application menu.

# --- Adjusted Dark Theme Stylesheet (Based on unnamed.png) ---
# Aiming for the darker grey look with specific text colors
DARK_MENU_STYLESHEET = """
    QMenu {
        background-color: #2E2E2E; /* Dark grey background */
        color: #E0E0E0; /* Default light text */
        border: 1px solid #404040;
        border-radius: 8px; /* Rounded corners for menu */
        padding: 4px; /* Padding inside menu */
        font-size: 11pt; /* Default font size */
    }
    QMenu::item {
        padding: 6px 20px 6px 20px; /* Adjust padding */
        min-height: 24px;
        background-color: transparent;
        color: #E0E0E0; /* Standard item text */
    }
    QMenu::item:selected {
        background-color: #4A4A4A; /* Selection color */
        color: #FFFFFF;
        border-radius: 4px; /* Rounded selection */
    }
    QMenu::item:disabled {
        color: #808080; /* Dimmer disabled text */
        background-color: transparent;
    }
    /* Style the submenu indicator */
    QMenu::right-arrow {
        image: none; /* Remove default arrow if needed */
    }
    QMenu::indicator:non-exclusive:unchecked { /* Style checkmarks if used */
        image: none;
    }
    QMenu::separator {
        height: 1px;
        background: #484848; /* Slightly lighter separator */
        margin-top: 4px;
        margin-bottom: 4px;
        margin-left: 10px;
        margin-right: 10px;
    }
    /* Styling for embedded QWidgetAction widgets */
    QWidgetAction {
        background-color: transparent;
    }
    /* Style Tooltips */
    QToolTip {
        color: #E0E0E0;
        background-color: #444444;
        border: 1px solid #505050;
        padding: 4px;
    }
    /* Styling for QInputDialog (if ever used again) */
    QInputDialog QLineEdit { color: #E0E0E0; background-color: #444444; border: 1px solid #656565; }
    QInputDialog QPushButton { color: #E0E0E0; background-color: #555555; border: 1px solid #656565; border-radius: 4px; padding: 5px 15px; min-width: 70px; }
    QInputDialog QPushButton:hover { background-color: #606060; }
    QInputDialog QPushButton:pressed { background-color: #4A4A4A; }
    QInputDialog QPushButton:default { border: 1px solid #77BBFF; }

    /* --- Styling for Slider Widget embedded in menu --- */
    /* Use the default slider style to ensure ticks are visible, */
    /* but customize the ticks themselves for better contrast. */
    QWidget#SliderWidget QSlider::tick:horizontal {
         height: 5px;
         width: 1px;
         background: #A0A0A0; /* Slightly dimmer tick color than pure white */
         margin-top: 2px;   /* Move ticks slightly below the groove */
         margin-bottom: 2px; /* Add margin below ticks */
    }
    /* --- End Styling for Slider Widget --- */
"""