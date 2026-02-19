from PySide6.QtWidgets import (
    QGraphicsScene, QGraphicsTextItem, QGraphicsPixmapItem, 
    QGraphicsRectItem, QDialog, QGraphicsEllipseItem, QGraphicsLineItem,
    QStyle
)
from PySide6.QtCore import Qt, QRectF, QTimer, Signal, QPointF
from PySide6.QtGui import (
    QColor, QFont, QFontMetrics, QTextBlockFormat, QTextCursor, 
    QPixmap, QBrush, QPen, QAbstractTextDocumentLayout, QTextCharFormat,
    QCursor
)
from src.verse_loader import VerseLoader
from src.study_manager import StudyManager
from src.mark_popup import MarkPopup
from src.note_editor import NoteEditor
from src.symbol_manager import SymbolManager
from src.constants import (
    APP_BACKGROUND_COLOR, TEXT_COLOR, REFERENCE_COLOR,
    DEFAULT_FONT_FAMILY, VERSE_FONT_FAMILY, DEFAULT_FONT_SIZE, 
    HEADER_FONT_SIZE, CHAPTER_FONT_SIZE,
    LINE_SPACING_DEFAULT, SCROLL_SENSITIVITY, SIDE_MARGIN, TOP_MARGIN,
    LAYOUT_DEBOUNCE_INTERVAL, SEARCH_HIGHLIGHT_COLOR, SELECTION_COLOR
)
import bisect
import re
import os
import math

class NoFocusTextItem(QGraphicsTextItem):
    """Custom QGraphicsTextItem that doesn't draw a dashed focus rectangle."""
    def paint(self, painter, option, widget=None):
        # Remove the focus state from the option before painting
        if option.state & QStyle.State_HasFocus:
            option.state &= ~QStyle.State_HasFocus
        super().paint(painter, option, widget)

