# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

block_cipher = None

# Collect PySide6 plugins and pyvista shaders
pyside6_datas = collect_data_files('PySide6')
pyvista_datas = collect_data_files('pyvista')

datas = pyside6_datas + pyvista_datas
binaries = []

# Map QPA plugins depending on OS
if sys.platform == 'win32':
    # Add windows specific binaries if needed
    pass
elif sys.platform == 'darwin':
    pass
elif sys.platform == 'linux':
    pass

a = Analysis(
    ['../dig/__main__.py'],
    pathex=['..'],
    binaries=binaries,
    datas=datas,
    hiddenimports=['vtkmodules', 'vtkmodules.all', 'pyvista', 'pyvistaqt', 'PySide6'],
    hookspath=['packaging/hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='dig',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file='packaging/macos/entitlements.plist' if sys.platform == 'darwin' else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='dig',
)
