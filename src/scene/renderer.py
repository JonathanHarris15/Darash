import bisect
from PySide6.QtGui import QPen, QColor
from PySide6.QtCore import Qt, QPointF
from PySide6.QtWidgets import QGraphicsLineItem
from src.scene.components.reader_items import VerseNumberItem, SentenceHandleItem, TranslationIndicatorItem
from src.scene.outline_renderer import OutlineRenderer
from src.scene.study_renderer import StudyRenderer

class OverlayRenderer:
    def __init__(self, scene):
        self.scene = scene
        self.translation_indicator_items = [] # Track indicators for cleanup
        self.outline_renderer = OutlineRenderer(scene)
        self.study_renderer = StudyRenderer(scene)

    def render_verses(self):
        scene = self.scene
        doc = scene.main_text_item.document()
        layout = doc.documentLayout()
        
        pos = layout.hitTest(QPointF(scene.side_margin + 10, scene.scroll_y + 100), Qt.FuzzyHit)
        if pos != -1:
            ref = scene._get_ref_from_pos(pos)
            if ref and ref != scene.last_emitted_ref:
                scene.last_emitted_ref = ref
                scene.currentReferenceChanged.emit(ref)
        
        self._render_visible_verse_numbers()
        
        active_translations = [scene.primary_translation] + scene.enabled_interlinear
        if len(active_translations) > 1:
            self._render_interlinear_dividers()
        else:
            # Clear them if they exist
            if hasattr(scene, "interlinear_divider_items"):
                for it in scene.interlinear_divider_items:
                    scene.removeItem(it)
                scene.interlinear_divider_items.clear()
            
        if scene.strongs_enabled:
            self.study_renderer.render_strongs_overlays()
            
        if scene.outlines_enabled or scene.active_outline_id:
            self.outline_renderer.render()
            
        # Ensure marks, symbols, and arrows are updated with the new layout
        scene._render_study_overlays()

    def _render_interlinear_dividers(self):
        scene = self.scene
        if not hasattr(scene, "interlinear_divider_items"):
            scene.interlinear_divider_items = []
            
        for it in scene.interlinear_divider_items:
            scene.removeItem(it)
        scene.interlinear_divider_items.clear()
        
        # Less faint, slightly thicker line
        pen = QPen(QColor(100, 100, 100, 150), 1.0) 
        
        # Draw line at the bottom of each verse's stack in the visible chunk
        for i in range(scene.chunk_start_idx, scene.chunk_end_idx):
            verse = scene.loader.flat_verses[i]
            ref = verse['ref']
            if ref not in scene.verse_y_map: continue
            
            y_top, y_bottom = scene.verse_y_map[ref]
            
            # Don't draw divider for the last verse in the chunk
            if i == scene.chunk_end_idx - 1: continue
            
            line = QGraphicsLineItem(scene.side_margin, y_bottom, scene.last_width - scene.side_margin, y_bottom)
            line.setPen(pen)
            line.setZValue(-2)
            line.setAcceptedMouseButtons(Qt.NoButton)
            line.setVisible(scene._is_rect_visible(line.boundingRect()))
            scene.addItem(line)
            scene.interlinear_divider_items.append(line)

    def _render_visible_verse_numbers(self):
        scene = self.scene
        doc = scene.main_text_item.document()
        layout = doc.documentLayout()
        
        buffer = 500 # Increased buffer for smoother scrolling
        start_pos = layout.hitTest(QPointF(scene.side_margin + 10, max(0, scene.scroll_y - buffer)), Qt.FuzzyHit)
        end_pos = layout.hitTest(QPointF(scene.side_margin + 10, scene.scroll_y + scene.view_height + buffer), Qt.FuzzyHit)
        
        if start_pos == -1: start_pos = 0
        if end_pos == -1: end_pos = doc.characterCount()
        
        visible_refs = set()
        visible_sentence_refs = set()
        start_idx = bisect.bisect_left(scene.pos_verse_map, (start_pos, ""))
        end_idx = bisect.bisect_right(scene.pos_verse_map, (end_pos, "zzzzzz"))
        
        start_idx = max(0, start_idx - 1)
        end_idx = min(len(scene.pos_verse_map), end_idx + 1)
        
        verse_indents = scene.study_manager.data.get("verse_indent", {})
        verse_marks = scene.study_manager.data.get("verse_marks", {})
        
        # Clear old indicators
        for it in self.translation_indicator_items:
            scene.removeItem(it)
        self.translation_indicator_items.clear()
        
        active_translations = [scene.primary_translation] + scene.enabled_interlinear

        for i in range(start_idx, end_idx):
            char_pos, ref = scene.pos_verse_map[i]
            visible_refs.add(ref)
            
            mark_type = verse_marks.get(ref)
            is_selected = hasattr(scene, "selected_refs") and ref in scene.selected_refs

            verse_data = scene.loader.get_verse_by_ref(ref)
            if not verse_data: continue
            
            block = doc.findBlock(char_pos)
            if not block.isValid(): continue
            rect = layout.blockBoundingRect(block)
            
            # Use |0 suffix for indentation level if sentences are enabled
            s_ref = f"{ref}|0" if scene.sentence_break_enabled else ref
            indent_level = verse_indents.get(s_ref, verse_indents.get(ref, 0))
            
            if ref not in scene.verse_number_items:
                v_item = VerseNumberItem(verse_data['verse_num'], ref, scene.verse_num_font, scene.ref_color, mark_font=scene.verse_mark_font)
                v_item.setZValue(10)
                v_item.clicked.connect(lambda shift, v=v_item: scene._on_verse_num_clicked(v, shift))
                v_item.doubleClicked.connect(scene._clear_verse_selection)
                v_item.contextMenuRequested.connect(lambda pos, v=v_item: scene._on_verse_num_context_menu(v, pos))
                v_item.dragged.connect(lambda dx, v=v_item: scene.indentation_manager.on_verse_num_dragged(v, dx))
                v_item.released.connect(scene.indentation_manager.on_verse_num_released)
                
                scene.addItem(v_item)
                scene.verse_number_items[ref] = v_item
            
            # ALWAYS update position and state to handle scrolling/layout changes
            v_item = scene.verse_number_items[ref]
            v_item.setPos(scene.side_margin + (indent_level * scene.tab_size), rect.top())
            v_item.mark_type = mark_type
            v_item.is_selected = is_selected
            v_item.is_search_result = ref in getattr(scene, 'search_verse_refs', set())
            v_item.update()
            
            # --- Render Translation Labels if multiple translations active ---
            if len(active_translations) > 1:
                # Primary translation label
                # ... (rest of translation label logic)
                baseline_y = rect.top()
                block_layout = block.layout()
                if block_layout.lineCount() > 0:
                    first_line = block_layout.lineAt(0)
                    baseline_y += first_line.y() + first_line.ascent()
                else:
                    baseline_y += scene.font_size
                    
                p_label = TranslationIndicatorItem(scene.primary_translation, scene, scene.ref_color)
                p_label.setPos(scene.side_margin + (indent_level * scene.tab_size) + 28, baseline_y)
                scene.addItem(p_label)
                self.translation_indicator_items.append(p_label)
                
                # Secondary translation labels
                curr_block = block.next()
                if scene.sentence_break_enabled:
                    s_idx = 1
                    while f"{ref}|{s_idx}" in scene.verse_pos_map:
                        curr_block = curr_block.next()
                        s_idx += 1
                
                for tid in scene.enabled_interlinear:
                    if curr_block and curr_block.isValid():
                        t_rect = layout.blockBoundingRect(curr_block)
                        t_block_layout = curr_block.layout()
                        t_baseline_y = t_rect.top()
                        if t_block_layout.lineCount() > 0:
                            t_first_line = t_block_layout.lineAt(0)
                            t_baseline_y += t_first_line.y() + t_first_line.ascent()
                        else:
                            t_baseline_y += scene.font_size
                            
                        t_label = TranslationIndicatorItem(tid, scene, QColor(120, 120, 120))
                        t_label.setPos(scene.side_margin + (indent_level * scene.tab_size) + 28, t_baseline_y)
                        scene.addItem(t_label)
                        self.translation_indicator_items.append(t_label)
                        curr_block = curr_block.next()
                
            # Handle additional sentence handles for indentation
            if scene.sentence_break_enabled:
                s_idx = 1 # Start from index 1 as index 0 is covered by VerseNumberItem
                while True:
                    s_ref = f"{ref}|{s_idx}"
                    if s_ref not in scene.verse_pos_map: break
                    
                    visible_sentence_refs.add(s_ref)
                    s_pos = scene.verse_pos_map[s_ref]
                    s_block = doc.findBlock(s_pos)
                    s_rect = layout.blockBoundingRect(s_block)
                    s_indent = verse_indents.get(s_ref, 0)
                    
                    if s_ref not in scene.sentence_handle_items:
                        s_item = SentenceHandleItem(ref, s_ref, scene.verse_num_font, scene.ref_color)
                        s_item.setZValue(9)
                        s_item.clicked.connect(lambda shift, v=s_item: scene._on_verse_num_clicked(v, shift))
                        s_item.dragged.connect(lambda dx, v=s_item: scene.indentation_manager.on_verse_num_dragged(v, dx))
                        s_item.released.connect(scene.indentation_manager.on_verse_num_released)
                        
                        scene.addItem(s_item)
                        scene.sentence_handle_items[s_ref] = s_item
                    
                    # ALWAYS update position
                    scene.sentence_handle_items[s_ref].setPos(scene.side_margin + (s_indent * scene.tab_size), s_rect.top())
                    scene.sentence_handle_items[s_ref].setVisible(self._is_rect_visible(s_rect))
                    
                    s_idx += 1

        to_remove = []
        for ref, it in scene.verse_number_items.items():
            if ref not in visible_refs and not it.is_selected:
                to_remove.append(ref)
        
        for ref in to_remove:
            it = scene.verse_number_items.pop(ref)
            scene.removeItem(it)

        to_remove_s = []
        for s_ref, it in scene.sentence_handle_items.items():
            if s_ref not in visible_sentence_refs:
                to_remove_s.append(s_ref)
        for s_ref in to_remove_s:
            it = scene.sentence_handle_items.pop(s_ref)
            scene.removeItem(it)

    def _render_outline_overlays(self):
        self.outline_renderer.render()

    def _render_strongs_overlays(self):
        self.study_renderer.render_strongs_overlays()

    def _render_search_overlays(self):
        self.study_renderer.render_search_overlays()

    def _is_rect_visible(self, r):
        scene = self.scene
        buffer = 800 
        return not (r.bottom() < scene.scroll_y - buffer or r.top() > scene.scroll_y + scene.view_height + buffer)

    def create_symbol_item(self, symbol_name, target_rect, opacity):
        return self.study_renderer.create_symbol_item(symbol_name, target_rect, opacity)

    def flash_verse(self, ref):
        self.study_renderer.flash_verse(ref)

    def update_flash_fade(self):
        self.study_renderer.update_flash_fade()
