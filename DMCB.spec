# -*- mode: python ; coding: utf-8 -*-

import sys

icon = (
    'icon.icns'
    if sys.platform == 'darwin'
    else 'icon.ico'
    if sys.platform == 'win32'
    else None
)

a = Analysis(
    ['src/dmcb/app.py'],
    pathex=['src', '.'],
    binaries=[],
    datas=[('icon.iconset/icon_512x512.png', 'icon.iconset')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DMCB',
    icon=icon,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DMCB',
)
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='DMCB.app',
        icon='icon.icns',
        bundle_identifier=None,
    )
