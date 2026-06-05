# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 配置：打包图片处理工具 GUI 为 Windows 可执行程序。"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

PROJECT_ROOT = Path(SPECPATH).resolve().parent.parent

hiddenimports = [
    "image_processing",
    "image_utils",
    "ocr_engines",
    "PIL",
    "PIL.Image",
    "PIL.ImageOps",
    "PIL.ImageEnhance",
    "PIL.ImageTk",
    "cv2",
    "numpy",
    "docx",
    "pytesseract",
    "tkinter",
    "tkinter.ttk",
    "tkinter.filedialog",
    "tkinter.colorchooser",
    "tkinter.scrolledtext",
    "tkinter.messagebox",
    "paddle",
    "paddle.base",
    "paddle.base.core",
    "paddleocr",
    "paddlex",
]

# 仅收集 OCR 管线相关子模块，避免 collect 全量包导致 CI 超时/OOM
for sub in (
    "paddleocr._pipelines",
    "paddleocr._models",
    "paddleocr._utils",
    "paddlex.inference",
    "paddlex.utils",
):
    try:
        hiddenimports += collect_submodules(sub)
    except Exception:
        pass

datas: list = []
binaries: list = []

for pkg in ("paddleocr", "paddlex"):
    try:
        ret = collect_all(pkg)
        datas += ret[0]
        binaries += ret[1]
        hiddenimports += ret[2]
    except Exception:
        pass

a = Analysis(
    [str(PROJECT_ROOT / "image_tool_gui.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=list(dict.fromkeys(hiddenimports)),
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
    name="ImageTool",
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
    name="ImageTool",
)
