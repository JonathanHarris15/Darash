# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

import os
from PyInstaller.utils.hooks import collect_data_files

# Helper to include files from junctions/subtrees that PyInstaller might skip
def get_translation_files():
    trans_dir = os.path.join('data', 'BibleTranslations', 'bible-master', 'bible-master', 'bible', 'translations')
    files = []
    if os.path.exists(trans_dir):
        for f in os.listdir(trans_dir):
            if f.endswith('.xml'):
                # Source path, Destination path (relative to app root)
                src = os.path.join(trans_dir, f)
                dest = os.path.join('data', 'BibleTranslations', 'bible-master', 'bible-master', 'bible', 'translations')
                files.append((src, dest))
    return files

added_files = [
    ('data', 'data'),
    ('resources', 'resources'),
    ('symbols_library', 'symbols_library'),
] + get_translation_files() + collect_data_files('spellchecker')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=['spellchecker'],
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
    console=True,
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
