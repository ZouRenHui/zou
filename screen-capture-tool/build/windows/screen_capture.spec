# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 配置：打包录屏/截屏工具为 Windows 可执行程序。"""

from pathlib import Path

block_cipher = None

PROJECT_ROOT = Path(SPECPATH).resolve().parent.parent

a = Analysis(
    [str(PROJECT_ROOT / "screen_capture_gui.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[],
    hiddenimports=[
        "app_log",
        "clipboard_utils",
        "record_button",
        "recorder",
        "screenshot",
        "mss",
        "PIL",
        "PIL.Image",
        "PIL.ImageTk",
        "cv2",
        "numpy",
        "tkinter",
        "tkinter.ttk",
        "tkinter.filedialog",
        "tkinter.messagebox",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib",
        "scipy",
        "pandas",
        "pytest",
        "torch",
        "tensorflow",
        "IPython",
        "jupyter",
        "notebook",
        "sklearn",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ScreenCapture",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="ScreenCapture",
)
