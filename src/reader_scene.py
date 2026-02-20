from PySide6.QtWidgets import (
    QGraphicsScene, QGraphicsPixmapItem, QGraphicsRectItem, QDialog, 
    QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsItem
)
from PySide6.QtCore import Qt, QRectF, QTimer, Signal, QPointF
from PySide6.QtGui import (
    QColor, QFont, QPixmap, QBrush, QPen, QTextCursor, QCursor,
    QTextBlockFormat, QTextCharFormat
)
from src.verse_loader import VerseLoader
from src.study_manager import StudyManager
from src.mark_popup import MarkPopup
from src.note_editor import NoteEditor
from src.symbol_manager import SymbolManager
from src.reader_items import NoFocusTextItem, NoteIcon, ArrowItem
from src.reader_utils import (
    get_ref_from_pos, get_word_idx_from_pos, get_text_rects, 
    get_word_offset_in_verse
)
from src.constants import (
    APP_BACKGROUND_COLOR, TEXT_COLOR, REFERENCE_COLOR,
    DEFAULT_FONT_FAMILY, VERSE_FONT_FAMILY, DEFAULT_FONT_SIZE, 
    HEADER_FONT_SIZE, CHAPTER_FONT_SIZE,
    LINE_SPACING_DEFAULT, SCROLL_SENSITIVITY, SIDE_MARGIN, TOP_MARGIN,
    LAYOUT_DEBOUNCE_INTERVAL, SEARCH_HIGHLIGHT_COLOR, SELECTION_COLOR,
    BIBLE_SECTIONS
)
import bisect
import os
import math
import time

