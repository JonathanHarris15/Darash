from PySide6.QtGui import QTextCursor, QTextBlockFormat, QTextCharFormat
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

        chunk_verses = scene.loader.flat_verses[start_idx:end_idx]
        
        for i, verse in enumerate(chunk_verses):
            if verse['book'] != last_book:
                cursor.insertBlock(header_fmt)
                cursor.setCharFormat(header_char_fmt)
                cursor.insertText(verse['book'])
                scene._pending_headings.append((cursor.block().blockNumber(), "book", verse['book']))
                last_book, last_chap = verse['book'], None

            if verse['chapter'] != last_chap:
                cursor.insertBlock(chap_fmt)
                cursor.setCharFormat(chap_char_fmt)
                cursor.insertText(f"{verse['book']} {verse['chapter']}")
                scene._pending_headings.append((cursor.block().blockNumber(), "chapter", f"{verse['book']} {verse['chapter']}"))
                last_chap = verse['chapter']
                
            # Split text into sentences if enabled
            if scene.sentence_break_enabled:
                # Split by .!? followed by space or end of string
                # Handles multiple spaces and non-breaking spaces
                sentences = [s.strip() for s in re.split(r'(?<=[.!?])[\s\u00A0]+', verse['text']) if s.strip()]
            else:
                sentences = [verse['text']]
                
            for s_idx, s_text in enumerate(sentences):
                # Use sub-reference for sentence-level indentation
                s_ref = f"{verse['ref']}|{s_idx}" if scene.sentence_break_enabled else verse['ref']
                indent_level = verse_indents.get(s_ref, verse_indents.get(verse['ref'], 0))
                
                verse_fmt = QTextBlockFormat()
                verse_fmt.setLineHeight(float(scene.line_spacing * 100), int(QTextBlockFormat.ProportionalHeight.value))
                verse_fmt.setBottomMargin(scene.font_size * 0.5 if s_idx == len(sentences) - 1 else 2)
                verse_fmt.setLeftMargin(indent_level * scene.tab_size + VERSE_NUMBER_RESERVED_WIDTH)
                
                cursor.insertBlock(verse_fmt)
                cursor.setCharFormat(verse_char_fmt)
                
                # Only map the start of the verse for global navigation
                if s_idx == 0:
                    scene.verse_pos_map[verse['ref']] = cursor.position()
                    scene.pos_verse_map.append((cursor.position(), verse['ref']))
                
                # Store position for each sentence if needed for indentation dragging
                scene.verse_pos_map[s_ref] = cursor.position()
                
                cursor.insertText(s_text)

        cursor.endEditBlock()
        
        # Now that layout is fixed, calculate y-boundaries for each verse/sentence
        for i, verse in enumerate(chunk_verses):
            ref = verse['ref']
            
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
                        # For internal sentences, we use the block's bottom
                        # unless it's the last sentence of a verse, then we might want to include headers?
                        # No, the NEXT verse's first sentence will own the headers above it via the 'y_top' logic.
                        y_bottom = rect.bottom()

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
                
                # Simplified boundary logic: Each verse owns the space from the 
                # bottom of the previous verse to its own bottom.
                if i == 0:
                    y_top = 0.0
                else:
                    prev_ref = chunk_verses[i-1]['ref']
                    y_top = layout.blockBoundingRect(doc.findBlock(scene.verse_pos_map[prev_ref])).bottom()

                if i == len(chunk_verses) - 1:
                    y_bottom = layout.documentSize().height()
                else:
                    y_bottom = rect.bottom()

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
