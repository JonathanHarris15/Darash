import os
import shutil
import re
from pathlib import Path

# Mapping of current file name to new relative path
file_mapping = {
    'appearance_panel.py': 'ui/components/appearance_panel.py',
    'bookmark_ui.py': 'ui/components/bookmark_ui.py',
    'constants.py': 'core/constants.py',
    'main.py': 'core/main.py',
    'mark_popup.py': 'ui/components/mark_popup.py',
    'navigation.py': 'ui/components/navigation.py',
    'note_editor.py': 'ui/components/note_editor.py',
    'outline_dialog.py': 'ui/components/outline_dialog.py',
    'outline_editor.py': 'ui/components/outline_editor.py',
    'outline_manager.py': 'managers/outline_manager.py',
    'outline_panel.py': 'ui/components/outline_panel.py',
    'reader_items.py': 'scene/components/reader_items.py',
    'reader_scene.py': 'scene/reader_scene.py',
    'reader_utils.py': 'utils/reader_utils.py',
    'scene_input_handler.py': 'scene/scene_input_handler.py',
    'scene_overlay_manager.py': 'scene/scene_overlay_manager.py',
    'search_bar.py': 'ui/components/search_bar.py',
    'snake_path_finder.py': 'utils/snake_path_finder.py',
    'strongs_manager.py': 'managers/strongs_manager.py',
    'strongs_ui.py': 'ui/components/strongs_ui.py',
    'study_manager.py': 'managers/study_manager.py',
    'study_panel.py': 'ui/components/study_panel.py',
    'suggested_symbols_dialog.py': 'ui/components/suggested_symbols_dialog.py',
    'symbol_dialog.py': 'ui/components/symbol_dialog.py',
    'symbol_manager.py': 'managers/symbol_manager.py',
    'ui.py': 'ui/main_window.py',
    'verse_loader.py': 'core/verse_loader.py',
    '__init__.py': 'core/__init__.py'
}

# Add __init__.py files
for d in ['ui', 'ui/components', 'core', 'scene', 'scene/components', 'managers', 'utils']:
    init_path = Path(f'src/{d}/__init__.py')
    if not init_path.exists():
        init_path.parent.mkdir(parents=True, exist_ok=True)
        init_path.touch()

# Move the files
for old_name, new_path in file_mapping.items():
    src_file = Path(f'src/{old_name}')
    dest_file = Path(f'src/{new_path}')
    if src_file.exists():
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_file), str(dest_file))

# Import rewrite rules mapping old module name -> new module name
import_rules = {}
for old_name, new_path in file_mapping.items():
    old_mod = 'src.' + old_name.replace('.py', '')
    new_mod = 'src.' + new_path.replace('.py', '').replace('/', '.')
    import_rules[old_mod] = new_mod

# Fix imports in all python files
for py_file in Path('.').rglob('*.py'):
    # Skip venv or other external dirs if they exist
    if 'laptop-venv' in str(py_file): continue
    
    with open(py_file, 'r', encoding='utf-8') as f:
        content = f.read()
        
    original = content
    # Sort rules by length of old_mod descending to avoid partial matches on prefixes
    for old_mod, new_mod in sorted(import_rules.items(), key=lambda x: len(x[0]), reverse=True):
        escaped_old = old_mod.replace('.', r'\.')
        # Use negative lookahead to ensure we match the exact module path
        content = re.sub(rf'\bfrom {escaped_old}(?!\w|\.)', f'from {new_mod}', content)
        content = re.sub(rf'\bimport {escaped_old}(?!\w|\.)', f'import {new_mod}', content)
        
    if content != original:
        with open(py_file, 'w', encoding='utf-8') as f:
            f.write(content)

print("Files moved and imports updated.")
