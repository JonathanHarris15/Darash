import bisect
from PySide6.QtGui import QPen, QColor, QBrush
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsLineItem
from src.scene.components.reader_items import VerseNumberItem, OutlineDividerItem, SentenceHandleItem, TranslationIndicatorItem

class OverlayRenderer:
    def __init__(self, scene):
        self.scene = scene
        self.translation_indicator_items = [] # Track indicators for cleanup

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
            self._render_strongs_overlays()
            
        if scene.outlines_enabled or scene.active_outline_id:
            self._render_outline_overlays()

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
        
        buffer = 200
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

            if ref not in scene.verse_number_items:
                verse_data = scene.loader.get_verse_by_ref(ref)
                if not verse_data: continue
                
                block = doc.findBlock(char_pos)
                rect = layout.blockBoundingRect(block)
                
                # Use |0 suffix for indentation level if sentences are enabled
                s_ref = f"{ref}|0" if scene.sentence_break_enabled else ref
                indent_level = verse_indents.get(s_ref, verse_indents.get(ref, 0))
                
                v_item = VerseNumberItem(verse_data['verse_num'], ref, scene.verse_num_font, scene.ref_color, mark_font=scene.verse_mark_font)
                v_item.setPos(scene.side_margin + (indent_level * scene.tab_size), rect.top())
                v_item.setZValue(10)
                v_item.mark_type = mark_type
                v_item.is_selected = is_selected
                v_item.is_search_result = ref in getattr(scene, 'search_verse_refs', set())
                
                v_item.clicked.connect(lambda shift, v=v_item: scene._on_verse_num_clicked(v, shift))
                v_item.doubleClicked.connect(scene._clear_verse_selection)
                v_item.contextMenuRequested.connect(lambda pos, v=v_item: scene._on_verse_num_context_menu(v, pos))
                v_item.dragged.connect(lambda dx, v=v_item: scene.indentation_manager.on_verse_num_dragged(v, dx))
                v_item.released.connect(scene.indentation_manager.on_verse_num_released)
                
                scene.addItem(v_item)
                scene.verse_number_items[ref] = v_item
            else:
                it = scene.verse_number_items[ref]
                is_search = ref in getattr(scene, 'search_verse_refs', set())
                if it.mark_type != mark_type or it.is_selected != is_selected or getattr(it, 'is_search_result', False) != is_search:
                    it.mark_type = mark_type
                    it.is_selected = is_selected
                    it.is_search_result = is_search
                    it.update()
            
            # --- Render Translation Labels if multiple translations active ---
            if len(active_translations) > 1:
                # Primary translation label
                block = doc.findBlock(scene.verse_pos_map[ref])
                rect = layout.blockBoundingRect(block)
                indent = verse_indents.get(ref + "|0" if scene.sentence_break_enabled else ref, verse_indents.get(ref, 0))
                
                # Calculate the exact baseline of the first line of the block
                block_layout = block.layout()
                baseline_y = rect.top()
                if block_layout.lineCount() > 0:
                    first_line = block_layout.lineAt(0)
                    baseline_y += first_line.y() + first_line.ascent()
                else:
                    baseline_y += scene.font_size
                    
                p_label = TranslationIndicatorItem(scene.primary_translation, scene, scene.ref_color)
                p_label.setPos(scene.side_margin + (indent * scene.tab_size) + 28, baseline_y)
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
                    if curr_block.isValid():
                        t_rect = layout.blockBoundingRect(curr_block)
                        t_block_layout = curr_block.layout()
                        t_baseline_y = t_rect.top()
                        if t_block_layout.lineCount() > 0:
                            t_first_line = t_block_layout.lineAt(0)
                            t_baseline_y += t_first_line.y() + t_first_line.ascent()
                        else:
                            t_baseline_y += scene.font_size
                            
                        t_label = TranslationIndicatorItem(tid, scene, QColor(120, 120, 120))
                        t_label.setPos(scene.side_margin + (indent * scene.tab_size) + 28, t_baseline_y)
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
                    if s_ref not in scene.sentence_handle_items:
                        s_pos = scene.verse_pos_map[s_ref]
                        s_block = doc.findBlock(s_pos)
                        s_rect = layout.blockBoundingRect(s_block)
                        s_indent = verse_indents.get(s_ref, 0)
                        
                        # Only show handles if they are on screen
                        if s_rect.top() > scene.scroll_y + scene.view_height + 500 or s_rect.bottom() < scene.scroll_y - 500:
                             s_idx += 1; continue
                             
                        s_item = SentenceHandleItem(ref, s_ref, scene.verse_num_font, scene.ref_color)
                        s_item.setPos(scene.side_margin + (s_indent * scene.tab_size), s_rect.top())
                        s_item.setZValue(9)
                        s_item.clicked.connect(lambda shift, v=s_item: scene._on_verse_num_clicked(v, shift))
                        s_item.dragged.connect(lambda dx, v=s_item: scene.indentation_manager.on_verse_num_dragged(v, dx))
                        s_item.released.connect(scene.indentation_manager.on_verse_num_released)
                        
                        scene.addItem(s_item)
                        scene.sentence_handle_items[s_ref] = s_item
                    else:
                        # Update position if layout changed
                        s_pos = scene.verse_pos_map[s_ref]
                        s_rect = layout.blockBoundingRect(doc.findBlock(s_pos))
                        s_indent = verse_indents.get(s_ref, 0)
                        scene.sentence_handle_items[s_ref].setPos(scene.side_margin + (s_indent * scene.tab_size), s_rect.top())
                    
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
        scene = self.scene
        scene._clear_outline_overlays()
        if not scene.outlines_enabled and not scene.active_outline_id: return
        
        outlines = scene.study_manager.outline_manager.get_outlines()
        if not scene.outlines_enabled and scene.active_outline_id:
            outlines = [o for o in outlines if o["id"] == scene.active_outline_id]
            
        doc = scene.main_text_item.document()
        layout = doc.documentLayout()
        
        def get_verse_y_range(ref, is_end=False):
            import re
            m = re.match(r"(.* \d+:\d+)([a-zA-Z]+)?$", ref)
            if not m: return None, None, None, None
            base_ref = m.group(1)
            letters = m.group(2)

            if base_ref in scene.verse_y_map:
                y_top, y_bottom = scene.verse_y_map[base_ref]
                
                if not letters:
                    visual_top = scene.layout_engine.get_first_verse_y_top(base_ref) if not is_end else y_top
                    return visual_top, y_bottom, None, None
                
                word_idx = scene.loader.letters_to_word_idx(letters)
                v_data = scene.loader.get_verse_by_ref(base_ref)
                if not v_data or word_idx >= len(v_data['tokens']): return y_top, y_bottom, None, None
                
                def get_inline_metrics(v_data, w_index):
                    pos = scene.verse_pos_map[base_ref]
                    w_offset = scene._get_word_offset_in_verse(v_data, w_index)
                    rects = scene._get_text_rects(pos + w_offset, len(v_data['tokens'][w_index][0]))
                    if not rects: return None
                    
                    rct = rects[-1]
                    gap_x = rct.right()
                    
                    if w_index + 1 < len(v_data['tokens']):
                        n_offset = scene._get_word_offset_in_verse(v_data, w_index + 1)
                        if n_offset >= 0:
                            n_rects = scene._get_text_rects(pos + n_offset, len(v_data['tokens'][w_index + 1][0]))
                            if n_rects:
                                n_rct = n_rects[0]
                                if abs(n_rct.center().y() - rct.center().y()) < 5:
                                    gap_x = (rct.right() + n_rct.left()) / 2
                                else:
                                    gap_x += 4
                    else:
                        gap_x += 4
                    
                    pitch = rct.height() * scene.line_spacing
                    top_y = rct.center().y() - pitch / 2
                    bot_y = rct.center().y() + pitch / 2
                    
                    return (gap_x, top_y, bot_y)

                if not is_end:
                    if word_idx > 0:
                        metrics = get_inline_metrics(v_data, word_idx - 1)
                        if metrics:
                            return y_top, y_bottom, metrics, metrics
                else:
                    metrics = get_inline_metrics(v_data, word_idx)
                    if metrics:
                        return y_top, y_bottom, metrics, metrics
                
                return y_top, y_bottom, None, None
            return None, None, None, None

        def get_line_style(level):
            color = QColor("#AAAAAA")
            if level == 0:
                pen = QPen(color, 2)
                return pen, True, None
            elif level == 1:
                pen = QPen(color, 2, Qt.SolidLine)
                return pen, False, None
            elif level == 2:
                pen = QPen(color, 1.5, Qt.CustomDashLine)
                pen.setDashPattern([4, 4])
                return pen, False, None
            elif level == 3:
                pen = QPen(color, 1.5, Qt.CustomDashLine)
                pen.setDashPattern([4, 10, 1, 10])
                return pen, False, None
            elif level == 4:
                pen = QPen(color, 1.5, Qt.CustomDashLine)
                pen.setDashPattern([1, 14])
                return pen, False, level
            else:
                pen = QPen(color, 1, Qt.SolidLine)
                return pen, False, level

        def render_node(node, level=0, is_active=False):
            start_ref = node["range"]["start"]
            end_ref = node["range"]["end"]
            
            node_is_active = is_active or (scene.active_outline_id and node.get("id") == scene.active_outline_id)
            
            s_top, s_bottom, s_inline_top, s_inline_bottom = get_verse_y_range(start_ref, is_end=False)
            e_top, e_bottom, e_inline_top, e_inline_bottom = get_verse_y_range(end_ref, is_end=True)
            
            if s_top is None or e_bottom is None: return

            def draw_divider(y, h_level, summary_node=None, split_parent=None, split_idx=-1, inline_pos=None):
                pen, is_double, text_level = get_line_style(h_level)
                x_end = scene.sceneRect().width() - 10
                
                item = OutlineDividerItem(split_parent, split_idx, y, scene.side_margin, x_end, pen, is_double, text_level=text_level)
                if inline_pos:
                    item.is_inline = True
                    item.inline_x = inline_pos[0]
                    item.inline_y_top = inline_pos[1]
                    item.inline_y_bot = inline_pos[2]
                
                item.setVisible(scene._is_rect_visible(item.boundingRect()))
                if summary_node:
                    tip = f"[{summary_node['title']}]\\n{summary_node.get('summary', '')}"
                    item.setToolTip(tip)
                
                if node_is_active and split_idx != -1:
                    item.dragStarted.connect(scene._start_divider_drag)
                else:
                    item.setCursor(Qt.ArrowCursor)
                
                scene.addItem(item)
                scene.outline_overlay_items.append(item)

            if level == 0:
                draw_divider(s_top, 0, node, split_parent=node, split_idx=-2, inline_pos=s_inline_top)
                draw_divider(e_bottom, 0, node, split_parent=node, split_idx=-3, inline_pos=e_inline_bottom)
            
            if "children" in node:
                children = node["children"]
                child_divider_level = level + 1
                
                for i in range(len(children) - 1):
                    _, child_bottom, _, c_inline_bottom = get_verse_y_range(children[i]["range"]["end"], is_end=True)
                    next_child_top, _, nc_inline_top, _ = get_verse_y_range(children[i+1]["range"]["start"], is_end=False)
                    
                    if child_bottom is not None and next_child_top is not None:
                        inline_pos = c_inline_bottom if c_inline_bottom else nc_inline_top
                        if inline_pos:
                            draw_divider(inline_pos[1], child_divider_level, node, split_parent=node, split_idx=i, inline_pos=inline_pos)
                        else:
                            draw_divider(next_child_top, child_divider_level, node, split_parent=node, split_idx=i)
            
                for child in children:
                    render_node(child, level + 1, node_is_active)
                    
        for outline in outlines:
            render_node(outline)

    def _render_strongs_overlays(self):
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
        
        pen = QPen(QColor(120, 120, 120, 120), 1.5) 
        
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

    def _render_search_overlays(self):
        scene = self.scene
        from src.core.constants import SEARCH_HIGHLIGHT_COLOR
        for it in scene.search_overlay_items: scene.removeItem(it)
        scene.search_overlay_items.clear()
        
        # We only draw overlays for chapter and book headings here.
        # Verse number highlights are handled intrinsically by VerseNumberItem in their own paint methods.
        search_matches = getattr(scene, 'search_heading_matches', set())
        if not search_matches: return
        
        for h_rect, h_type, h_text in scene.heading_rects:
            if (h_type, h_text) in search_matches:
                hl = QGraphicsRectItem(h_rect)
                hl.setBrush(QBrush(SEARCH_HIGHLIGHT_COLOR))
                hl.setPen(Qt.NoPen)
                hl.setZValue(-1)
                hl.setAcceptedMouseButtons(Qt.NoButton)
                hl.setVisible(scene._is_rect_visible(h_rect))
                scene.addItem(hl)
                scene.search_overlay_items.append(hl)
