# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 配置：打包 GUI 为 Windows 可执行程序。"""

from pathlib import Path

block_cipher = None

# spec 位于 build/windows/，项目根目录为上两级
PROJECT_ROOT = Path(SPECPATH).resolve().parent.parent

a = Analysis(
    [str(PROJECT_ROOT / "pdf_to_word_gui.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[],
    hiddenimports=[
        "pdf_to_word",
        "pdf2docx",
        "pdf2docx.converter",
        "fitz",
        "docx",
        "numpy",
        "PIL",
        "PIL.Image",
        "lxml",
        "lxml.etree",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "scipy", "pandas", "pytest"],
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
    name="PdfToWord",
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
    name="PdfToWord",
)
