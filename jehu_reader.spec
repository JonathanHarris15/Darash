# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

added_files = [
    ('data', 'data'),
    ('resources', 'resources'),
    ('symbols_library', 'symbols_library'),
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

import os

# Helper to provide icon if it exists
def get_icon(path):
    return path if os.path.exists(path) else None

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='JehuReader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=get_icon('resources/icons/app_icon.ico'),
)

app = BUNDLE(
    exe,
    name='JehuReader.app',
    icon=get_icon('resources/icons/app_icon.icns'),
    bundle_identifier='com.jonathan.jehu-reader',
    info_plist={
        'NSHighResolutionCapable': 'True',
        'LSBackgroundOnly': 'False',
    },
)
