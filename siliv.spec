# siliv.spec - PyInstaller specification file

# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files
import os

# --- Basic Analysis ---
app_entry_point = 'src/siliv/main.py'
app_name = 'Siliv'
icon_path_source = 'assets/icons/icon.icns'

# datas: Include icon preserving structure
datas = [ (icon_path_source, 'assets/icons') ]

# Updated hidden imports for PyQt6
hiddenimports = [
    'PyQt6.sip',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets'
]

a = Analysis(
    [app_entry_point],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher_block_size=16,
    noarchive=False
)

# --- Bytecode Compilation ---
pyz = PYZ(a.pure, a.zipped_data, cipher_block_size=16)

# --- Executable Creation ---
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False, # Set to False for GUI applications
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path_source
)

# --- macOS Application Bundle ---
app = BUNDLE(
    exe,
    name=f'{app_name}.app',
    icon=icon_path_source,
    bundle_identifier='com.sub01.siliv',
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'NSAppleScriptEnabled': False,
        'LSUIElement': '1',
        'CFBundleDisplayName': app_name,
        'CFBundleName': app_name,
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0',
        'NSHumanReadableCopyright': 'Copyright © 2025 Sub01. All rights reserved.'
    }
)