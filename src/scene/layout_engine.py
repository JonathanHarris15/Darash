from PySide6.QtGui import QTextCursor, QTextBlockFormat, QTextCharFormat
from PySide6.QtCore import Qt, QRectF
from src.core.constants import BIBLE_SECTIONS

class LayoutEngine:
    def __init__(self, scene):
        self.scene = scene

    def recalculate_layout(self, width: float):
        scene = self.scene
        if width <= 0: return
        scene.layoutStarted.emit()
        
        scene.verse_pos_map.clear()
        scene.pos_verse_map.clear()
        
        # Clear old verse number items
        for it in scene.verse_number_items.values():
            scene.removeItem(it)
        scene.verse_number_items.clear()
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

        for verse in scene.loader.flat_verses:
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
                
            indent_level = verse_indents.get(verse['ref'], 0)
            
            verse_fmt = QTextBlockFormat()
            verse_fmt.setLineHeight(float(scene.line_spacing * 100), int(QTextBlockFormat.ProportionalHeight.value))
            verse_fmt.setBottomMargin(scene.font_size * 0.5)
            verse_fmt.setLeftMargin(indent_level * scene.tab_size)
            verse_fmt.setTextIndent(30)
            
            cursor.insertBlock(verse_fmt)
            cursor.setCharFormat(verse_char_fmt)
            scene.verse_pos_map[verse['ref']] = cursor.position()
            scene.pos_verse_map.append((cursor.position(), verse['ref']))
            
            cursor.insertText(verse['text'])

        cursor.endEditBlock()

        scene.total_height = layout.documentSize().height() + 200
        self._update_heading_rects()
        
        scene.layoutChanged.emit(int(scene.total_height))
        scene.layoutFinished.emit()
        self.calculate_section_positions()
        scene.render_verses()
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
        doc = scene.main_text_item.document()
        layout = doc.documentLayout()
        scene.total_height = layout.documentSize().height() + 200

        if not scene.verse_pos_map:
            return
            
        section_data = []
        
        for section in BIBLE_SECTIONS:
            first_book = section["books"][0]
            last_book = section["books"][-1]
            
            y_start = 0
            y_end = 0
            
            ref_start = f"{first_book} 1:1"
            if ref_start in scene.verse_pos_map:
                pos = scene.verse_pos_map[ref_start]
                y_start = layout.blockBoundingRect(doc.findBlock(pos)).top()
            
            last_verse_ref = None
            for ref in reversed(list(scene.verse_pos_map.keys())):
                if ref.startswith(f"{last_book} "):
                    last_verse_ref = ref
                    break
            
            if last_verse_ref:
                pos = scene.verse_pos_map[last_verse_ref]
                y_end = layout.blockBoundingRect(doc.findBlock(pos)).bottom()
            else:
                y_end = y_start + 100 
                
            section_data.append({
                "name": section["name"],
                "y_start": y_start,
                "y_end": y_end,
                "color": section["color"]
            })
            
        scene.sectionsUpdated.emit(section_data, int(scene.total_height))
