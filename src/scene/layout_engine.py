from PySide6.QtGui import QTextCursor, QTextBlockFormat, QTextCharFormat, QFont, QColor
from PySide6.QtCore import Qt, QRectF
import re
from src.core.constants import BIBLE_SECTIONS, VERSE_NUMBER_RESERVED_WIDTH

class LayoutEngine:
    def __init__(self, scene):
        self.scene = scene

    def recalculate_layout(self, width: float, center_verse_idx: int = None):
        scene = self.scene
        if width <= 0: return
        scene.layoutStarted.emit()
        
        # Determine chunk range
        if center_verse_idx is None:
            center_verse_idx = int(scene.virtual_scroll_y)
            
        total_verses = len(scene.loader.flat_verses)
        half_chunk = scene.CHUNK_SIZE // 2
        
        start_idx = max(0, center_verse_idx - half_chunk)
        end_idx = min(total_verses, start_idx + scene.CHUNK_SIZE)
        
        # Adjust start if we hit the end
        if end_idx == total_verses:
            start_idx = max(0, end_idx - scene.CHUNK_SIZE)
            
        scene.chunk_start_idx = start_idx
        scene.chunk_end_idx = end_idx
        
        scene.verse_pos_map.clear()
        scene.verse_y_map.clear()
        scene.pos_verse_map.clear()
        scene.verse_stack_end_pos = {}
        
        # Clear old verse number items
        for it in scene.verse_number_items.values():
            scene.removeItem(it)
        scene.verse_number_items.clear()
        
        for it in scene.sentence_handle_items.values():
            scene.removeItem(it)
        scene.sentence_handle_items.clear()
        
        scene.selected_verse_items.clear()
        scene.last_clicked_verse_idx = -1
        
        doc = scene.main_text_item.document()
        layout = doc.documentLayout()
        doc.clear()
        doc.setDocumentMargin(scene.side_margin)
        
        doc.setTextWidth(width)
        scene.main_text_item.setTextWidth(width)

        cursor = QTextCursor(doc)
        cursor.beginEditBlock()
        
        last_book, last_chap = None, None
        
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
        
        verse_indents = scene.study_manager.data.get("verse_indent", {})

        # Clear previous heading data
        scene.last_width = width
        scene.heading_rects = []
        scene._pending_headings = []

        # Prepare formatting for secondary translations
        interlinear_fmt = QTextBlockFormat()
        interlinear_fmt.setLineHeight(float(scene.line_spacing * 100), int(QTextBlockFormat.ProportionalHeight.value))
        interlinear_fmt.setBottomMargin(2)
        
        interlinear_char_fmt = QTextCharFormat()
        interlinear_char_fmt.setFont(QFont(scene.font_family, scene.font_size))
        interlinear_char_fmt.setForeground(QColor(150, 150, 150)) # Dimmed grey

        chunk_verses = scene.loader.flat_verses[start_idx:end_idx]
        active_translations = [scene.primary_translation] + scene.enabled_interlinear
        
        # We need to fetch multi-translation data in chunks per chapter to be efficient
        # But for simplicity in the current loop, we'll fetch per verse if not already cached
        # Better: Group verses by book/chapter and fetch multi-translation data for each chapter block.
        
        current_multi_data = {}
        last_fetched_chap = (None, None)

        for i, verse in enumerate(chunk_verses):
            book, chap = verse['book'], verse['chapter']
            
            # Fetch multi-data if we moved to a new chapter
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
            
            # Render each translation in the stack
            for tid in active_translations:
                v_data = verse_multi.get(tid)
                if not v_data: continue
                
                is_primary = (tid == scene.primary_translation)
                v_text = v_data['text']
                
                # Split text into sentences if enabled (usually only for primary)
                if scene.sentence_break_enabled and is_primary:
                    sentences = [s.strip() for s in re.split(r'(?<=[.!?])[\s\u00A0]+', v_text) if s.strip()]
                else:
                    sentences = [v_text]
                    
                for s_idx, s_text in enumerate(sentences):
                    # Use sub-reference for sentence-level indentation
                    s_ref = f"{verse['ref']}|{s_idx}" if (scene.sentence_break_enabled and is_primary) else verse['ref']
                    
                    # For secondary translations, we should use the indent of the primary verse's first sentence
                    # or the primary verse itself, to keep them "grouped" with the marker.
                    if not is_primary:
                        lookup_ref = f"{verse['ref']}|0" if scene.sentence_break_enabled else verse['ref']
                        indent_level = verse_indents.get(lookup_ref, verse_indents.get(verse['ref'], 0))
                    else:
                        indent_level = verse_indents.get(s_ref, verse_indents.get(verse['ref'], 0))
                    
                    block_fmt = QTextBlockFormat()
                    is_last_in_verse = (tid == active_translations[-1])
                    
                    if is_primary:
                        block_fmt.setLineHeight(float(scene.line_spacing * 100), int(QTextBlockFormat.ProportionalHeight.value))
                        # If primary is the only one, use standard margin.
                        # If more translations exist, use small margin between them.
                        if len(active_translations) == 1:
                            block_fmt.setBottomMargin(scene.font_size * 0.5 if s_idx == len(sentences) - 1 else 2)
                        else:
                            block_fmt.setBottomMargin(2)
                        cursor.setCharFormat(verse_char_fmt)
                    else:
                        block_fmt.setLineHeight(float(scene.line_spacing * 100), int(QTextBlockFormat.ProportionalHeight.value))
                        # Last translation in the stack gets a large margin to separate from next verse
                        if is_last_in_verse:
                            block_fmt.setBottomMargin(scene.font_size * 1.5)
                        else:
                            block_fmt.setBottomMargin(1)
                        cursor.setCharFormat(interlinear_char_fmt)
                    
                    block_fmt.setLeftMargin(indent_level * scene.tab_size + VERSE_NUMBER_RESERVED_WIDTH)
                    
                    cursor.insertBlock(block_fmt)
                    
                    # Only map the primary translation for global navigation & overlays
                    if is_primary:
                        if s_idx == 0:
                            scene.verse_pos_map[verse['ref']] = cursor.position()
                            scene.pos_verse_map.append((cursor.position(), verse['ref']))
                        scene.verse_pos_map[s_ref] = cursor.position()
                    
                    # Track the position of the last block added to this verse stack
                    scene.verse_stack_end_pos[verse['ref']] = cursor.position()
                    
                    cursor.insertText(s_text)

        cursor.endEditBlock()
        
        # Now that layout is fixed, calculate y-boundaries for each verse/sentence
        for i, verse in enumerate(chunk_verses):
            ref = verse['ref']
            
            if ref not in scene.verse_pos_map:
                y_top = 0.0 if i == 0 else scene.verse_y_map.get(chunk_verses[i-1]['ref'], (0.0, 0.0))[1]
                scene.verse_y_map[ref] = (y_top, y_top)
                continue

            if scene.sentence_break_enabled:
                # Iterate through all sentences of this verse
                s_idx = 0
                while True:
                    s_ref = f"{ref}|{s_idx}"
                    if s_ref not in scene.verse_pos_map: break
                    
                    pos = scene.verse_pos_map[s_ref]
                    block = doc.findBlock(pos)
                    rect = layout.blockBoundingRect(block)
                    
                    # Calculate top bound: if first sentence of chunk, own from 0.0
                    if s_idx == 0:
                        if i == 0:
                            y_top = 0.0
                        else:
                            prev_ref = chunk_verses[i-1]['ref']
                            # Link to the bottom of the previous verse
                            y_top = scene.verse_y_map[prev_ref][1]
                    else:
                        prev_s_ref = f"{ref}|{s_idx-1}"
                        y_top = scene.verse_y_map[prev_s_ref][1]

                    # Calculate bottom bound: if last sentence of last verse in chunk, own to end
                    # Use a small peek at the next block if it exists to find the visual gap
                    next_block = block.next()
                    if i == len(chunk_verses) - 1 and next_block.isValid() == False:
                        y_bottom = layout.documentSize().height()
                    else:
                        y_bottom = (rect.bottom() + layout.blockBoundingRect(next_block).top()) / 2

                    scene.verse_y_map[s_ref] = (y_top, y_bottom)
                    s_idx += 1
                
                # Main verse ref spans all its sentences
                first_s = f"{ref}|0"
                last_s = f"{ref}|{s_idx-1}"
                scene.verse_y_map[ref] = (scene.verse_y_map[first_s][0], scene.verse_y_map[last_s][1])
            else:
                pos = scene.verse_pos_map[ref]
                block = doc.findBlock(pos)
                rect = layout.blockBoundingRect(block)
                
                # Bottom should be the bottom of the LAST block in the translation stack
                last_pos = scene.verse_stack_end_pos.get(ref, pos)
                last_block = doc.findBlock(last_pos)
                last_rect = layout.blockBoundingRect(last_block)
                
                # Simplified boundary logic: Each verse owns the space from the 
                # bottom of the previous verse to its own bottom.
                if i == 0:
                    y_top = 0.0
                else:
                    prev_ref = chunk_verses[i-1]['ref']
                    # Previous verse's bottom bound is already calculated
                    y_top = scene.verse_y_map[prev_ref][1]

                if i == len(chunk_verses) - 1:
                    y_bottom = layout.documentSize().height()
                else:
                    next_block = last_block.next()
                    y_bottom = (last_rect.bottom() + layout.blockBoundingRect(next_block).top()) / 2 if next_block.isValid() else last_rect.bottom()

                scene.verse_y_map[ref] = (y_top, y_bottom)

        scene.total_height = layout.documentSize().height() + 200
        self._update_heading_rects()
        
        # Virtual total height is the total number of verses
        scene.layoutChanged.emit(total_verses) 
        scene.layoutFinished.emit()
        self.calculate_section_positions()
        scene.render_verses()
        scene._render_search_overlays()
        scene.layout_version += 1

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
        
        section_data = []
        for section in BIBLE_SECTIONS:
            first_book = section["books"][0]
            last_book = section["books"][-1]
            
            # Find index of first verse of first book
            ref_start = f"{first_book} 1:1"
            idx_start = scene.loader.get_verse_index(ref_start)
            
            # Find index of last verse of last book
            idx_end = idx_start
            # Search backwards for the last verse of last_book
            for i in range(len(scene.loader.flat_verses)-1, -1, -1):
                if scene.loader.flat_verses[i]['book'] == last_book:
                    idx_end = i
                    break
                    
            section_data.append({
                "name": section["name"],
                "y_start": idx_start, # Now represents virtual index
                "y_end": idx_end,
                "color": section["color"]
            })
            
        scene.sectionsUpdated.emit(section_data, total_verses)
