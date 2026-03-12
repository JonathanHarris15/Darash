from PySide6.QtGui import QTextCursor, QTextBlockFormat, QTextCharFormat, QFont, QColor
from PySide6.QtCore import Qt, QRectF, QPointF
import re
from src.core.constants import BIBLE_SECTIONS, VERSE_NUMBER_RESERVED_WIDTH

class LayoutEngine:
    def __init__(self, scene):
        self.scene = scene
        self._layout_in_progress = False

    def recalculate_layout(self, width: float, center_verse_idx: int = None):
        scene = self.scene
        if width <= 0: return
        
        # Guard against re-entrant calls (e.g. from cascading resize events)
        if self._layout_in_progress:
            return
        
        self._layout_in_progress = True
        scene.layoutStarted.emit()
        
        try:
            self._prepare_chunk_range(center_verse_idx)
            self._clear_layout_state()
            
            doc = scene.main_text_item.document()
            doc.clear()
            doc.setDocumentMargin(scene.side_margin)
            doc.setTextWidth(width)
            scene.main_text_item.setTextWidth(width)

            cursor = QTextCursor(doc)
            cursor.beginEditBlock()
            
            self._render_chunk_verses(cursor, width)

            cursor.endEditBlock()
            
            self._calculate_verse_boundaries(doc)

            scene.total_height = doc.documentLayout().documentSize().height() + 200
            self._update_heading_rects()
            
            scene.layoutChanged.emit(len(scene.loader.flat_verses)) 
            self.calculate_section_positions()
            scene.render_verses()
            scene._render_search_overlays()
            scene.layout_version += 1
        finally:
            self._layout_in_progress = False
            scene.layoutFinished.emit()

    def _prepare_chunk_range(self, center_verse_idx):
        scene = self.scene
        if center_verse_idx is None:
            center_verse_idx = int(scene.virtual_scroll_y)
            
        total_verses = len(scene.loader.flat_verses)
        half_chunk = scene.CHUNK_SIZE // 2
        
        start_idx = max(0, center_verse_idx - half_chunk)
        end_idx = min(total_verses, start_idx + scene.CHUNK_SIZE)
        
        if end_idx == total_verses:
            start_idx = max(0, end_idx - scene.CHUNK_SIZE)
            
        scene.chunk_start_idx = start_idx
        scene.chunk_end_idx = end_idx

    def _clear_layout_state(self):
        scene = self.scene
        scene.verse_pos_map.clear()
        scene.verse_y_map.clear()
        scene.pos_verse_map.clear()
        scene.verse_stack_end_pos = {}
        
        for it in scene.verse_number_items.values():
            scene.removeItem(it)
        scene.verse_number_items.clear()
        
        for it in scene.sentence_handle_items.values():
            scene.removeItem(it)
        scene.sentence_handle_items.clear()
        
        scene.selected_verse_items.clear()
        scene.last_clicked_verse_idx = -1

    def _render_chunk_verses(self, cursor, width):
        scene = self.scene
        last_book, last_chap = None, None
        
        # Setup Formats
        header_fmt = QTextBlockFormat()
        header_fmt.setAlignment(Qt.AlignCenter)
        header_fmt.setTopMargin(40); header_fmt.setBottomMargin(20)
        
        chap_fmt = QTextBlockFormat()
        chap_fmt.setAlignment(Qt.AlignCenter)
        chap_fmt.setTopMargin(20); chap_fmt.setBottomMargin(20)
        
        header_char_fmt = QTextCharFormat()
        header_char_fmt.setFont(scene.header_font); header_char_fmt.setForeground(scene.text_color)
        
        chap_char_fmt = QTextCharFormat()
        chap_char_fmt.setFont(scene.chapter_font); chap_char_fmt.setForeground(scene.text_color)
        
        verse_char_fmt = QTextCharFormat()
        verse_char_fmt.setFont(scene.font); verse_char_fmt.setForeground(scene.text_color)
        
        interlinear_char_fmt = QTextCharFormat()
        interlinear_char_fmt.setFont(QFont(scene.font_family, scene.font_size))
        interlinear_char_fmt.setForeground(QColor(150, 150, 150))

        verse_indents = scene.study_manager.data.get("verse_indent", {})
        scene.last_width = width
        scene.heading_rects = []
        scene._pending_headings = []

        chunk_verses = scene.loader.flat_verses[scene.chunk_start_idx:scene.chunk_end_idx]
        active_translations = [scene.primary_translation] + scene.enabled_interlinear
        
        current_multi_data = {}
        last_fetched_chap = (None, None)

        for i, verse in enumerate(chunk_verses):
            book, chap = verse['book'], verse['chapter']
            if (book, chap) != last_fetched_chap:
                current_multi_data = scene.loader.load_chapter_multi(book, int(chap), active_translations)
                last_fetched_chap = (book, chap)

            if book != last_book:
                cursor.insertBlock(header_fmt)
                cursor.setCharFormat(header_char_fmt)
                cursor.insertText(book)
                scene._pending_headings.append((cursor.block().blockNumber(), "book", book))
                last_book, last_chap = book, None

            if chap != last_chap:
                cursor.insertBlock(chap_fmt)
                cursor.setCharFormat(chap_char_fmt)
                cursor.insertText(f"{book} {chap}")
                scene._pending_headings.append((cursor.block().blockNumber(), "chapter", f"{book} {chap}"))
                last_chap = chap
                
            v_num = verse['verse_num']
            verse_multi = current_multi_data.get(v_num, {})
            
            for tid in active_translations:
                v_data = verse_multi.get(tid)
                if not v_data: continue
                
                is_primary = (tid == scene.primary_translation)
                v_text = v_data['text']
                
                if scene.sentence_break_enabled and is_primary:
                    sentences = [s.strip() for s in re.split(r'(?<=[.!?])[\s\u00A0]+', v_text) if s.strip()]
                else:
                    sentences = [v_text]
                    
                for s_idx, s_text in enumerate(sentences):
                    s_ref = f"{verse['ref']}|{s_idx}" if (scene.sentence_break_enabled and is_primary) else verse['ref']
                    if not is_primary:
                        lookup_ref = f"{verse['ref']}|0" if scene.sentence_break_enabled else verse['ref']
                        indent_level = verse_indents.get(lookup_ref, verse_indents.get(verse['ref'], 0))
                    else:
                        indent_level = verse_indents.get(s_ref, verse_indents.get(verse['ref'], 0))
                    
                    block_fmt = QTextBlockFormat()
                    is_last_in_verse = (tid == active_translations[-1])
                    block_fmt.setLineHeight(float(scene.line_spacing * 100), int(QTextBlockFormat.ProportionalHeight.value))
                    
                    if is_primary:
                        if len(active_translations) == 1:
                            block_fmt.setBottomMargin(scene.font_size * 0.5 if s_idx == len(sentences) - 1 else 2)
                        else:
                            block_fmt.setBottomMargin(2)
                        cursor.setCharFormat(verse_char_fmt)
                    else:
                        if is_last_in_verse:
                            block_fmt.setBottomMargin(scene.font_size * 1.5)
                        else:
                            block_fmt.setBottomMargin(1)
                        cursor.setCharFormat(interlinear_char_fmt)
                    
                    block_fmt.setLeftMargin(indent_level * scene.tab_size + VERSE_NUMBER_RESERVED_WIDTH)
                    cursor.insertBlock(block_fmt)
                    
                    if is_primary:
                        if s_idx == 0:
                            scene.verse_pos_map[verse['ref']] = cursor.position()
                            scene.pos_verse_map.append((cursor.position(), verse['ref']))
                        scene.verse_pos_map[s_ref] = cursor.position()
                    
                    scene.verse_stack_end_pos[verse['ref']] = cursor.position()
                    cursor.insertText(s_text)

    def _calculate_verse_boundaries(self, doc):
        scene = self.scene
        layout = doc.documentLayout()
        chunk_verses = scene.loader.flat_verses[scene.chunk_start_idx:scene.chunk_end_idx]
        
        for i, verse in enumerate(chunk_verses):
            ref = verse['ref']
            if ref not in scene.verse_pos_map:
                y_top = 0.0 if i == 0 else scene.verse_y_map.get(chunk_verses[i-1]['ref'], (0.0, 0.0))[1]
                scene.verse_y_map[ref] = (y_top, y_top)
                continue

            if scene.sentence_break_enabled:
                s_idx = 0
                while True:
                    s_ref = f"{ref}|{s_idx}"
                    if s_ref not in scene.verse_pos_map: break
                    
                    pos = scene.verse_pos_map[s_ref]
                    block = doc.findBlock(pos)
                    rect = layout.blockBoundingRect(block)
                    
                    if s_idx == 0:
                        y_top = 0.0 if i == 0 else scene.verse_y_map[chunk_verses[i-1]['ref']][1]
                    else:
                        y_top = scene.verse_y_map[f"{ref}|{s_idx-1}"][1]

                    next_block = block.next()
                    if i == len(chunk_verses) - 1 and not next_block.isValid():
                        y_bottom = layout.documentSize().height()
                    else:
                        y_bottom = (rect.bottom() + layout.blockBoundingRect(next_block).top()) / 2 if next_block.isValid() else rect.bottom()

                    scene.verse_y_map[s_ref] = (y_top, y_bottom)
                    s_idx += 1
                
                first_s = f"{ref}|0"
                y_top = scene.verse_y_map[first_s][0]
                last_pos = scene.verse_stack_end_pos.get(ref, scene.verse_pos_map[first_s])
                last_block = doc.findBlock(last_pos)
                last_rect = layout.blockBoundingRect(last_block)
                next_block = last_block.next()
                if i == len(chunk_verses) - 1 and not next_block.isValid():
                    y_bottom = layout.documentSize().height()
                else:
                    y_bottom = (last_rect.bottom() + layout.blockBoundingRect(next_block).top()) / 2 if next_block.isValid() else last_rect.bottom()
                scene.verse_y_map[ref] = (y_top, y_bottom)
            else:
                pos = scene.verse_pos_map[ref]
                block = doc.findBlock(pos)
                last_pos = scene.verse_stack_end_pos.get(ref, pos)
                last_block = doc.findBlock(last_pos)
                last_rect = layout.blockBoundingRect(last_block)
                
                y_top = 0.0 if i == 0 else scene.verse_y_map[chunk_verses[i-1]['ref']][1]
                if i == len(chunk_verses) - 1:
                    y_bottom = layout.documentSize().height()
                else:
                    next_block = last_block.next()
                    y_bottom = (last_rect.bottom() + layout.blockBoundingRect(next_block).top()) / 2 if next_block.isValid() else last_rect.bottom()

                scene.verse_y_map[ref] = (y_top, y_bottom)

    def _update_heading_rects(self):
        scene = self.scene
        scene.heading_rects = []
        doc = scene.main_text_item.document()
        layout = doc.documentLayout()
        
        for block_num, h_type, h_text in scene._pending_headings:
            block = doc.findBlockByNumber(block_num)
            if block.isValid():
                block_height = block.layout().boundingRect().height()
                if block_height <= 0:
                    font = scene.header_font if h_type == "book" else scene.chapter_font
                    block_height = font.pointSize() * 2.0
                
                block_rect = layout.blockBoundingRect(block)
                full_width_rect = QRectF(0, block_rect.y(), scene.last_width, block_height)
                scene.heading_rects.append((full_width_rect, h_type, h_text))

    def calculate_section_positions(self):
        scene = self.scene
        total_verses = len(scene.loader.flat_verses)
        if total_verses == 0: return
        
        section_data = []
        for section in BIBLE_SECTIONS:
            first_book = section["books"][0]
            last_book = section["books"][-1]
            
            # Find index of first verse of first book
            idx_start = scene.loader.get_verse_index(f"{first_book} 1:1")
            if idx_start < 0: idx_start = 0
            
            # Find index of last verse of last book
            idx_end = idx_start
            for i in range(total_verses - 1, -1, -1):
                if scene.loader.flat_verses[i]['book'] == last_book:
                    idx_end = i
                    break
                    
            section_data.append({
                "name": section["name"],
                "y_start": float(idx_start),
                "y_end": float(idx_end),
                "color": section["color"]
            })
            
        scene.sectionsUpdated.emit(section_data, total_verses)


    def _get_ref_from_pos(self, pos):
        scene = self.scene
        if not scene.pos_verse_map: return None
        import bisect
        idx = bisect.bisect_right(scene.pos_verse_map, (pos, "zzzzzz")) - 1
        return scene.pos_verse_map[idx][1] if idx >= 0 else None

    def _get_text_rects(self, start_pos, length, return_baselines=False):
        scene = self.scene
        doc = scene.main_text_item.document()
        results = []
        
        cur_pos = start_pos
        end_pos = start_pos + length
        
        while cur_pos < end_pos:
            block = doc.findBlock(cur_pos)
            if not block.isValid():
                break
                
            block_layout = block.layout()
            block_pos = block.position()
            rel_pos = cur_pos - block_pos
            
            line = block_layout.lineForTextPosition(rel_pos)
            if not line.isValid():
                cur_pos += 1
                continue
                
            line_end_rel = line.textStart() + line.textLength()
            chunk_end_rel = min(end_pos - block_pos, line_end_rel)
            
            if chunk_end_rel <= rel_pos:
                cur_pos += 1
                continue
                
            x_start, _ = line.cursorToX(rel_pos)
            x_end, _ = line.cursorToX(chunk_end_rel)
            
            block_rect = doc.documentLayout().blockBoundingRect(block)
            doc_x = block_rect.left()
            doc_y = block_rect.top() + line.y()
            
            doc_rect = QRectF(doc_x + x_start, doc_y, x_end - x_start, line.height())
            scene_rect = self.scene.main_text_item.mapToScene(doc_rect).boundingRect()
            
            # Use line.ascent() to find the precise baseline in scene coordinates
            baseline_y = self.scene.main_text_item.mapToScene(QPointF(0, doc_y + line.ascent())).y()
            
            if return_baselines:
                if not results or abs(scene_rect.top() - results[-1][0].top()) > 5:
                    results.append((scene_rect, baseline_y))
                else:
                    results[-1] = (results[-1][0].united(scene_rect), baseline_y)
            else:
                if not results or abs(scene_rect.top() - results[-1].top()) > 5:
                    results.append(scene_rect)
                else:
                    results[-1] = results[-1].united(scene_rect)
                
            cur_pos = block_pos + chunk_end_rel
            
        return results

    def _get_word_idx_from_pos(self, verse_data, rel_pos):
        # rel_pos here is the character offset relative to the START OF THE VERSE
        # (including any block separators if it spans multiple blocks).
        # However, QTextDocument.hitTest returns document-absolute positions.
        # This function is used by _get_word_key_at_pos where rel_pos = pos - v_start.
        accum = 0
        for i, token in enumerate(verse_data['tokens']):
            word = token[0]
            if rel_pos >= accum and rel_pos < accum + len(word):
                return i
            accum += len(word) + 1
        return -1

    def _get_word_document_pos(self, ref, word_idx):
        """Returns the document-absolute position of a word using QTextCursor word iteration."""
        scene = self.scene
        v_start = scene.verse_pos_map.get(ref)
        if v_start is None: return -1
        
        doc = scene.main_text_item.document()
        cursor = QTextCursor(doc)
        cursor.setPosition(v_start)
        
        count = 0
        while count < word_idx:
            # Move to next word start. 
            # Note: doc.findBlock(cursor.position()) tells us if we crossed a block.
            # We skip the space or separator.
            cursor.movePosition(QTextCursor.NextWord)
            if cursor.atEnd() or self._get_ref_from_pos(cursor.position()) != ref:
                return -1
            count += 1
            
        return cursor.position()

    def _get_word_key_at_pos(self, scene_pos):
        scene = self.scene
        doc_pos = scene.main_text_item.mapFromScene(scene_pos)
        pos = scene.main_text_item.document().documentLayout().hitTest(doc_pos, Qt.FuzzyHit)
        if pos == -1: return None
        ref = self._get_ref_from_pos(pos)
        if not ref: return None
        verse_data = scene.loader.get_verse_by_ref(ref)
        if not verse_data: return None
        v_start = scene.verse_pos_map.get(ref)
        if v_start is None: return None
        
        # Reconstruct word index using QTextCursor from v_start
        doc = scene.main_text_item.document()
        cursor = QTextCursor(doc)
        cursor.setPosition(v_start)
        
        word_idx = 0
        while cursor.position() < pos:
            next_cursor = QTextCursor(cursor)
            next_cursor.movePosition(QTextCursor.NextWord)
            if next_cursor.position() > pos or next_cursor.position() <= cursor.position():
                break
            if self._get_ref_from_pos(next_cursor.position()) != ref:
                break
            cursor = next_cursor
            word_idx += 1
            
        return f"{verse_data['book']}|{verse_data['chapter']}|{verse_data['verse_num']}|{word_idx}"

    def _get_strongs_at_pos(self, scene_pos):
        scene = self.scene
        key = self._get_word_key_at_pos(scene_pos)
        if not key: return None, None
        
        ref_parts = key.split('|')
        if len(ref_parts) < 4: return None, key
        
        ref = f"{ref_parts[0]} {ref_parts[1]}:{ref_parts[2]}"
        word_idx = int(ref_parts[3])
        
        verse_data = scene.loader.get_verse_by_ref(ref)
        if not verse_data or word_idx >= len(verse_data['tokens']): return None, key
        
        token = verse_data['tokens'][word_idx]
        if len(token) > 1:
            # Token format is [word, strongs1, strongs2, ...]
            # Return first strongs number
            return token[1], key
            
        return None, key

    def _get_word_rect(self, key):
        scene = self.scene
        if not key: return None
        ref_parts = key.split('|')
        if len(ref_parts) < 4: return None
        ref = f"{ref_parts[0]} {ref_parts[1]}:{ref_parts[2]}"
        
        word_idx = int(ref_parts[3])
        
        word_pos = self._get_word_document_pos(ref, word_idx)
        if word_pos == -1: return None
        
        verse_data = scene.loader.get_verse_by_ref(ref)
        if not verse_data or word_idx >= len(verse_data['tokens']): return None
        token = verse_data['tokens'][word_idx][0]
        
        rects = self._get_text_rects(word_pos, len(token))
        return rects[0] if rects else None

    def _get_word_center(self, key):
        rect = self._get_word_rect(key)
        return rect.center() if rect else None

    def _get_word_offset_in_verse(self, verse_data, word_idx):
        offset = 0
        for i in range(word_idx):
            offset += len(verse_data['tokens'][i][0]) + 1
        return offset

    def get_sentence_ref_at_pos(self, scene_pos):
        scene = self.scene
        doc_pos = scene.main_text_item.mapFromScene(scene_pos)
        pos = scene.main_text_item.document().documentLayout().hitTest(doc_pos, Qt.FuzzyHit)
        if pos == -1: return None
        
        ref = self._get_ref_from_pos(pos)
        if not ref: return None
        if not scene.sentence_break_enabled: return ref
        
        block = scene.main_text_item.document().findBlock(pos)
        block_pos = block.position()
        
        for s_ref, s_pos in scene.verse_pos_map.items():
            if s_pos == block_pos and s_ref.startswith(ref + "|"):
                return s_ref
        
        return ref + "|0"

    def get_verse_y_midpoint(self, ref_before, ref_after):
        scene = self.scene
        if ref_before in scene.verse_y_map:
            return scene.verse_y_map[ref_before][1]
        return 0

    def get_first_verse_y_top(self, ref):
        scene = self.scene
        if ref not in scene.verse_pos_map: return 0
        doc = scene.main_text_item.document()
        layout = doc.documentLayout()
        block = doc.findBlock(scene.verse_pos_map[ref])
        prev = block.previous()
        rect = layout.blockBoundingRect(block)
        return (layout.blockBoundingRect(prev).bottom() + rect.top()) / 2 if prev.isValid() else rect.top() - 5
