import os
from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsLineItem, QGraphicsEllipseItem, QGraphicsPixmapItem
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QBrush, QPen, QPixmap
from src.reader_items import NoteIcon, ArrowItem, SnakeArrowItem, LogicalMarkItem
from src.snake_path_finder import SnakePathFinder
from src.constants import LOGICAL_MARKS, LOGICAL_MARK_COLOR

class SceneOverlayManager:
    """
    Manages the lifecycle and rendering of all visual study overlays.
    """
    def __init__(self, scene):
        self.scene = scene
        self.path_finder = SnakePathFinder(scene)

    def render_study_overlays(self):
        scene = self.scene
        for it in scene.study_overlay_items:
            if it.scene() == scene:
                scene.removeItem(it)
        scene.study_overlay_items.clear()
        
        self._render_marks_layer()
        self._render_logical_marks_layer()
        self._render_symbols_layer()
        self._render_notes_layer()
        self._render_arrows_layer()

    def _render_marks_layer(self):
        scene = self.scene
        for mark in scene.study_manager.data["marks"]:
            ref = f"{mark['book']} {mark['chapter']}:{mark['verse_num']}"
            if ref in scene.verse_pos_map:
                start_pos = scene.verse_pos_map[ref] + mark['start']
                rects = scene._get_text_rects(start_pos, mark['length'])
                for r in rects:
                    self._add_mark_rect(r, mark['type'], mark.get('color', 'yellow'))

    def _render_logical_marks_layer(self):
        scene = self.scene
        # Logical marks are stored in logical_marks dict
        # key: mark_type (e.g. "arrow_right")
        for key, mark_type in scene.study_manager.data.get("logical_marks", {}).items():
            if mark_type not in LOGICAL_MARKS: continue
            
            ref_parts = key.split('|')
            ref = f"{ref_parts[0]} {ref_parts[1]}:{ref_parts[2]}"
            if ref in scene.verse_pos_map:
                v_start = scene.verse_pos_map[ref]
                verse_data = scene.loader.get_verse_by_ref(ref)
                if verse_data:
                    word_idx = int(ref_parts[3])
                    if word_idx < len(verse_data['tokens']):
                        start_pos = v_start + scene._get_word_offset_in_verse(verse_data, word_idx)
                        rects = scene._get_text_rects(start_pos, len(verse_data['tokens'][word_idx][0]))
                        if rects:
                            r = rects[0]
                            symbol_text = LOGICAL_MARKS[mark_type]
                            
                            item = LogicalMarkItem(key, symbol_text, r, scene.logical_mark_color)
                            item.setZValue(-0.5) # Behind text
                            item.setOpacity(scene.logical_mark_opacity)
                            item.setVisible(scene._is_rect_visible(r))
                            scene.addItem(item)
                            scene.study_overlay_items.append(item)

    def _render_symbols_layer(self):
        scene = self.scene
        symbol_opacity = scene.symbol_manager.get_opacity()
        for key, symbol_name in scene.study_manager.data["symbols"].items():
            ref_parts = key.split('|')
            ref = f"{ref_parts[0]} {ref_parts[1]}:{ref_parts[2]}"
            if ref in scene.verse_pos_map:
                v_start = scene.verse_pos_map[ref]
                verse_data = scene.loader.get_verse_by_ref(ref)
                if verse_data:
                    start_pos = v_start + scene._get_word_offset_in_verse(verse_data, int(ref_parts[3]))
                    rects = scene._get_text_rects(start_pos, len(verse_data['tokens'][int(ref_parts[3])][0]))
                    if rects:
                        r = rects[0]
                        pix_item = scene._create_symbol_item(symbol_name, r, symbol_opacity)
                        if pix_item:
                            pix_item.setVisible(scene._is_rect_visible(r))
                            scene.addItem(pix_item)
                            scene.study_overlay_items.append(pix_item)

    def _render_notes_layer(self):
        scene = self.scene
        for key in scene.study_manager.data["notes"].keys():
            if key.startswith("standalone_"): continue
            ref_parts = key.split('|')
            ref = f"{ref_parts[0]} {ref_parts[1]}:{ref_parts[2]}"
            if ref in scene.verse_pos_map:
                v_start = scene.verse_pos_map[ref]
                verse_data = scene.loader.get_verse_by_ref(ref)
                if verse_data:
                    start_pos = v_start + scene._get_word_offset_in_verse(verse_data, int(ref_parts[3]))
                    rects = scene._get_text_rects(start_pos, len(verse_data['tokens'][int(ref_parts[3])][0]))
                    if rects:
                        r = rects[0]
                        note_icon = NoteIcon(key, ref, scene)
                        note_icon.setPos(r.right() - 5, r.top() - 5)
                        note_icon.setVisible(scene._is_rect_visible(r))
                        scene.addItem(note_icon)
                        scene.study_overlay_items.append(note_icon)

    def _render_arrows_layer(self):
        scene = self.scene
        for start_key, arrow_list in scene.study_manager.data.get("arrows", {}).items():
            start_center = scene._get_word_center(start_key)
            if not start_center: continue
            for arrow_data in arrow_list:
                end_key = arrow_data.get('end_key')
                if not end_key: continue
                
                # Check arrow type
                a_type = arrow_data.get('type', 'straight')
                
                if a_type == "snake":
                    points = self.path_finder.calculate_path(start_key, end_key)
                    if points:
                        item = SnakeArrowItem(points, arrow_data['color'])
                        item.setOpacity(scene.arrow_opacity)
                        # Visibility check
                        xs = [p.x() for p in points]; ys = [p.y() for p in points]
                        rect = QRectF(min(xs), min(ys), max(xs)-min(xs), max(ys)-min(ys))
                        item.setVisible(scene._is_rect_visible(rect))
                        scene.addItem(item)
                        scene.study_overlay_items.append(item)
                else:
                    end_center = scene._get_word_center(end_key)
                    if end_center:
                        item = ArrowItem(start_center, end_center, arrow_data['color'])
                        item.setOpacity(scene.arrow_opacity)
                        item.setVisible(scene._is_rect_visible(QRectF(start_center, end_center).normalized()))
                        scene.addItem(item)
                        scene.study_overlay_items.append(item)

    def _add_mark_rect(self, r, mark_type, color_val):
        scene = self.scene
        color = QColor(color_val)
        item = None
        if mark_type == "highlight":
            color.setAlpha(120)
            item = QGraphicsRectItem(r); item.setBrush(QBrush(color))
            item.setPen(Qt.NoPen); item.setZValue(-1)
        elif mark_type == "underline":
            item = QGraphicsLineItem(r.left(), r.bottom(), r.right(), r.bottom()); item.setPen(QPen(color, 2))
        elif mark_type == "box":
            item = QGraphicsRectItem(r); item.setPen(QPen(color, 1))
        elif mark_type == "circle":
            item = QGraphicsEllipseItem(r); item.setPen(QPen(color, 1))
            
        if item:
            item.setAcceptedMouseButtons(Qt.NoButton)
            item.setVisible(scene._is_rect_visible(r))
            scene.addItem(item); scene.study_overlay_items.append(item)
