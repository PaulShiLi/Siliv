<div align="center">
  <h1>Siliv</h1>
  <img src="assets/icons/logo.png" alt="Siliv Logo" width="150" height="150">
  <h3>Just Another MacOS menu bar utility to adjust GPU VRAM allocation</h3>
  <br>
</div>

## Description

Siliv (`Sili`con `V`RAM) provides a convenient way to view the current VRAM allocation on Apple Silicon Macs (and potentially some Intel Macs with adjustable VRAM via sysctl) and set a custom limit. This can be useful for specific applications or games that might benefit from a higher VRAM allocation than the macOS default.

The application uses the `sysctl` command to read and write the `iogpu.wired_limit_mb` (macOS 14 Sonoma and later) or `debug.iogpu.wired_limit` (macOS 13 Ventura) values. Setting the VRAM requires administrator privileges.

## Features

* **Menu Bar Icon:** Resides in the macOS menu bar for easy access.
* **VRAM Display:** Shows current allocated VRAM and reserved system RAM.
* **Visual Allocation Bar:** Provides a graphical representation of the target VRAM vs. reserved RAM.
* **Custom Allocation:** Set a specific VRAM limit (in MB) using a slider.
    * Slider snaps to the nearest 5 GB interval upon release.
* **Presets:** Quickly apply predefined VRAM allocation values.
* **Default Reset:** Option to reset VRAM allocation to the macOS default (by setting the sysctl key to 0).
* **Automatic Refresh:** Periodically updates the displayed VRAM information.

## Requirements

* **Operating System:** macOS (Tested primarily on Ventura/Sonoma, may have limited functionality on older versions). Requires a version where `iogpu.wired_limit_mb` or `debug.iogpu.wired_limit` sysctl keys are available.
* **Python:** Python 3.x
* **Dependencies:** PyQt6 (see `requirements.txt`)

## Installation and Running from Source

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd siliv
    ```
2.  **Create a virtual environment (Recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Run the application:**
    ```bash
    python -m src.siliv.main
    ```
    The Siliv icon should appear in your menu bar.

## Building the Application (.dmg)

A build script is provided to create a distributable `.dmg` file using PyInstaller and `create-dmg`.

1.  **Install Build Tools:**
    * **PyInstaller:** `pip install pyinstaller`
    * **create-dmg:** Requires Homebrew. If you don't have Homebrew, install it first. Then run:
        ```bash
        brew install create-dmg
        ```
2.  **Run the build script:**
    ```bash
    ./scripts/build_dmg.sh
    ```
3.  The final `Siliv.dmg` file will be located in the `dist/` directory.

## Usage Notes

* **Administrator Privileges:** Setting the VRAM limit requires administrator privileges. You will be prompted for your password when applying a new VRAM value.
* **System Stability:** Modifying VRAM allocation is an advanced feature. Setting it too high might potentially lead to system instability if not enough RAM is left for the OS and other applications. Use with caution.
* **Persistence:** Changes made via `sysctl` might not persist across reboots by default.

