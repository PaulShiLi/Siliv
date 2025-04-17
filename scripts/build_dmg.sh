#!/bin/bash

# --- Configuration ---
APP_NAME="Siliv"
SPEC_FILE="siliv.spec"
ICON_PATH="assets/icons/icon.icns" # Updated Icon Path
DIST_DIR="dist"
DMG_DIR="dmg_contents" # Temporary dir for DMG contents
FINAL_DMG_NAME="${APP_NAME}.dmg"
SRC_PACKAGE_DIR="src/siliv"

# --- Ensure running from project root ---
# Check for the spec file and source directory
if [ ! -f "$SPEC_FILE" ] || [ ! -d "$SRC_PACKAGE_DIR" ]; then
    echo "Error: This script must be run from the project root directory."
    echo "Ensure '${SPEC_FILE}' exists and the source directory is '${SRC_PACKAGE_DIR}'."
    exit 1
fi

echo "--- Cleaning previous builds ---"
rm -rf build "$DIST_DIR" "$DMG_DIR"

echo "--- Building application using PyInstaller ---"
# Run PyInstaller using the spec file
pyinstaller "$SPEC_FILE" || { echo "PyInstaller build failed"; exit 1; }

# --- Verify app bundle exists ---
APP_BUNDLE_PATH="${DIST_DIR}/${APP_NAME}.app"
if [ ! -d "$APP_BUNDLE_PATH" ]; then
    echo "Error: Application bundle '${APP_BUNDLE_PATH}' not found after build!"
    exit 1
fi
echo "Application bundle created at: ${APP_BUNDLE_PATH}"

# --- Prepare DMG contents ---
echo "--- Preparing files for DMG ---"
mkdir -p "$DMG_DIR"
# Copy the built .app bundle into the temporary DMG directory
cp -r "$APP_BUNDLE_PATH" "$DMG_DIR/" || { echo "Failed to copy app bundle"; exit 1; }

# --- Check/Install create-dmg ---
if ! command -v create-dmg &> /dev/null; then
    echo "create-dmg command not found. Attempting to install via Homebrew..."
    if ! command -v brew &> /dev/null; then
        echo "Error: Homebrew not found. Please install Homebrew and then run 'brew install create-dmg'."
        exit 1
    fi
    brew install create-dmg || { echo "Failed to install create-dmg via Homebrew"; exit 1; }
fi
CREATE_DMG_CMD=$(command -v create-dmg)
echo "Using create-dmg at: ${CREATE_DMG_CMD}"

# --- Check for icon (in new location) ---
if [ ! -f "$ICON_PATH" ]; then
    echo "Warning: Application icon not found at '${ICON_PATH}'. DMG will not have a custom volume icon."
    VOL_ICON_ARG=""
else
    VOL_ICON_ARG="--volicon \"${ICON_PATH}\"" # Use the updated ICON_PATH
fi


# --- Create DMG ---
echo "--- Creating DMG ---"
# The --volicon argument uses the updated ICON_PATH relative to the project root
eval "$CREATE_DMG_CMD \
  --volname \"${APP_NAME} Installer\" \
  ${VOL_ICON_ARG} \
  --window-pos 200 120 \
  --window-size 600 300 \
  --icon-size 100 \
  --icon \"${APP_NAME}.app\" 175 120 \
  --hide-extension \"${APP_NAME}.app\" \
  --app-drop-link 425 120 \
  \"${DIST_DIR}/${FINAL_DMG_NAME}\" \
  \"${DMG_DIR}/\""
if [ $? -ne 0 ]; then
    echo "Error: create-dmg failed."
    exit 1
fi


# --- Clean up temporary DMG directory ---
echo "--- Cleaning up temporary files ---"
rm -rf "$DMG_DIR"

echo "--- Build Complete ---"
echo "DMG created at: $(pwd)/${DIST_DIR}/${FINAL_DMG_NAME}"

exit 0