class NoteIcon(QGraphicsEllipseItem):
    """Clickable icon representing a note."""
    def __init__(self, note_key, ref, scene, parent=None):
        super().__init__(0, 0, 10, 10, parent)
        self.note_key = note_key
        self.ref = ref
        self.reader_scene = scene
        self.setBrush(QBrush(QColor("cyan")))
        self.setPen(QPen(Qt.black, 1))
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setZValue(10) # Ensure it's above text

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.reader_scene.open_note_by_key(self.note_key, self.ref)
            event.accept()
        else:
            super().mousePressEvent(event)

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
        self.flash_items = []  # [(item, opacity)]
        
        self.overlay_items = [] 
        
        # Arrow State
        self.is_drawing_arrow = False
        self.arrow_start_key = None
        self.arrow_start_center = None
        self.temp_arrow_items = [] # [line, head1, head2]
        
        # Flash Fade Timer
        self.flash_timer = QTimer(self)
        self.flash_timer.setInterval(50)
        self.flash_timer.timeout.connect(self._update_flash_fade)
        
        # Debouncing & Layout
        self.target_font_size = self.font_size
        self.target_line_spacing = self.line_spacing
        self.layout_timer = QTimer(self)
        self.layout_timer.setSingleShot(True)
        self.layout_timer.setInterval(LAYOUT_DEBOUNCE_INTERVAL)
        self.layout_timer.timeout.connect(self.apply_layout_changes)
        self.pending_anchor = None
        
        # Appearance
        self.font = QFont(VERSE_FONT_FAMILY, self.font_size)
        self.header_font = QFont(DEFAULT_FONT_FAMILY, HEADER_FONT_SIZE, QFont.Bold)
        self.chapter_font = QFont(DEFAULT_FONT_FAMILY, CHAPTER_FONT_SIZE, QFont.Bold)
        self.text_color = TEXT_COLOR
        self.ref_color = REFERENCE_COLOR
        
        self.scroll_timer = QTimer(self)
        self.scroll_timer.setInterval(16)
        self.scroll_timer.timeout.connect(self.update_scroll_step)
        
        self.setBackgroundBrush(APP_BACKGROUND_COLOR)
        self.last_width = 800
        self.recalculate_layout(self.last_width)

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

    def render_verses(self) -> None:
        for oi in self.overlay_items: self.removeItem(oi)
        self.overlay_items.clear()
        
        doc = self.main_text_item.document()
        layout = doc.documentLayout()
        
        pos = layout.hitTest(QPointF(SIDE_MARGIN + 10, self.scroll_y + 100), Qt.FuzzyHit)
        if pos != -1:
            ref = self._get_ref_from_pos(pos)
            if ref and ref != self.last_emitted_ref:
                self.last_emitted_ref = ref
                self.currentReferenceChanged.emit(ref)

        for start, length in self.search_results:
            rects = self._get_text_rects(start, length)
            for r in rects:
                if self._is_rect_visible(r):
                    hl = QGraphicsRectItem(r)
                    hl.setBrush(QBrush(SEARCH_HIGHLIGHT_COLOR))
                    hl.setPen(Qt.NoPen); hl.setZValue(-1)
                    hl.setAcceptedMouseButtons(Qt.NoButton)
                    self.addItem(hl); self.overlay_items.append(hl)

        self._render_study_overlays()

    def _render_study_overlays(self):
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
                    if rects and self._is_rect_visible(rects[0]):
                        r = rects[0]
                        pix_path = self.symbol_manager.get_symbol_path(symbol_name)
                        if os.path.exists(pix_path):
                            pix_item = QGraphicsPixmapItem()
                            orig_pix = QPixmap(pix_path)
                            # Increase size significantly for better visibility
                            target_h = int(r.height() * 1.8)
                            scaled_pix = orig_pix.scaled(target_h, target_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                            pix_item.setPixmap(scaled_pix)
                            pix_item.setOpacity(symbol_opacity)
                            pix_item.setAcceptedMouseButtons(Qt.NoButton)
                            
                            # Center on the word's horizontal center
                            # Ensure we are using the precise center of the rect
                            x_pos = r.left() + (r.width() - scaled_pix.width()) / 2
                            y_pos = r.top() + (r.height() - scaled_pix.height()) / 2
                            pix_item.setPos(x_pos, y_pos)
                            
                            pix_item.setZValue(5)
                            self.addItem(pix_item); self.overlay_items.append(pix_item)

        for key, arrow_list in self.study_manager.data.get("arrows", {}).items():
            ref_parts = key.split('|')
            ref = f"{ref_parts[0]} {ref_parts[1]}:{ref_parts[2]}"
            if ref in self.verse_pos_map:
                v_start = self.verse_pos_map[ref]
                verse_data = self.loader.get_verse(ref_parts[0], int(ref_parts[1]), int(ref_parts[2]))
                if verse_data:
                    start_pos_in_verse = self._get_word_offset_in_verse(verse_data, int(ref_parts[3]))
                    rects = self._get_text_rects(v_start + start_pos_in_verse, len(verse_data['tokens'][int(ref_parts[3])][0]))
                    if rects and self._is_rect_visible(rects[0]):
                        start_center = rects[0].center()
                        for arrow_data in arrow_list:
                            end_pos = QPointF(start_center.x() + arrow_data['end_dx'], start_center.y() + arrow_data['end_dy'])
                            arrow_color = QColor()
                            arrow_color.setNamedColor(arrow_data['color'])
                            items = self._create_arrow_items(start_center, end_pos, arrow_color)
                            for it in items:
                                self.addItem(it)
                                self.overlay_items.append(it)

        for mark in self.study_manager.data["marks"]:
            ref = f"{mark['book']} {mark['chapter']}:{mark['verse_num']}"
            if ref in self.verse_pos_map:
                start_pos = self.verse_pos_map[ref] + mark['start']
                rects = self._get_text_rects(start_pos, mark['length'])
                for r in rects:
                    if self._is_rect_visible(r):
                        self._add_mark_rect(r, mark['type'], mark.get('color', 'yellow'))

        for key in self.study_manager.data["notes"].keys():
            ref_parts = key.split('|')
            ref = f"{ref_parts[0]} {ref_parts[1]}:{ref_parts[2]}"
            if ref in self.verse_pos_map:
                v_start = self.verse_pos_map[ref]
                verse_data = self.loader.get_verse(ref_parts[0], int(ref_parts[1]), int(ref_parts[2]))
                if verse_data:
                    start_pos = v_start + self._get_word_offset_in_verse(verse_data, int(ref_parts[3]))
                    rects = self._get_text_rects(start_pos, len(verse_data['tokens'][int(ref_parts[3])][0]))
                    if rects and self._is_rect_visible(rects[0]):
                        r = rects[0]
                        note_icon = NoteIcon(key, ref, self)
                        note_icon.setPos(r.right() - 5, r.top() - 5)
                        self.addItem(note_icon); self.overlay_items.append(note_icon)

    def open_note_by_key(self, note_key, ref):
        """Opens the note editor for an existing note or focuses it if already open."""
        if note_key in self.open_editors:
            self.open_editors[note_key].activateWindow()
            self.open_editors[note_key].raise_()
            return

        existing_text = self.study_manager.data["notes"].get(note_key, "")
        editor = NoteEditor(existing_text, ref)
        editor.jumpRequested.connect(self.jump_to)
        self.open_editors[note_key] = editor
        editor.finished.connect(lambda result: self._on_note_editor_finished(result, editor, note_key))
        editor.show()

    def _on_note_editor_finished(self, result, editor, note_key):
        if note_key in self.open_editors:
            del self.open_editors[note_key]
        if result == QDialog.Accepted:
            ref_parts = note_key.split('|')
            self.study_manager.add_note(ref_parts[0], ref_parts[1], ref_parts[2], int(ref_parts[3]), editor.get_text())
            self.render_verses()
            self.studyDataChanged.emit()
        elif result == NoteEditor.DELETE_CODE:
            self.study_manager.delete_note(note_key)
            self.render_verses()
            self.studyDataChanged.emit()

    def _is_rect_visible(self, r):
        return not (r.bottom() < self.scroll_y or r.top() > self.scroll_y + self.view_height)

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
            self.addItem(item); self.overlay_items.append(item)

    def _get_ref_from_pos(self, pos):
        if not self.pos_verse_map: return None
        idx = bisect.bisect_right(self.pos_verse_map, (pos, "zzzzzz")) - 1
        return self.pos_verse_map[idx][1] if idx >= 0 else None

    def _get_word_offset_in_verse(self, verse_data, word_idx):
        prefix = f"{verse_data['verse_num']}  "
        text = verse_data['text']
        pos = 0
        for i in range(word_idx):
            token_text = verse_data['tokens'][i][0]
            found_pos = text.find(token_text, pos)
            if found_pos != -1:
                pos = found_pos + len(token_text)
        
        target_token = verse_data['tokens'][word_idx][0]
        actual_start = text.find(target_token, pos)
        if actual_start == -1: return len(prefix) + pos
        return len(prefix) + actual_start

    def _get_text_rects(self, start, length):
        doc = self.main_text_item.document()
        rects = []
        block = doc.findBlock(start)
        while block.isValid() and block.position() < start + length:
            block_pos = block.position()
            rel_start = max(0, start - block_pos)
            rel_end = min(block.length(), start + length - block_pos)
            if rel_start < rel_end:
                layout = block.layout()
                for i in range(layout.lineCount()):
                    line = layout.lineAt(i)
                    l_start, l_end = line.textStart(), line.textStart() + line.textLength()
                    i_start, i_end = max(rel_start, l_start), min(rel_end, l_end)
                    if i_start < i_end:
                        x1, _ = line.cursorToX(i_start); x2, _ = line.cursorToX(i_end)
                        line_rect = line.rect()
                        rect = QRectF(min(x1, x2) + layout.position().x(), 
                                      line_rect.top() + layout.position().y(), 
                                      abs(x2 - x1), line_rect.height())
                        rect.translate(self.main_text_item.pos())
                        rects.append(rect.adjusted(0, 2, 0, -2))
            block = block.next()
        return rects

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
        self.render_verses()

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
        self.render_verses()

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
        while block.isValid() and block.position() < start + length:
            ref = self._get_ref_from_pos(block.position())
            if ref:
                v_start = self.verse_pos_map[ref]
                rel_start = max(0, start - v_start)
                rel_end = min(block.length(), start + length - v_start)
                if rel_start < rel_end: self._apply_mark_to_verse(ref, rel_start, rel_end - rel_start, mark_type, color)
            block = block.next()
        self._clear_selection()
        self.render_verses()
        self.studyDataChanged.emit()

    def _apply_mark_to_verse(self, ref, rel_start, rel_length, mark_type, color):
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
            self.study_manager.add_mark({"type": mark_type, "book": verse_data['book'], "chapter": verse_data['chapter'],
                "verse_num": verse_data['verse_num'], "start": rel_start, "length": rel_length, "color": color})
            # add_mark already calls save_study
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
        if note_key in self.open_editors:
            self.open_editors[note_key].activateWindow(); self.open_editors[note_key].raise_(); self._clear_selection(); return
        editor = NoteEditor(self.study_manager.data["notes"].get(note_key, ""), ref)
        editor.jumpRequested.connect(self.jump_to)
        self.open_editors[note_key] = editor
        editor.finished.connect(lambda result: self._on_new_note_editor_finished(result, editor, note_key))
        self._clear_selection(); editor.show()

    def _on_new_note_editor_finished(self, result, editor, note_key):
        if note_key in self.open_editors: del self.open_editors[note_key]
        if result == QDialog.Accepted:
            ref_parts = note_key.split('|')
            self.study_manager.add_note(ref_parts[0], ref_parts[1], ref_parts[2], int(ref_parts[3]), editor.get_text())
            self.render_verses()
            self.studyDataChanged.emit()
        elif result == NoteEditor.DELETE_CODE:
            self.study_manager.delete_note(note_key); self.render_verses()
            self.studyDataChanged.emit()
        else: self.render_verses()

    def keyPressEvent(self, event):
        key = event.key()
        text = event.text()
        modifiers = event.modifiers()

        if key == Qt.Key_Z and modifiers == Qt.ControlModifier:
            if self.study_manager.undo():
                self.render_verses()
                self.studyDataChanged.emit()
            return

        if key == Qt.Key_Delete:
            view = self.views()[0]
            mouse_pos = view.mapToScene(view.mapFromGlobal(QCursor.pos()))
            pos = self.main_text_item.document().documentLayout().hitTest(self.main_text_item.mapFromScene(mouse_pos), Qt.FuzzyHit)
            if pos != -1:
                ref = self._get_ref_from_pos(pos)
                if ref:
                    verse_data = next((v for v in self.loader.flat_verses if v['ref'] == ref), None)
                    word_idx = self._get_word_idx_from_pos(verse_data, pos - self.verse_pos_map[ref])
                    if word_idx != -1:
                        key_str = f"{verse_data['book']}|{verse_data['chapter']}|{verse_data['verse_num']}|{word_idx}"
                        if key_str in self.study_manager.data["symbols"]:
                            self.study_manager.save_state()
                            del self.study_manager.data["symbols"][key_str]
                            self.study_manager.save_study()
                            self.render_verses()
                            self.studyDataChanged.emit()
            return

        if key == Qt.Key_A and not self.is_drawing_arrow:
            if event.isAutoRepeat(): return
            # Start drawing arrow
            view = self.views()[0]
            mouse_pos = view.mapToScene(view.mapFromGlobal(QCursor.pos()))
            pos = self.main_text_item.document().documentLayout().hitTest(self.main_text_item.mapFromScene(mouse_pos), Qt.FuzzyHit)
            if pos != -1:
                ref = self._get_ref_from_pos(pos)
                if ref:
                    verse_data = next((v for v in self.loader.flat_verses if v['ref'] == ref), None)
                    word_idx = self._get_word_idx_from_pos(verse_data, pos - self.verse_pos_map[ref])
                    if word_idx != -1:
                        # Punctuation check: don't start arrows on just punctuation
                        token_text = verse_data['tokens'][word_idx][0]
                        if not any(c.isalnum() for c in token_text):
                            return

                        self.arrow_start_key = f"{verse_data['book']}|{verse_data['chapter']}|{verse_data['verse_num']}|{word_idx}"
                        # Calculate start center
                        v_start = self.verse_pos_map[ref]
                        start_pos_in_verse = self._get_word_offset_in_verse(verse_data, word_idx)
                        rects = self._get_text_rects(v_start + start_pos_in_verse, len(verse_data['tokens'][word_idx][0]))
                        if rects:
                            self.arrow_start_center = rects[0].center()
                            self.is_drawing_arrow = True
                            self._draw_temp_arrow(mouse_pos)
            return

        if Qt.Key_1 <= key <= Qt.Key_9:
            self._apply_symbol_at_mouse(str(key - Qt.Key_0))
        elif text.isdigit() and text != '0':
            self._apply_symbol_at_mouse(text)
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_A and self.is_drawing_arrow:
            if event.isAutoRepeat(): return
            # Finish drawing arrow
            view = self.views()[0]
            mouse_pos = view.mapToScene(view.mapFromGlobal(QCursor.pos()))
            
            # Calculate dx, dy relative to start center
            dx = mouse_pos.x() - self.arrow_start_center.x()
            dy = mouse_pos.y() - self.arrow_start_center.y()
            
            color = QColor("white")
            color.setAlphaF(0.6)
            self.study_manager.add_arrow(self.arrow_start_key, dx, dy, color.name(QColor.HexArgb))
            
            self.is_drawing_arrow = False
            self.arrow_start_key = None
            self.arrow_start_center = None
            self._clear_temp_arrow()
            self.render_verses()
            self.studyDataChanged.emit()
        super().keyReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_drawing_arrow:
            self._draw_temp_arrow(event.scenePos())
        super().mouseMoveEvent(event)

    def _draw_temp_arrow(self, end_pos):
        self._clear_temp_arrow()
        if not self.arrow_start_center: return
        
        color = QColor("white")
        color.setAlphaF(0.6)
        self.temp_arrow_items = self._create_arrow_items(self.arrow_start_center, end_pos, color)
        for item in self.temp_arrow_items:
            self.addItem(item)

    def _clear_temp_arrow(self):
        for item in self.temp_arrow_items:
            self.removeItem(item)
        self.temp_arrow_items.clear()

    def _create_arrow_items(self, start, end, color):
        line = QGraphicsLineItem(start.x(), start.y(), end.x(), end.y())
        pen = QPen(color, 2)
        line.setPen(pen)
        line.setZValue(20)
        line.setAcceptedMouseButtons(Qt.NoButton)
        
        # Arrow head
        angle = math.atan2(end.y() - start.y(), end.x() - start.x())
        head_len = 10
        head_angle = math.pi / 6 # 30 degrees
        
        p1 = QPointF(end.x() - head_len * math.cos(angle - head_angle),
                     end.y() - head_len * math.sin(angle - head_angle))
        p2 = QPointF(end.x() - head_len * math.cos(angle + head_angle),
                     end.y() - head_len * math.sin(angle + head_angle))
        
        head1 = QGraphicsLineItem(end.x(), end.y(), p1.x(), p1.y())
        head1.setPen(pen); head1.setZValue(20); head1.setAcceptedMouseButtons(Qt.NoButton)
        
        head2 = QGraphicsLineItem(end.x(), end.y(), p2.x(), p2.y())
        head2.setPen(pen); head2.setZValue(20); head2.setAcceptedMouseButtons(Qt.NoButton)
        
        return [line, head1, head2]

    def _apply_symbol_at_mouse(self, number_key):
        symbol_name = self.symbol_manager.get_binding(number_key)
        if not symbol_name:
            return

        view = self.views()[0]; mouse_pos = view.mapToScene(view.mapFromGlobal(QCursor.pos()))
        pos = self.main_text_item.document().documentLayout().hitTest(self.main_text_item.mapFromScene(mouse_pos), Qt.FuzzyHit)
        if pos != -1:
            ref = self._get_ref_from_pos(pos)
            if ref:
                verse_data = next((v for v in self.loader.flat_verses if v['ref'] == ref), None)
                word_idx = self._get_word_idx_from_pos(verse_data, pos - self.verse_pos_map[ref])
                if word_idx != -1:
                    # Punctuation check: don't add symbols to just punctuation
                    token_text = verse_data['tokens'][word_idx][0]
                    if not any(c.isalnum() for c in token_text):
                        return

                    self.study_manager.add_symbol(verse_data['book'], verse_data['chapter'], verse_data['verse_num'], word_idx, symbol_name)
                    self.render_verses()
                    self.studyDataChanged.emit()

    def _get_word_idx_from_pos(self, item_data, pos):
        if item_data is None: return -1
        prefix = f"{item_data['verse_num']}  "
        rel_pos = pos - len(prefix)
        
        # Map verse number/prefix to the first word (index 0)
        if 0 <= pos < len(prefix):
            return 0
        
        if pos < 0: return -1
        
        text = item_data['text']
        search_pos = 0
        for i, token in enumerate(item_data['tokens']):
            token_text = token[0]
            start = text.find(token_text, search_pos)
            if start != -1:
                end = start + len(token_text)
                if start <= rel_pos <= end:
                    return i
                search_pos = end
        return -1

    def set_scroll_y(self, value: float) -> None:
        self.target_scroll_y = float(value); self.scroll_y = self.target_scroll_y
        super().setSceneRect(QRectF(0, self.scroll_y, self.last_width, self.view_height))
        self.render_verses(); self.scrollChanged.emit(int(self.scroll_y))

    def setSceneRect(self, *args) -> None:
        if len(args) == 1: rect = args[0]
        else: rect = QRectF(args[0], args[1], args[2], args[3])
        if abs(rect.width() - self.last_width) > 2:
            self.last_width = rect.width(); self.recalculate_layout(self.last_width)
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
        self.font = QFont(VERSE_FONT_FAMILY, self.target_font_size)
        self.header_font = QFont(DEFAULT_FONT_FAMILY, HEADER_FONT_SIZE, QFont.Bold)
        self.chapter_font = QFont(DEFAULT_FONT_FAMILY, CHAPTER_FONT_SIZE, QFont.Bold)
        self.font_size, self.line_spacing = self.target_font_size, self.target_line_spacing
        self.recalculate_layout(self.last_width); self.pending_anchor = None
        super().setSceneRect(QRectF(0, self.scroll_y, self.last_width, self.view_height))
        self.render_verses(); self.scrollChanged.emit(int(self.scroll_y)); self.layoutFinished.emit()

    def update_scroll_step(self) -> None:
        diff = self.target_scroll_y - self.scroll_y
        if abs(diff) < 1.0: self.scroll_y = self.target_scroll_y; self.scroll_timer.stop()
        else: self.scroll_y += diff * 0.15
        super().setSceneRect(QRectF(0, self.scroll_y, self.last_width, self.view_height))
        self.render_verses(); self.scrollChanged.emit(int(self.scroll_y))

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

