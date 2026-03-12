import bisect
import os
from PySide6.QtGui import QColor, QPen, QBrush, QPixmap
from PySide6.QtCore import Qt, QPointF
from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsLineItem, QGraphicsPixmapItem
from src.ui.theme import Theme

class StudyRenderer:
    def __init__(self, scene):
        self.scene = scene

    def render_strongs_overlays(self):
        scene = self.scene
        scene._clear_strongs_overlays()
        
        doc = scene.main_text_item.document()
        layout = doc.documentLayout()
        
        buffer = 100
        start_pos = layout.hitTest(QPointF(scene.side_margin + 10, max(0, scene.scroll_y - buffer)), Qt.FuzzyHit)
        end_pos = layout.hitTest(QPointF(scene.side_margin + 10, scene.scroll_y + scene.view_height + buffer), Qt.FuzzyHit)
        
        if start_pos == -1: start_pos = 0
        if end_pos == -1: end_pos = doc.characterCount()
        
        start_idx = bisect.bisect_left(scene.pos_verse_map, (start_pos, ""))
        end_idx = bisect.bisect_right(scene.pos_verse_map, (end_pos, "zzzzzz"))
        
        start_idx = max(0, start_idx - 1)
        end_idx = min(len(scene.pos_verse_map), end_idx + 1)
        
        pen = QPen(Theme.color("ACCENT_GOLD"), 1.5) 
        pen.setColor(QColor(255, 204, 0, 180)) # Semi-transparent gold for better blending
        
        for i in range(start_idx, end_idx):
            char_pos, ref = scene.pos_verse_map[i]
            
            # Use the actual displayed primary translation, not raw ESV base data
            verse = None
            if scene.primary_translation in scene.loader.translation_cache:
                v_parts = ref.split()
                if len(v_parts) >= 2:
                    book_name = " ".join(v_parts[:-1])
                    c_v = v_parts[-1].split(":")
                    if len(c_v) == 2:
                        chapter, v_num = c_v[0], c_v[1]
                        verse = scene.loader.translation_cache[scene.primary_translation].get(
                            book_name, {}).get(chapter, {}).get(v_num)

            if not verse:
                verse = scene.loader.get_verse_by_ref(ref)
                
            if not verse: continue
            
            v_start = scene.verse_pos_map[ref]
            
            for word_idx, token in enumerate(verse['tokens']):
                if len(token) > 1:
                    start_pos_in_v = scene._get_word_offset_in_verse(verse, word_idx)
                    rects = scene._get_text_rects(v_start + start_pos_in_v, len(token[0]))
                    for r in rects:
                        line = QGraphicsLineItem(r.left(), r.bottom() + 1, r.right(), r.bottom() + 1)
                        line.setPen(pen)
                        line.setZValue(-1)
                        line.setAcceptedMouseButtons(Qt.NoButton)
                        scene.addItem(line)
                        scene.strongs_overlay_items.append(line)

    def render_search_overlays(self):
        scene = self.scene
        for it in scene.search_overlay_items: scene.removeItem(it)
        scene.search_overlay_items.clear()
        
        # We only draw overlays for chapter and book headings here.
        # Verse number highlights are handled intrinsically by VerseNumberItem in their own paint methods.
        search_matches = getattr(scene, 'search_heading_matches', set())
        if not search_matches: return
        
        for h_rect, h_type, h_text in scene.heading_rects:
            if (h_type, h_text) in search_matches:
                hl = QGraphicsRectItem(h_rect)
                hl.setBrush(QBrush(Theme.color("SEARCH_HIGHLIGHT")))
                hl.setPen(Qt.NoPen)
                hl.setZValue(-1)
                hl.setAcceptedMouseButtons(Qt.NoButton)
                hl.setVisible(self._is_rect_visible(h_rect))
                scene.addItem(hl)
                scene.search_overlay_items.append(hl)

    def _is_rect_visible(self, r):
        scene = self.scene
        buffer = 800 
        return not (r.bottom() < scene.scroll_y - buffer or r.top() > scene.scroll_y + scene.view_height + buffer)

    def create_symbol_item(self, symbol_name, target_rect, opacity):
        scene = self.scene
        pix_path = scene.symbol_manager.get_symbol_path(symbol_name)
        if not os.path.exists(pix_path): return None
        target_h = int(target_rect.height() * 1.8)
        cache_key = (symbol_name, target_h)
        if cache_key in scene.pixmap_cache: scaled_pix = scene.pixmap_cache[cache_key]
        else:
            orig_pix = QPixmap(pix_path)
            scaled_pix = orig_pix.scaled(target_h, target_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            scene.pixmap_cache[cache_key] = scaled_pix
        pix_item = QGraphicsPixmapItem(scaled_pix); pix_item.setOpacity(opacity)
        pix_item.setAcceptedMouseButtons(Qt.NoButton); pix_item.setZValue(5)
        x_pos = target_rect.left() + (target_rect.width() - scaled_pix.width()) / 2
        y_pos = target_rect.top() + (target_rect.height() - scaled_pix.height()) / 2
        pix_item.setPos(x_pos, y_pos)
        return pix_item

    def flash_verse(self, ref):
        scene = self.scene
        if ref not in scene.verse_pos_map: return
        pos = scene.verse_pos_map[ref]; doc = scene.main_text_item.document(); rects = scene._get_text_rects(pos, doc.findBlock(pos).length())
        for r in rects:
            item = QGraphicsRectItem(r); item.setBrush(QBrush(QColor(100, 200, 255, 100))); item.setPen(Qt.NoPen); item.setZValue(-2) 
            scene.addItem(item); scene.flash_items.append([item, 1.0])
        if not scene.flash_timer.isActive(): scene.flash_timer.start()

    def update_flash_fade(self):
        scene = self.scene
        to_remove = []
        for i, (item, opacity) in enumerate(scene.flash_items):
            new_opacity = opacity - 0.05
            if new_opacity <= 0: scene.removeItem(item); to_remove.append(i)
            else: item.setOpacity(new_opacity); scene.flash_items[i][1] = new_opacity
        for i in sorted(to_remove, reverse=True): scene.flash_items.pop(i)
        if not scene.flash_items: scene.flash_timer.stop()
