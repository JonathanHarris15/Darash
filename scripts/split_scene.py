import re

with open('src/scene/reader_scene.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

def extract_methods(method_names):
    extracted = []
    in_method = False
    current_method = None
    remaining_lines = []
    
    for line in lines:
        match = re.match(r'^    def ([a-zA-Z0-9_]+)\(', line)
        if match:
            method = match.group(1)
            if method in method_names:
                in_method = True
                current_method = method
                extracted.append(line)
                continue
            else:
                in_method = False
        
        if in_method:
            extracted.append(line)
        else:
            remaining_lines.append(line)
            
    return extracted, remaining_lines

layout_methods = [
    'calculate_section_positions', 'recalculate_layout', '_update_heading_rects', 'apply_layout_changes'
]

renderer_methods = [
    'render_verses', '_render_visible_verse_numbers', '_clear_outline_overlays', '_render_outline_overlays',
    '_clear_strongs_overlays', '_render_strongs_overlays', '_render_search_overlays', '_render_study_overlays',
    '_create_symbol_item', '_update_flash_fade', 'flash_verse', '_update_all_verse_number_positions'
]

actions_methods = [
    '_create_outline_from_selection', '_create_outline_from_verse_selection', '_start_divider_drag',
    'open_note_by_key', '_on_note_editor_finished', 'handle_search', 'scroll_to_current_match',
    'next_match', 'prev_match', 'clear_search', '_clear_verse_selection', '_on_verse_num_context_menu',
    '_set_selected_verse_mark', '_clear_selection', '_on_mark_selected', '_apply_mark_to_verse',
    '_on_add_bookmark_requested', '_on_add_note_requested', 'cycle_divider_at_pos', 'jump_to',
    '_on_verse_num_clicked', '_on_verse_num_dragged', '_on_verse_num_released', '_show_suggested_symbols_dialog'
]

imports = """from PySide6.QtWidgets import (
    QGraphicsScene, QGraphicsPixmapItem, QGraphicsRectItem, QDialog, 
    QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsItem, QMenu
)
from PySide6.QtCore import Qt, QRectF, QTimer, Signal, QPointF
from PySide6.QtGui import (
    QColor, QFont, QPixmap, QBrush, QPen, QTextCursor, QCursor,
    QTextBlockFormat, QTextCharFormat, QAction, QClipboard, QGuiApplication
)
import bisect
import os
import math
import time

from src.core.constants import *
from src.scene.components.reader_items import *
from src.utils.reader_utils import *
from src.ui.main_window.components.outline_dialog import OutlineDialog
from src.ui.main_window.components.note_editor import NoteEditor
"""

def write_mixin(name, class_name, methods, imports_str=""):
    global lines
    extracted, lines = extract_methods(methods)
    with open(f'src/scene/{name}.py', 'w', encoding='utf-8') as f:
        f.write(imports_str + '\n\n')
        f.write(f'class {class_name}:\n')
        for line in extracted:
            f.write(line)

write_mixin('scene_layout', 'SceneLayoutMixin', layout_methods, imports)
write_mixin('scene_renderer', 'SceneRendererMixin', renderer_methods, imports)
write_mixin('scene_actions', 'SceneActionsMixin', actions_methods, imports)

# Rewrite reader_scene.py
with open('src/scene/reader_scene.py', 'w', encoding='utf-8') as f:
    for line in lines:
        if line.startswith('class ReaderScene(QGraphicsScene):'):
            f.write('from src.scene.scene_layout import SceneLayoutMixin\n')
            f.write('from src.scene.scene_renderer import SceneRendererMixin\n')
            f.write('from src.scene.scene_actions import SceneActionsMixin\n\n')
            f.write('class ReaderScene(QGraphicsScene, SceneLayoutMixin, SceneRendererMixin, SceneActionsMixin):\n')
        else:
            f.write(line)

print("Split completed successfully.")