class ReaderScene(QGraphicsScene):
    """
    The main rendering engine for the Bible reader.
    Uses a single unified QTextDocument for seamless multi-verse selection.
    """
    scrollChanged = Signal(int)
    layoutChanged = Signal(int)
    currentReferenceChanged = Signal(str)
    settingsPreview = Signal(int, float)
    layoutStarted = Signal()
    layoutFinished = Signal()
    searchResultsFound = Signal(int)
    searchStatusUpdated = Signal(int, int) # current_idx, total
    sectionsUpdated = Signal(list, int) # section_data, total_height
    bookmarksUpdated = Signal()
    studyDataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scroll_y = 0.0
        self.target_scroll_y = 0.0
        self.font_size = DEFAULT_FONT_SIZE
        self.line_spacing = LINE_SPACING_DEFAULT
        self.scroll_sens = SCROLL_SENSITIVITY
        self.last_emitted_ref = ""
        
        self.loader = VerseLoader()
        self.study_manager = StudyManager()
        self.symbol_manager = SymbolManager()
        self.pixmap_cache = {} # Cache for symbol pixmaps
        
        # Unified Text Item
        self.main_text_item = NoFocusTextItem()
        self.main_text_item.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.addItem(self.main_text_item)
        
        # Popups
        self.mark_popup = MarkPopup()
        self.mark_popup.markSelected.connect(self._on_mark_selected)
        self.mark_popup.addNoteRequested.connect(self._on_add_note_requested)
        self.mark_popup.addBookmarkRequested.connect(self._on_add_bookmark_requested)
        self.current_selection = None
        
        # Layout & Search State
        self.verse_pos_map = {}
        self.pos_verse_map = []
        self.search_results = []
        self.search_marks_y = [] 
        self.current_search_idx = -1
        self.open_editors = {} # {note_key: editor_instance}
        self.flash_items = []  # [[item, opacity]]
        
        self.study_overlay_items = [] 
        self.search_overlay_items = []
        
        # Arrow Drawing State
        self.is_drawing_arrow = False
        self.arrow_start_key = None
        self.arrow_start_center = None
        self.temp_arrow_item = None
        
        # Timer Management
        self._init_timers()
        
        # Appearance Initialization
        self._update_fonts()
        self.text_color = TEXT_COLOR
        self.ref_color = REFERENCE_COLOR
        self.setBackgroundBrush(APP_BACKGROUND_COLOR)
        
        self.last_width = 800
        self.view_height = 600
        self.total_height = 0

    def _init_timers(self):
        """Initializes all scene timers with their default settings."""
        self.flash_timer = QTimer(self)
        self.flash_timer.setInterval(50)
        self.flash_timer.timeout.connect(self._update_flash_fade)
        
        self.layout_timer = QTimer(self)
        self.layout_timer.setSingleShot(True)
        self.layout_timer.setInterval(LAYOUT_DEBOUNCE_INTERVAL)
        self.layout_timer.timeout.connect(self.apply_layout_changes)
        
        self.scroll_timer = QTimer(self)
        self.scroll_timer.setInterval(16)
        self.scroll_timer.timeout.connect(self.update_scroll_step)
        
        self.visibility_timer = QTimer(self)
        self.visibility_timer.setSingleShot(True)
        self.visibility_timer.setInterval(100)
        self.visibility_timer.timeout.connect(self._update_item_visibility)

    def _update_fonts(self):
        """Updates the internal font objects based on current size settings."""
        self.font = QFont(VERSE_FONT_FAMILY, self.font_size)
        self.header_font = QFont(DEFAULT_FONT_FAMILY, HEADER_FONT_SIZE, QFont.Bold)
        self.chapter_font = QFont(DEFAULT_FONT_FAMILY, CHAPTER_FONT_SIZE, QFont.Bold)

    def _is_rect_visible(self, r):
        # Slightly larger buffer to prevent flickering
        buffer = 150
        return not (r.bottom() < self.scroll_y - buffer or r.top() > self.scroll_y + self.view_height + buffer)

    def _update_item_visibility(self):
        """Updates the visible state of all study and search items based on scroll."""
        for item in self.study_overlay_items + self.search_overlay_items:
            item.setVisible(self._is_rect_visible(item.sceneBoundingRect()))

    def _get_ref_from_pos(self, pos):
        return get_ref_from_pos(pos, self.pos_verse_map)

    def _get_text_rects(self, start, length):
        return get_text_rects(self.main_text_item, start, length)

    def _get_word_offset_in_verse(self, verse_data, word_idx):
        return get_word_offset_in_verse(verse_data, word_idx)

    def _get_word_idx_from_pos(self, verse_data, pos):
        return get_word_idx_from_pos(verse_data, pos)

    def calculate_section_positions(self):
        """Calculates Y-ranges for bible sections based on current layout."""
        doc = self.main_text_item.document()
        layout = doc.documentLayout()
        self.total_height = layout.documentSize().height() + 200

        if not self.verse_pos_map:
            return
            
        section_data = []
        
        for section in BIBLE_SECTIONS:
            # Find start position of first book in section
            first_book = section["books"][0]
            last_book = section["books"][-1]
            
            y_start = 0
            y_end = 0
            
            # Start of section
            ref_start = f"{first_book} 1:1"
            if ref_start in self.verse_pos_map:
                pos = self.verse_pos_map[ref_start]
                y_start = layout.blockBoundingRect(doc.findBlock(pos)).top()
            
            # End of section (last verse of last book)
            # Find the very last verse of the last book
            last_verse_ref = None
            for ref in reversed(list(self.verse_pos_map.keys())):
                if ref.startswith(f"{last_book} "):
                    last_verse_ref = ref
                    break
            
            if last_verse_ref:
                pos = self.verse_pos_map[last_verse_ref]
                y_end = layout.blockBoundingRect(doc.findBlock(pos)).bottom()
            else:
                # Fallback to next section's start or end of doc
                y_end = y_start + 100 
                
            section_data.append({
                "name": section["name"],
                "y_start": y_start,
                "y_end": y_end,
                "color": section["color"]
            })
            
        self.sectionsUpdated.emit(section_data, int(self.total_height))

    def recalculate_layout(self, width: float) -> None:
        """Builds a single QTextDocument containing all loaded Bible text."""
        if width <= 0: return
        self.layoutStarted.emit()
        
        self.verse_pos_map.clear()
        self.pos_verse_map.clear()
        
        doc = self.main_text_item.document()
        doc.clear()
        doc.setDocumentMargin(SIDE_MARGIN)
        
        doc.setTextWidth(width)
        self.main_text_item.setTextWidth(width)

        cursor = QTextCursor(doc)
        last_book, last_chap = None, None
        
        header_fmt = QTextBlockFormat()
        header_fmt.setAlignment(Qt.AlignCenter)
        header_fmt.setTopMargin(40); header_fmt.setBottomMargin(20)
        
        chap_fmt = QTextBlockFormat()
        chap_fmt.setAlignment(Qt.AlignCenter)
        chap_fmt.setTopMargin(20); chap_fmt.setBottomMargin(20)
        
        verse_fmt = QTextBlockFormat()
        verse_fmt.setLineHeight(float(self.line_spacing * 100), int(QTextBlockFormat.ProportionalHeight.value))
        verse_fmt.setBottomMargin(self.font_size * 0.5)

        header_char_fmt = QTextCharFormat()
        header_char_fmt.setFont(self.header_font); header_char_fmt.setForeground(self.text_color)
        
        chap_char_fmt = QTextCharFormat()
        chap_char_fmt.setFont(self.chapter_font); chap_char_fmt.setForeground(self.text_color)
        
        verse_char_fmt = QTextCharFormat()
        verse_char_fmt.setFont(self.font); verse_char_fmt.setForeground(self.text_color)
        
        for verse in self.loader.flat_verses:
            if verse['book'] != last_book:
                cursor.insertBlock(header_fmt)
                cursor.setCharFormat(header_char_fmt)
                cursor.insertText(verse['book'])
                last_book, last_chap = verse['book'], None

            if verse['chapter'] != last_chap:
                cursor.insertBlock(chap_fmt)
                cursor.setCharFormat(chap_char_fmt)
                cursor.insertText(f"{verse['book']} {verse['chapter']}")
                last_chap = verse['chapter']
                
            cursor.insertBlock(verse_fmt)
            cursor.setCharFormat(verse_char_fmt)
            self.verse_pos_map[verse['ref']] = cursor.position()
            self.pos_verse_map.append((cursor.position(), verse['ref']))
            cursor.insertText(f"{verse['verse_num']}  {verse['text']}")

        layout = doc.documentLayout()
        doc_height = layout.documentSize().height()
        
        self.total_height = doc_height + 200
        self.layoutChanged.emit(int(self.total_height))
        self.layoutFinished.emit()
        self.calculate_section_positions()

    def render_verses(self) -> None:
        """Updates transient UI elements (like HUD) that depend on scroll position."""
        doc = self.main_text_item.document()
        layout = doc.documentLayout()
        
        pos = layout.hitTest(QPointF(SIDE_MARGIN + 10, self.scroll_y + 100), Qt.FuzzyHit)
        if pos != -1:
            ref = self._get_ref_from_pos(pos)
            if ref and ref != self.last_emitted_ref:
                self.last_emitted_ref = ref
                self.currentReferenceChanged.emit(ref)

    def _render_search_overlays(self):
        for it in self.search_overlay_items: self.removeItem(it)
        self.search_overlay_items.clear()

        for start, length in self.search_results:
            rects = self._get_text_rects(start, length)
            for r in rects:
                hl = QGraphicsRectItem(r)
                hl.setBrush(QBrush(SEARCH_HIGHLIGHT_COLOR))
                hl.setPen(Qt.NoPen); hl.setZValue(-1)
                hl.setAcceptedMouseButtons(Qt.NoButton)
                hl.setVisible(self._is_rect_visible(r))
                self.addItem(hl); self.search_overlay_items.append(hl)

    def _get_word_center(self, key):
        """Returns the scene center point of a word key or None."""
        ref_parts = key.split('|')
        ref = f"{ref_parts[0]} {ref_parts[1]}:{ref_parts[2]}"
        if ref in self.verse_pos_map:
            v_start = self.verse_pos_map[ref]
            verse_data = self.loader.get_verse(ref_parts[0], int(ref_parts[1]), int(ref_parts[2]))
            if verse_data:
                word_idx = int(ref_parts[3])
                if word_idx < len(verse_data['tokens']):
                    start_pos_in_verse = self._get_word_offset_in_verse(verse_data, word_idx)
                    rects = self._get_text_rects(v_start + start_pos_in_verse, len(verse_data['tokens'][word_idx][0]))
                    if rects:
                        return rects[0].center()
        return None

    def _render_study_overlays(self):
        """Main rendering pass for all study data."""
        # Clean up existing items
        for it in self.study_overlay_items:
            if it.scene() == self:
                self.removeItem(it)
        self.study_overlay_items.clear()
        
        # Render each layer
        self._render_marks_layer()
        self._render_symbols_layer()
        self._render_notes_layer()
        self._render_arrows_layer()

    def _render_symbols_layer(self):
        """Renders word-anchored symbols."""
        symbol_opacity = self.symbol_manager.get_opacity()
        for key, symbol_name in self.study_manager.data["symbols"].items():
            ref_parts = key.split('|')
            ref = f"{ref_parts[0]} {ref_parts[1]}:{ref_parts[2]}"
            if ref in self.verse_pos_map:
                v_start = self.verse_pos_map[ref]
                verse_data = self.loader.get_verse(ref_parts[0], int(ref_parts[1]), int(ref_parts[2]))
                if verse_data:
                    start_pos = v_start + self._get_word_offset_in_verse(verse_data, int(ref_parts[3]))
                    rects = self._get_text_rects(start_pos, len(verse_data['tokens'][int(ref_parts[3])][0]))
                    if rects:
                        r = rects[0]
                        pix_item = self._create_symbol_item(symbol_name, r, symbol_opacity)
                        if pix_item:
                            pix_item.setVisible(self._is_rect_visible(r))
                            self.addItem(pix_item)
                            self.study_overlay_items.append(pix_item)

    def _create_symbol_item(self, symbol_name, target_rect, opacity):
        """Creates a cached pixmap item for a symbol."""
        pix_path = self.symbol_manager.get_symbol_path(symbol_name)
        if not os.path.exists(pix_path): return None
        
        target_h = int(target_rect.height() * 1.8)
        cache_key = (symbol_name, target_h)
        
        if cache_key in self.pixmap_cache:
            scaled_pix = self.pixmap_cache[cache_key]
        else:
            orig_pix = QPixmap(pix_path)
            scaled_pix = orig_pix.scaled(target_h, target_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.pixmap_cache[cache_key] = scaled_pix
            
        pix_item = QGraphicsPixmapItem(scaled_pix)
        pix_item.setOpacity(opacity)
        pix_item.setAcceptedMouseButtons(Qt.NoButton)
        pix_item.setZValue(5)
        
        # Center on word
        x_pos = target_rect.left() + (target_rect.width() - scaled_pix.width()) / 2
        y_pos = target_rect.top() + (target_rect.height() - scaled_pix.height()) / 2
        pix_item.setPos(x_pos, y_pos)
        return pix_item

    def _render_arrows_layer(self):
        """Renders arrows between words."""
        for start_key, arrow_list in self.study_manager.data.get("arrows", {}).items():
            start_center = self._get_word_center(start_key)
            if not start_center: continue
            
            for arrow_data in arrow_list:
                end_key = arrow_data.get('end_key')
                if not end_key: continue
                
                end_center = self._get_word_center(end_key)
                if end_center:
                    item = ArrowItem(start_center, end_center, arrow_data['color'])
                    item.setVisible(self._is_rect_visible(QRectF(start_center, end_center).normalized()))
                    self.addItem(item)
                    self.study_overlay_items.append(item)

    def _render_marks_layer(self):
        """Renders highlights and other text markings."""
        for mark in self.study_manager.data["marks"]:
            ref = f"{mark['book']} {mark['chapter']}:{mark['verse_num']}"
            if ref in self.verse_pos_map:
                start_pos = self.verse_pos_map[ref] + mark['start']
                rects = self._get_text_rects(start_pos, mark['length'])
                for r in rects:
                    self._add_mark_rect(r, mark['type'], mark.get('color', 'yellow'))

    def _render_notes_layer(self):
        """Renders note icons."""
        for key in self.study_manager.data["notes"].keys():
            if key.startswith("standalone_"): continue
                
            ref_parts = key.split('|')
            ref = f"{ref_parts[0]} {ref_parts[1]}:{ref_parts[2]}"
            if ref in self.verse_pos_map:
                v_start = self.verse_pos_map[ref]
                verse_data = self.loader.get_verse(ref_parts[0], int(ref_parts[1]), int(ref_parts[2]))
                if verse_data:
                    start_pos = v_start + self._get_word_offset_in_verse(verse_data, int(ref_parts[3]))
                    rects = self._get_text_rects(start_pos, len(verse_data['tokens'][int(ref_parts[3])][0]))
                    if rects:
                        r = rects[0]
                        # Pass 'self' as the scene manager to NoteIcon
                        note_icon = NoteIcon(key, ref, self)
                        note_icon.setPos(r.right() - 5, r.top() - 5)
                        note_icon.setVisible(self._is_rect_visible(r))
                        self.addItem(note_icon)
                        self.study_overlay_items.append(note_icon)

    def open_note_by_key(self, note_key, ref):
        """Opens the note editor for an existing note or focuses it if already open."""
        if note_key in self.open_editors:
            self.open_editors[note_key].activateWindow()
            self.open_editors[note_key].raise_()
            return

        note_data = self.study_manager.data["notes"].get(note_key, "")
        if isinstance(note_data, dict):
            existing_text = note_data.get("text", "")
            existing_title = note_data.get("title", "")
        else:
            existing_text = note_data
            existing_title = ""
            
        editor = NoteEditor(existing_text, ref, initial_title=existing_title)
        editor.jumpRequested.connect(self.jump_to)
        self.open_editors[note_key] = editor
        editor.finished.connect(lambda result: self._on_note_editor_finished(result, editor, note_key))
        editor.show()

    def _on_note_editor_finished(self, result, editor, note_key):
        if note_key in self.open_editors:
            del self.open_editors[note_key]
        if result == QDialog.Accepted:
            if note_key.startswith("standalone_"):
                # Handle standalone note update
                self.study_manager.data["notes"][note_key]["title"] = editor.get_title()
                self.study_manager.data["notes"][note_key]["text"] = editor.get_text()
                self.study_manager.save_study()
            else:
                ref_parts = note_key.split('|')
                self.study_manager.add_note(ref_parts[0], ref_parts[1], ref_parts[2], int(ref_parts[3]), 
                                           editor.get_text(), editor.get_title())
            self._render_study_overlays()
            self.studyDataChanged.emit()
        elif result == NoteEditor.DELETE_CODE:
            self.study_manager.delete_note(note_key)
            self._render_study_overlays()
            self.studyDataChanged.emit()

    def _add_mark_rect(self, r, mark_type, color_val):
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
            item.setVisible(self._is_rect_visible(r))
            self.addItem(item); self.study_overlay_items.append(item)

    def handle_search(self, text: str):
        self.search_results.clear(); self.search_marks_y.clear()
        self.current_search_idx = -1
        if not text: self.searchStatusUpdated.emit(0, 0); self.render_verses(); return
        doc = self.main_text_item.document()
        cursor = doc.find(text)
        while not cursor.isNull():
            start = cursor.selectionStart()
            self.search_results.append((start, cursor.selectionEnd() - start))
            self.search_marks_y.append(doc.documentLayout().blockBoundingRect(cursor.block()).top())
            cursor = doc.find(text, cursor)
        total = len(self.search_results)
        if total > 0:
            self.current_search_idx = 0
            self.scroll_to_current_match()
        self.searchStatusUpdated.emit(self.current_search_idx, total)
        self._render_search_overlays()

    def scroll_to_current_match(self):
        if 0 <= self.current_search_idx < len(self.search_marks_y):
            y = self.search_marks_y[self.current_search_idx]
            self.set_scroll_y(y - 50)
            self.searchStatusUpdated.emit(self.current_search_idx, len(self.search_results))

    def next_match(self):
        if not self.search_results: return
        self.current_search_idx = (self.current_search_idx + 1) % len(self.search_results)
        self.scroll_to_current_match()

    def prev_match(self):
        if not self.search_results: return
        self.current_search_idx = (self.current_search_idx - 1) % len(self.search_results)
        self.scroll_to_current_match()

    def clear_search(self):
        self.search_results.clear(); self.search_marks_y.clear()
        self.current_search_idx = -1
        self.searchStatusUpdated.emit(-1, 0)
        self._render_search_overlays()

    def contextMenuEvent(self, event):
        cursor = self.main_text_item.textCursor()
        if not cursor.hasSelection():
            pos = self.main_text_item.document().documentLayout().hitTest(self.main_text_item.mapFromScene(event.scenePos()), Qt.FuzzyHit)
            if pos != -1:
                cursor.setPosition(pos); cursor.select(QTextCursor.WordUnderCursor); self.main_text_item.setTextCursor(cursor)
        if cursor.hasSelection():
            self.current_selection = (cursor.selectionStart(), cursor.selectionEnd() - cursor.selectionStart())
            view = self.views()[0]; screen_pos = view.viewport().mapToGlobal(view.mapFromScene(event.scenePos()))
            self.mark_popup.show_at(screen_pos); event.accept(); self.render_verses(); return
        super().contextMenuEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() != Qt.LeftButton: return
        cursor = self.main_text_item.textCursor()
        if cursor.hasSelection():
            self.current_selection = (cursor.selectionStart(), cursor.selectionEnd() - cursor.selectionStart())
            view = self.views()[0]; screen_pos = view.viewport().mapToGlobal(view.mapFromScene(event.scenePos()))
            self.mark_popup.show_at(screen_pos)
        else: self.current_selection = None
        self.render_verses()

    def _clear_selection(self):
        """Clears the current text selection and resets state."""
        cursor = self.main_text_item.textCursor()
        cursor.clearSelection()
        self.main_text_item.setTextCursor(cursor)
        self.current_selection = None

    def _on_mark_selected(self, mark_type, color):
        if not self.current_selection: return
        start, length = self.current_selection
        doc = self.main_text_item.document()
        block = doc.findBlock(start)
        
        # Generate a group_id for this specific marking action
        group_id = str(time.time())
        
        while block.isValid() and block.position() < start + length:
            ref = self._get_ref_from_pos(block.position())
            if ref:
                v_start = self.verse_pos_map[ref]
                rel_start = max(0, start - v_start)
                rel_end = min(block.length(), start + length - v_start)
                if rel_start < rel_end: 
                    self._apply_mark_to_verse(ref, rel_start, rel_end - rel_start, mark_type, color, group_id)
            block = block.next()
            
        self._clear_selection()
        self._render_study_overlays()
        self.studyDataChanged.emit()

    def _apply_mark_to_verse(self, ref, rel_start, rel_length, mark_type, color, group_id=None):
        verse_data = next((v for v in self.loader.flat_verses if v['ref'] == ref), None)
        if not verse_data: return
        
        # Save state for undo before any deletion
        if mark_type in ["clear", "clear_symbols", "clear_all"]:
            self.study_manager.save_state()

        modified = False
        if mark_type in ["clear", "clear_all"]:
            old_len = len(self.study_manager.data["marks"])
            self.study_manager.data["marks"] = [m for m in self.study_manager.data["marks"] if not (
                m['book'] == verse_data['book'] and m['chapter'] == verse_data['chapter'] and 
                m['verse_num'] == verse_data['verse_num'] and not (m['start'] + m['length'] <= rel_start or m['start'] >= rel_start + rel_length)
            )]
            if len(self.study_manager.data["marks"]) != old_len:
                modified = True
            
            # Clear Arrows (Now tied to Marks)
            arrow_keys_to_del = []
            for key in self.study_manager.data.get("arrows", {}).keys():
                parts = key.split('|')
                if parts[0] == verse_data['book'] and parts[1] == str(verse_data['chapter']) and parts[2] == str(verse_data['verse_num']):
                    word_idx = int(parts[3])
                    word_pos = self._get_word_offset_in_verse(verse_data, word_idx)
                    if rel_start <= word_pos <= rel_start + rel_length:
                        arrow_keys_to_del.append(key)
            if arrow_keys_to_del:
                for k in arrow_keys_to_del:
                    del self.study_manager.data["arrows"][k]
                modified = True
        
        if mark_type in ["clear_symbols", "clear_all"]:
            keys_to_del = []
            for key in self.study_manager.data["symbols"].keys():
                parts = key.split('|')
                if parts[0] == verse_data['book'] and parts[1] == str(verse_data['chapter']) and parts[2] == str(verse_data['verse_num']):
                    word_idx = int(parts[3])
                    word_pos = self._get_word_offset_in_verse(verse_data, word_idx)
                    if rel_start <= word_pos <= rel_start + rel_length:
                        keys_to_del.append(key)
            if keys_to_del:
                for k in keys_to_del:
                    del self.study_manager.data["symbols"][k]
                modified = True

        if mark_type not in ["clear", "clear_symbols", "clear_all"]:
            self.study_manager.add_mark({
                "type": mark_type, 
                "book": verse_data['book'], 
                "chapter": verse_data['chapter'],
                "verse_num": verse_data['verse_num'], 
                "start": rel_start, 
                "length": rel_length, 
                "color": color,
                "group_id": group_id
            })
            # add_mark already handles saving and rendering is handled by caller
        elif modified:
            self.study_manager.save_study()

    def _on_add_bookmark_requested(self):
        if not self.current_selection: return
        start, _ = self.current_selection
        ref = self._get_ref_from_pos(start)
        if not ref: return
        verse_data = next((v for v in self.loader.flat_verses if v['ref'] == ref), None)
        if verse_data:
            self.study_manager.add_bookmark(verse_data['book'], str(verse_data['chapter']), str(verse_data['verse_num']))
            self._clear_selection()
            self.bookmarksUpdated.emit()

    def _on_add_note_requested(self):
        if not self.current_selection: return
        start, _ = self.current_selection
        ref = self._get_ref_from_pos(start)
        if not ref: return
        verse_data = next((v for v in self.loader.flat_verses if v['ref'] == ref), None)
        word_idx = self._get_word_idx_from_pos(verse_data, start - self.verse_pos_map[ref])
        note_key = f"{verse_data['book']}|{verse_data['chapter']}|{verse_data['verse_num']}|{word_idx}"
        
        # Use the unified open_note_by_key to ensure consistency
        self.open_note_by_key(note_key, ref)
        self._clear_selection()

    def _get_word_key_at_pos(self, scene_pos):
        """Returns the word key (str) at the given scene position, or None."""
        pos = self.main_text_item.document().documentLayout().hitTest(self.main_text_item.mapFromScene(scene_pos), Qt.FuzzyHit)
        if pos != -1:
            ref = self._get_ref_from_pos(pos)
            if ref:
                verse_data = next((v for v in self.loader.flat_verses if v['ref'] == ref), None)
                if verse_data:
                    word_idx = self._get_word_idx_from_pos(verse_data, pos - self.verse_pos_map[ref])
                    if word_idx != -1:
                        # Punctuation check
                        token_text = verse_data['tokens'][word_idx][0]
                        if any(c.isalnum() for c in token_text):
                            return f"{verse_data['book']}|{verse_data['chapter']}|{verse_data['verse_num']}|{word_idx}"
        return None

    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()

        if key == Qt.Key_Z and modifiers == Qt.ControlModifier:
            if self.study_manager.undo():
                self._render_study_overlays()
                self.studyDataChanged.emit()
            return

        if key == Qt.Key_Delete:
            self._handle_delete_key()
            return

        if key == Qt.Key_A and not self.is_drawing_arrow and not event.isAutoRepeat():
            self._start_arrow_drawing()
            return

        if Qt.Key_1 <= key <= Qt.Key_9:
            self._apply_symbol_at_mouse(str(key - Qt.Key_0))
        elif event.text().isdigit() and event.text() != '0':
            self._apply_symbol_at_mouse(event.text())
            
        super().keyPressEvent(event)

    def _handle_delete_key(self):
        """Deletes study items under the mouse cursor."""
        view = self.views()[0]
        mouse_pos = view.mapToScene(view.mapFromGlobal(QCursor.pos()))
        key_str = self._get_word_key_at_pos(mouse_pos)
        if key_str and key_str in self.study_manager.data["symbols"]:
            self.study_manager.save_state()
            del self.study_manager.data["symbols"][key_str]
            self.study_manager.save_study()
            self._render_study_overlays()
            self.studyDataChanged.emit()

    def _start_arrow_drawing(self):
        """Initiates the arrow drawing process."""
        view = self.views()[0]
        mouse_pos = view.mapToScene(view.mapFromGlobal(QCursor.pos()))
        key_at_pos = self._get_word_key_at_pos(mouse_pos)
        if key_at_pos:
            self.arrow_start_key = key_at_pos
            self.arrow_start_center = self._get_word_center(key_at_pos)
            if self.arrow_start_center:
                self.is_drawing_arrow = True
                self._draw_temp_arrow(mouse_pos)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_A and self.is_drawing_arrow and not event.isAutoRepeat():
            self._finish_arrow_drawing()
        super().keyReleaseEvent(event)

    def _finish_arrow_drawing(self):
        """Finalizes the arrow drawing and saves it to study data."""
        view = self.views()[0]
        mouse_pos = view.mapToScene(view.mapFromGlobal(QCursor.pos()))
        end_key = self._get_word_key_at_pos(mouse_pos)
        
        if end_key and end_key != self.arrow_start_key:
            color = QColor("white")
            color.setAlphaF(0.6)
            self.study_manager.add_arrow(self.arrow_start_key, end_key, color.name(QColor.HexArgb))
        
        self.is_drawing_arrow = False
        self.arrow_start_key = None
        self.arrow_start_center = None
        self._clear_temp_arrow()
        self._render_study_overlays()
        self.studyDataChanged.emit()

    def mouseMoveEvent(self, event):
        if self.is_drawing_arrow:
            self._draw_temp_arrow(event.scenePos())
        super().mouseMoveEvent(event)

    def _draw_temp_arrow(self, end_pos):
        """Renders a temporary arrow following the mouse."""
        self._clear_temp_arrow()
        if not self.arrow_start_center: return
        
        color = QColor("white")
        color.setAlphaF(0.5)
        self.temp_arrow_item = ArrowItem(self.arrow_start_center, end_pos, color)
        self.addItem(self.temp_arrow_item)

    def _clear_temp_arrow(self):
        """Removes the temporary drawing arrow."""
        if self.temp_arrow_item:
            self.removeItem(self.temp_arrow_item)
            self.temp_arrow_item = None

    def _apply_symbol_at_mouse(self, number_key):
        """Applies a symbol based on number key binding at current mouse position."""
        symbol_name = self.symbol_manager.get_binding(number_key)
        if not symbol_name: return

        view = self.views()[0]
        mouse_pos = view.mapToScene(view.mapFromGlobal(QCursor.pos()))
        word_key = self._get_word_key_at_pos(mouse_pos)
        
        if word_key:
            parts = word_key.split('|')
            self.study_manager.add_symbol(parts[0], int(parts[1]), int(parts[2]), int(parts[3]), symbol_name)
            self._render_study_overlays()
            self.studyDataChanged.emit()

    def set_scroll_y(self, value: float) -> None:
        self.target_scroll_y = float(value); self.scroll_y = self.target_scroll_y
        super().setSceneRect(QRectF(0, self.scroll_y, self.last_width, self.view_height))
        self.render_verses(); self.scrollChanged.emit(int(self.scroll_y))
        self.visibility_timer.start()

    def setSceneRect(self, *args) -> None:
        if len(args) == 1: rect = args[0]
        else: rect = QRectF(args[0], args[1], args[2], args[3])
        if abs(rect.width() - self.last_width) > 2:
            self.last_width = rect.width(); self.recalculate_layout(self.last_width)
            self._render_study_overlays()
            self._render_search_overlays()
        self.view_height = rect.height()
        super().setSceneRect(QRectF(0, self.scroll_y, self.last_width, self.view_height))
        self.render_verses()

    def wheelEvent(self, event) -> None:
        modifiers = event.modifiers(); delta = event.delta()
        if delta == 0: return
        if modifiers & (Qt.ControlModifier | Qt.AltModifier):
            if modifiers & Qt.ControlModifier: self.target_font_size = max(8, min(72, self.target_font_size + (2 if delta > 0 else -2)))
            elif modifiers & Qt.AltModifier: self.target_line_spacing = max(1.0, min(3.0, self.target_line_spacing + (0.1 if delta > 0 else -0.1)))
            self.settingsPreview.emit(self.target_font_size, self.target_line_spacing); self.layout_timer.start(); event.accept(); return
        move = -(delta / 120.0) * self.scroll_sens
        self.target_scroll_y = max(0, min(self.total_height - self.view_height, self.target_scroll_y + move))
        if not self.scroll_timer.isActive(): self.scroll_timer.start()
        event.accept()

    def apply_layout_changes(self) -> None:
        self.font_size, self.line_spacing = self.target_font_size, self.target_line_spacing
        self._update_fonts()
        self.recalculate_layout(self.last_width)
        super().setSceneRect(QRectF(0, self.scroll_y, self.last_width, self.view_height))
        self._render_study_overlays()
        self._render_search_overlays()
        self.render_verses()
        self.scrollChanged.emit(int(self.scroll_y)); self.layoutFinished.emit()

    def update_scroll_step(self) -> None:
        diff = self.target_scroll_y - self.scroll_y
        if abs(diff) < 1.0: self.scroll_y = self.target_scroll_y; self.scroll_timer.stop()
        else: self.scroll_y += diff * 0.15
        super().setSceneRect(QRectF(0, self.scroll_y, self.last_width, self.view_height))
        self.render_verses(); self.scrollChanged.emit(int(self.scroll_y))
        self.visibility_timer.start()

    def jump_to(self, book: str, chapter: str, verse: str = "1") -> None:
        if verse is None: verse = "1"
        ref = f"{book} {chapter}:{verse}"
        
        target_ref = None
        if ref in self.verse_pos_map:
            target_ref = ref
        else:
            ref_start = f"{book} {chapter}:1"
            if ref_start in self.verse_pos_map:
                target_ref = ref_start
        
        if target_ref:
            pos = self.verse_pos_map[target_ref]
            block = self.main_text_item.document().findBlock(pos)
            y = self.main_text_item.document().documentLayout().blockBoundingRect(block).top()
            self.set_scroll_y(y - 50)
            self.flash_verse(target_ref)

    def flash_verse(self, ref):
        """Creates a temporary highlight that fades away."""
        if ref not in self.verse_pos_map:
            return
            
        pos = self.verse_pos_map[ref]
        # Get length of verse text
        doc = self.main_text_item.document()
        block = doc.findBlock(pos)
        length = block.length()
        
        rects = self._get_text_rects(pos, length)
        for r in rects:
            item = QGraphicsRectItem(r)
            item.setBrush(QBrush(QColor(100, 200, 255, 100))) # Light cyan
            item.setPen(Qt.NoPen)
            item.setZValue(-2) # Behind text
            self.addItem(item)
            self.flash_items.append([item, 1.0])
            
        if not self.flash_timer.isActive():
            self.flash_timer.start()

    def _update_flash_fade(self):
        """Decreases opacity of all flash items."""
        to_remove = []
        for i, (item, opacity) in enumerate(self.flash_items):
            new_opacity = opacity - 0.05
            if new_opacity <= 0:
                self.removeItem(item)
                to_remove.append(i)
            else:
                item.setOpacity(new_opacity)
                self.flash_items[i][1] = new_opacity
                
        # Remove backwards to keep indices valid
        for i in sorted(to_remove, reverse=True):
            self.flash_items.pop(i)
            
        if not self.flash_items:
            self.flash_timer.stop()

