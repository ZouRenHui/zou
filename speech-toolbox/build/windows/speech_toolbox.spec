# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 配置：打包语音工具箱为 Windows 可执行程序。"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all

block_cipher = None

PROJECT_ROOT = Path(SPECPATH).resolve().parent.parent

datas: list = []
binaries: list = []
hiddenimports = [
    "document_text",
    "export_text",
    "synthesize",
    "transcribe",
    "docx",
    "pypdf",
    "pptx",
    "lxml",
    "lxml.etree",
    "tkinter",
    "tkinter.ttk",
    "tkinter.filedialog",
    "tkinter.messagebox",
    "asyncio",
    "aiohttp",
]

for package in ("faster_whisper", "ctranslate2", "onnxruntime", "edge_tts", "tokenizers", "av"):
    try:
        pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
        datas += pkg_datas
        binaries += pkg_binaries
        hiddenimports += pkg_hidden
    except Exception:
        pass

a = Analysis(
    [str(PROJECT_ROOT / "speech_toolbox_gui.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name="SpeechToolbox",
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
    name="SpeechToolbox",
)
