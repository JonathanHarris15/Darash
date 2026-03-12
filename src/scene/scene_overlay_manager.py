import os
from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsLineItem, QGraphicsEllipseItem, QGraphicsPixmapItem
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QBrush, QPen, QPixmap
from src.scene.components.reader_items import (
    NoteIcon, ArrowItem, SnakeArrowItem, LogicalMarkItem, GhostArrowIconItem
)
from src.utils.snake_path_finder import SnakePathFinder
from src.ui.theme import Theme

class SceneOverlayManager:
    """
    Manages the lifecycle and rendering of all visual study overlays.
    """
    def __init__(self, scene):
        self.scene = scene
        self.path_finder = SnakePathFinder(scene)
        self._active_ghost_highlights = []  # Temp QGraphicsRectItems for hover highlights
        self._ghost_icon_map = {}           # key -> GhostArrowIconItem (for hover coordination)

    def render_study_overlays(self):
        scene = self.scene
        for it in scene.study_overlay_items:
            if it.scene() == scene:
                scene.removeItem(it)
        scene.study_overlay_items.clear()
        self._ghost_icon_map.clear()
        self._clear_ghost_highlights()
        
        self._render_marks_layer()
        self._render_logical_marks_layer()
        self._render_symbols_layer()
        self._render_notes_layer()
        self._render_arrows_layer()
        
        # Force a full repaint of the visible scene area. Qt only invalidates
        # per-item bounding rects when removeItem() is called, which can leave
        # ghost pixels from semi-transparent (alpha) fills and anti-aliased edges.
        scene.update(scene.sceneRect())

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
            if mark_type not in Theme.LOGICAL_MARKS: continue
            
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
                            symbol_text = Theme.LOGICAL_MARKS[mark_type]
                            
                            item = LogicalMarkItem(key, symbol_text, r, Theme.LOGICAL_MARK_COLOR)
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
                
                a_type = arrow_data.get('type', 'straight')
                
                if a_type == "ghost":
                    self._render_ghost_arrow(start_key, end_key)
                elif a_type == "snake":
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

    def _render_ghost_arrow(self, start_key, end_key):
        """Render ghost arrow icons on both the start and end word."""
        scene = self.scene
        start_rect = self._get_word_rect(start_key)
        end_rect = self._get_word_rect(end_key)
        if not start_rect or not end_rect:
            return

        start_icon = GhostArrowIconItem(start_rect, start_key, end_key, self)
        end_icon = GhostArrowIconItem(end_rect, end_key, start_key, self)

        for icon, rect in ((start_icon, start_rect), (end_icon, end_rect)):
            icon.setVisible(scene._is_rect_visible(rect))
            scene.addItem(icon)
            scene.study_overlay_items.append(icon)

        # Index icons by key so hover lookup is O(1)
        self._ghost_icon_map.setdefault(start_key, []).append(start_icon)
        self._ghost_icon_map.setdefault(end_key, []).append(end_icon)

    def _get_word_rect(self, key):
        """Return the first rect for a word key, or None."""
        scene = self.scene
        if not key: return None
        ref_parts = key.split('|')
        if len(ref_parts) < 4: return None
        ref = f"{ref_parts[0]} {ref_parts[1]}:{ref_parts[2]}"
        if ref not in scene.verse_pos_map: return None
        v_start = scene.verse_pos_map[ref]
        verse_data = scene.loader.get_verse_by_ref(ref)
        if not verse_data: return None
        word_idx = int(ref_parts[3])
        if word_idx >= len(verse_data['tokens']): return None
        offset = scene._get_word_offset_in_verse(verse_data, word_idx)
        rects = scene._get_text_rects(v_start + offset, len(verse_data['tokens'][word_idx][0]))
        return rects[0] if rects else None

    # ------------------------------------------------------------------
    # Ghost arrow hover coordination
    # ------------------------------------------------------------------

    def on_word_hover(self, word_key):
        """Called when the mouse hovers over a word."""
        self.on_word_hover_leave()
        if not word_key or word_key not in self._ghost_icon_map:
            return

        scene = self.scene
        # Find all keys connected to this word via ghost arrows
        keys_to_highlight = {word_key}
        for icon in self._ghost_icon_map[word_key]:
            keys_to_highlight.add(icon.partner_key)

        for key in keys_to_highlight:
            # Brighten all ghost icons for these words
            for icon in self._ghost_icon_map.get(key, []):
                icon.set_hovered(True)

            # Add highlight rect behind the word
            rect = self._get_word_rect(key)
            if rect:
                expanded = rect.adjusted(-2, -2, 2, 2)
                highlight = QGraphicsRectItem(expanded)
                color = QColor(100, 170, 255, 60)
                highlight.setBrush(QBrush(color))
                highlight.setPen(Qt.NoPen)
                highlight.setZValue(-0.5)
                scene.addItem(highlight)
                self._active_ghost_highlights.append(highlight)

    def on_word_hover_leave(self):
        """Called when the mouse leaves a hovered word or we want to clear ghost highlights."""
        self._clear_ghost_highlights()
        # Reset all icon hover states
        for icons in self._ghost_icon_map.values():
            for icon in icons:
                icon.set_hovered(False)

    def _clear_ghost_highlights(self):
        scene = self.scene
        for item in self._active_ghost_highlights:
            if item.scene() == scene:
                scene.removeItem(item)
        self._active_ghost_highlights.clear()

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

