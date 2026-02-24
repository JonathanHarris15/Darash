from PySide6.QtWidgets import QGraphicsScene, QMenu
from PySide6.QtCore import Qt, QRectF, QTimer, Signal, QPointF
from PySide6.QtGui import QColor, QFont, QCursor, QTextCursor, QAction

from src.core.verse_loader import VerseLoader
from src.managers.study_manager import StudyManager
from src.managers.symbol_manager import SymbolManager
from src.managers.strongs_manager import StrongsManager

from src.scene.scene_input_handler import SceneInputHandler
from src.scene.scene_overlay_manager import SceneOverlayManager
from src.scene.layout_engine import LayoutEngine
from src.scene.renderer import OverlayRenderer

from src.ui.components.mark_popup import MarkPopup
from src.ui.components.note_editor import NoteEditor
from src.ui.components.strongs_ui import StrongsTooltip
from src.ui.components.suggested_symbols_dialog import SuggestedSymbolsDialog
from src.ui.components.outline_dialog import OutlineDialog

from src.scene.components.reader_items import NoFocusTextItem, VerseNumberItem

from src.utils.reader_utils import (
    get_word_idx_from_pos, get_text_rects, 
    get_word_offset_in_verse
)

from src.core.constants import (
    APP_BACKGROUND_COLOR, TEXT_COLOR, REFERENCE_COLOR,
    DEFAULT_FONT_FAMILY, VERSE_FONT_FAMILY, DEFAULT_FONT_SIZE, 
    HEADER_FONT_SIZE, CHAPTER_FONT_SIZE,
    LINE_SPACING_DEFAULT, SCROLL_SENSITIVITY, SIDE_MARGIN,
    TAB_SIZE_DEFAULT, ARROW_OPACITY_DEFAULT, VERSE_MARK_SIZE_DEFAULT,
    LOGICAL_MARK_OPACITY_DEFAULT, LAYOUT_DEBOUNCE_INTERVAL, LOGICAL_MARK_COLOR
)
import bisect
import os
import time

class ReaderScene(QGraphicsScene):
    """
    The main rendering engine for the Bible reader.
    Acts as a facade coordinating LayoutEngine, OverlayRenderer, and InputHandler.
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
    outlineCreated = Signal(str) # node_id

    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.scroll_y = 0.0
        self.target_scroll_y = 0.0
        self.font_size = DEFAULT_FONT_SIZE
        self.line_spacing = LINE_SPACING_DEFAULT
        self.font_family = VERSE_FONT_FAMILY
        self.verse_num_font_size = DEFAULT_FONT_SIZE - 4
        self.side_margin = SIDE_MARGIN
        self.tab_size = TAB_SIZE_DEFAULT
        self.arrow_opacity = ARROW_OPACITY_DEFAULT
        self.verse_mark_size = VERSE_MARK_SIZE_DEFAULT
        self.logical_mark_opacity = LOGICAL_MARK_OPACITY_DEFAULT
        self.scroll_sens = SCROLL_SENSITIVITY
        self.last_emitted_ref = ""
        
        self.loader = VerseLoader()
        self.study_manager = StudyManager(loader=self.loader)
        self.symbol_manager = SymbolManager()
        self.strongs_manager = StrongsManager()
        self.strongs_manager.index_usages(self.loader)
        
        self.pixmap_cache = {} 
        self.verse_number_items = {} 
        self.selected_verse_items = []
        self.selected_refs = set()
        self.last_clicked_verse_idx = -1
        
        self.main_text_item = NoFocusTextItem()
        self.main_text_item.setAcceptHoverEvents(True)
        self.main_text_item.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.addItem(self.main_text_item)
        
        self.strongs_enabled = False
        self.strongs_tooltip = StrongsTooltip()
        self.strongs_overlay_items = []
        
        self.outlines_enabled = False
        self.active_outline_id = None
        self.outline_overlay_items = []
        self.ghost_line_item = None
        
        self.is_dragging_divider = False
        self.drag_divider_item = None
        self.drag_divider_ghost = None
        self.drag_min_idx = float('-inf')
        self.drag_max_idx = float('inf')
        
        self.mark_popup = MarkPopup()
        self.mark_popup.markSelected.connect(self._on_mark_selected)
        self.mark_popup.addNoteRequested.connect(self._on_add_note_requested)
        self.mark_popup.addBookmarkRequested.connect(self._on_add_bookmark_requested)
        self.mark_popup.createOutlineRequested.connect(self._create_outline_from_selection)
        self.current_selection = None
        
        self.verse_pos_map = {}
        self.pos_verse_map = []
        self.search_results = []
        self.search_marks_y = [] 
        self.current_search_idx = -1
        self.open_editors = {} 
        self.flash_items = []  
        
        self.study_overlay_items = [] 
        self.search_overlay_items = []
        self.heading_rects = [] 
        self._pending_headings = [] 
        
        self.is_drawing_arrow = False
        self.arrow_start_key = None
        self.arrow_start_center = None
        self.temp_arrow_item = None
        
        self._init_timers()
        self.load_settings()
        self._update_fonts()
        
        self.text_color = QColor(self.study_manager.data["settings"].get("text_color", TEXT_COLOR.name()))
        self.ref_color = QColor(self.study_manager.data["settings"].get("ref_color", REFERENCE_COLOR.name()))
        self.logical_mark_color = QColor(self.study_manager.data["settings"].get("logical_mark_color", LOGICAL_MARK_COLOR.name()))
        bg_color = QColor(self.study_manager.data["settings"].get("bg_color", APP_BACKGROUND_COLOR.name()))
        self.setBackgroundBrush(bg_color)
        
        self.last_width = 800
        self.view_height = 600
        self.total_height = 0
        self.layout_version = 0 
        
        self._wheel_accumulator = 0.0
        self._zoom_accumulator = 0.0

        # Sub-engines
        self.layout_engine = LayoutEngine(self)
        self.renderer = OverlayRenderer(self)
        self.input_handler = SceneInputHandler(self)
        self.overlay_manager = SceneOverlayManager(self)

    def load_settings(self):
        settings = self.study_manager.data.get("settings", {})
        self.font_size = settings.get("font_size", DEFAULT_FONT_SIZE)
        self.line_spacing = settings.get("line_spacing", LINE_SPACING_DEFAULT)
        self.font_family = settings.get("font_family", VERSE_FONT_FAMILY)
        self.verse_num_font_size = settings.get("verse_num_size", self.font_size - 4)
        self.side_margin = settings.get("side_margin", SIDE_MARGIN)
        self.tab_size = settings.get("tab_size", TAB_SIZE_DEFAULT)
        self.arrow_opacity = settings.get("arrow_opacity", ARROW_OPACITY_DEFAULT)
        self.verse_mark_size = settings.get("verse_mark_size", VERSE_MARK_SIZE_DEFAULT)
        self.logical_mark_opacity = settings.get("logical_mark_opacity", LOGICAL_MARK_OPACITY_DEFAULT)
        
        self.target_font_size = self.font_size
        self.target_line_spacing = self.line_spacing
        self.target_font_family = self.font_family
        self.target_verse_num_size = self.verse_num_font_size
        self.target_side_margin = self.side_margin
        self.target_tab_size = self.tab_size
        self.target_arrow_opacity = self.arrow_opacity
        self.target_verse_mark_size = self.verse_mark_size
        self.target_logical_mark_opacity = self.logical_mark_opacity

    def save_settings(self):
        settings = self.study_manager.data["settings"]
        settings["font_size"] = self.font_size
        settings["line_spacing"] = self.line_spacing
        settings["font_family"] = self.font_family
        settings["verse_num_size"] = self.verse_num_font_size
        settings["side_margin"] = self.side_margin
        settings["tab_size"] = self.tab_size
        settings["arrow_opacity"] = self.arrow_opacity
        settings["verse_mark_size"] = self.verse_mark_size
        settings["logical_mark_opacity"] = self.logical_mark_opacity
        settings["text_color"] = self.text_color.name()
        settings["ref_color"] = self.ref_color.name()
        settings["logical_mark_color"] = self.logical_mark_color.name()
        settings["bg_color"] = self.backgroundBrush().color().name()
        self.study_manager.save_study()

    def _init_timers(self):
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

    def _update_fonts(self):
        self.font = QFont(self.font_family, self.font_size)
        self.header_font = QFont(DEFAULT_FONT_FAMILY, HEADER_FONT_SIZE, QFont.Bold)
        self.chapter_font = QFont(DEFAULT_FONT_FAMILY, CHAPTER_FONT_SIZE, QFont.Bold)
        self.verse_num_font = QFont(self.font_family, self.verse_num_font_size)
        self.verse_mark_font = QFont(self.font_family, self.verse_mark_size)

    def _is_rect_visible(self, r):
        buffer = 800 
        return not (r.bottom() < self.scroll_y - buffer or r.top() > self.scroll_y + self.view_height + buffer)

    def _update_item_visibility(self):
        for item in self.study_overlay_items + self.search_overlay_items + self.outline_overlay_items:
            item.setVisible(self._is_rect_visible(item.sceneBoundingRect()))

    def _get_ref_from_pos(self, pos):
        if not self.pos_verse_map: return None
        idx = bisect.bisect_right(self.pos_verse_map, (pos, "zzzzzz")) - 1
        return self.pos_verse_map[idx][1] if idx >= 0 else None
    
    def _get_text_rects(self, start, length):
        return get_text_rects(self.main_text_item, start, length)

    def _get_word_offset_in_verse(self, verse_data, word_idx):
        return get_word_offset_in_verse(verse_data, word_idx)

    def _get_word_idx_from_pos(self, verse_data, pos):
        return get_word_idx_from_pos(verse_data, pos)

    def recalculate_layout(self, width: float) -> None:
        self.layout_engine.recalculate_layout(width)

    def render_verses(self) -> None:
        self.renderer.render_verses()

    def set_outlines_enabled(self, enabled: bool):
        self.outlines_enabled = enabled
        if not enabled:
            self._clear_outline_overlays()
        else:
            self.renderer._render_outline_overlays()

    def set_active_outline(self, outline_id: str):
        self.active_outline_id = outline_id
        self.renderer._render_outline_overlays()

    def _clear_outline_overlays(self):
        for it in self.outline_overlay_items:
            if it.scene() == self:
                self.removeItem(it)
        self.outline_overlay_items.clear()
        if self.ghost_line_item:
            if self.ghost_line_item.scene() == self:
                self.removeItem(self.ghost_line_item)
            self.ghost_line_item = None

    def set_strongs_enabled(self, enabled: bool):
        self.strongs_enabled = enabled
        if not enabled:
            self._clear_strongs_overlays()
            self.strongs_tooltip.hide()
        else:
            self.render_verses()

    def _clear_strongs_overlays(self):
        for it in self.strongs_overlay_items:
            if it.scene() == self:
                self.removeItem(it)
        self.strongs_overlay_items.clear()

    def _get_strongs_at_pos(self, scene_pos):
        pos = self.main_text_item.document().documentLayout().hitTest(self.main_text_item.mapFromScene(scene_pos), Qt.FuzzyHit)
        if pos != -1:
            ref = self._get_ref_from_pos(pos)
            if ref:
                verse_data = self.loader.get_verse_by_ref(ref)
                if verse_data:
                    word_idx = self._get_word_idx_from_pos(verse_data, pos - self.verse_pos_map[ref])
                    if word_idx != -1 and word_idx < len(verse_data['tokens']):
                        token = verse_data['tokens'][word_idx]
                        if len(token) > 1:
                            return token[1], ref 
        return None, None

    def _get_word_center(self, key):
        if not key or not isinstance(key, str): return None
        ref_parts = key.split('|')
        if len(ref_parts) < 4: return None
        
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
        self.overlay_manager.render_study_overlays()

    def _render_outline_overlays(self):
        self.renderer._render_outline_overlays()

    def _render_search_overlays(self):
        self.renderer._render_search_overlays()

    def _create_symbol_item(self, symbol_name, target_rect, opacity):
        from PySide6.QtWidgets import QGraphicsPixmapItem
        from PySide6.QtGui import QPixmap
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
        
        x_pos = target_rect.left() + (target_rect.width() - scaled_pix.width()) / 2
        y_pos = target_rect.top() + (target_rect.height() - scaled_pix.height()) / 2
        pix_item.setPos(x_pos, y_pos)
        return pix_item

    def open_note_by_key(self, note_key, ref):
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
        from PySide6.QtWidgets import QDialog
        editor.finished.connect(lambda result: self._on_note_editor_finished(result, editor, note_key))
        editor.show()

    def _on_note_editor_finished(self, result, editor, note_key):
        from PySide6.QtWidgets import QDialog
        if note_key in self.open_editors:
            del self.open_editors[note_key]
        if result == QDialog.Accepted:
            if note_key.startswith("standalone_"):
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
        heading_data = self._get_heading_at_pos(event.scenePos())
        if heading_data:
            menu = QMenu()
            menu.setStyleSheet("QMenu { background-color: #333; color: white; } QMenu::item:selected { background-color: #555; }")
            suggest_act = QAction("Get suggested symbols", menu)
            suggest_act.triggered.connect(lambda: self._show_suggested_symbols_dialog(heading_data))
            menu.addAction(suggest_act)
            menu.exec(event.screenPos())
            event.accept()
            return
            
        item = self.itemAt(event.scenePos(), self.views()[0].transform())
        if isinstance(item, VerseNumberItem):
            item.contextMenuRequested.emit(event.screenPos())
            event.accept()
            return

        cursor = self.main_text_item.textCursor()
        if not cursor.hasSelection():
            pos = self.main_text_item.document().documentLayout().hitTest(self.main_text_item.mapFromScene(event.scenePos()), Qt.FuzzyHit)
            if pos != -1:
                cursor.setPosition(pos); cursor.select(QTextCursor.WordUnderCursor); self.main_text_item.setTextCursor(cursor)
        
        if cursor.hasSelection():
            self.current_selection = (cursor.selectionStart(), cursor.selectionEnd() - cursor.selectionStart())
            view = self.views()[0]
            screen_pos = view.viewport().mapToGlobal(view.mapFromScene(event.scenePos()))
            self.mark_popup.show_at(screen_pos)
            self.render_verses() 
            event.accept()
            return
        super().contextMenuEvent(event)

    def mouseReleaseEvent(self, event):
        if self.is_dragging_divider:
            self.is_dragging_divider = False
            if self.drag_divider_ghost: 
                if not self.drag_divider_ghost.isVisible():
                    self.removeItem(self.drag_divider_ghost)
                    self.drag_divider_ghost = None
                    self.drag_divider_item = None
                    self.views()[0].setCursor(Qt.ArrowCursor)
                    event.accept()
                    return

                new_y = self.drag_divider_ghost.line().y1()
                
                doc = self.main_text_item.document()
                layout = doc.documentLayout()
                
                ref_before, ref_after = None, None
                
                for i in range(len(self.pos_verse_map) - 1):
                    char_pos1, r1 = self.pos_verse_map[i]
                    char_pos2, r2 = self.pos_verse_map[i+1]
                    rect1 = layout.blockBoundingRect(doc.findBlock(char_pos1))
                    rect2 = layout.blockBoundingRect(doc.findBlock(char_pos2))
                    mid_y = (rect1.bottom() + rect2.top()) / 2
                    if abs(new_y - mid_y) < 2: 
                        ref_before, ref_after = r1, r2
                        break
                
                if ref_before and ref_after:
                    item = self.drag_divider_item
                    if item.split_idx == -2: 
                        if self.study_manager.outline_manager.update_outline_boundary(item.parent_node["id"], True, ref_after, self.loader):
                            self._render_outline_overlays()
                            self.studyDataChanged.emit()
                    elif item.split_idx == -3: 
                        if self.study_manager.outline_manager.update_outline_boundary(item.parent_node["id"], False, ref_before, self.loader):
                            self._render_outline_overlays()
                            self.studyDataChanged.emit()
                    elif item.split_idx >= 0:
                        if self.study_manager.outline_manager.move_split_by_id(item.parent_node["id"], item.split_idx, ref_before, ref_after, self.loader):
                            self._render_outline_overlays()
                            self.studyDataChanged.emit()

                self.removeItem(self.drag_divider_ghost)
                self.drag_divider_ghost = None
                self.drag_divider_item = None
                self.views()[0].setCursor(Qt.ArrowCursor)
                event.accept()
                return

        if event.button() != Qt.LeftButton: 
            super().mouseReleaseEvent(event)
            return

        cursor = self.main_text_item.textCursor()
        if cursor.hasSelection():
            self.current_selection = (cursor.selectionStart(), cursor.selectionEnd() - cursor.selectionStart())
            view = self.views()[0]
            screen_pos = view.viewport().mapToGlobal(view.mapFromScene(event.scenePos()))
            self.mark_popup.show_at(screen_pos)
        else: 
            self.current_selection = None
        
        self.render_verses() 
        super().mouseReleaseEvent(event)

    def _clear_verse_selection(self):
        for it in self.verse_number_items.values():
            it.is_selected = False
            it.update()
        self.selected_verse_items = []
        if hasattr(self, "selected_refs"): self.selected_refs.clear()
        self.last_clicked_verse_idx = -1

    def _on_verse_num_context_menu(self, item, screen_pos):
        if item.ref not in self.selected_refs:
            self._on_verse_num_clicked(item, False)
            
        menu = QMenu()
        menu.setStyleSheet("QMenu { background-color: #333; color: white; } QMenu::item:selected { background-color: #555; }")
        
        heart_act = QAction("❤ Heart", menu)
        heart_act.triggered.connect(lambda: self._set_selected_verse_mark("heart"))
        menu.addAction(heart_act)
        
        question_act = QAction("? Question Mark", menu)
        question_act.triggered.connect(lambda: self._set_selected_verse_mark("question"))
        menu.addAction(question_act)
        
        attention_act = QAction("!! Attention", menu)
        attention_act.triggered.connect(lambda: self._set_selected_verse_mark("attention"))
        menu.addAction(attention_act)
        
        star_act = QAction("★ Star", menu)
        star_act.triggered.connect(lambda: self._set_selected_verse_mark("star"))
        menu.addAction(star_act)
        
        menu.addSeparator()
        
        clear_act = QAction("Clear Mark", menu)
        clear_act.triggered.connect(lambda: self._set_selected_verse_mark(None))
        menu.addAction(clear_act)

        menu.addSeparator()
        
        outline_act = QAction("Create Outline", menu)
        outline_act.triggered.connect(self._create_outline_from_verse_selection)
        menu.addAction(outline_act)
        
        menu.exec(screen_pos.toPoint())

    def _create_outline_from_verse_selection(self):
        if not self.selected_refs: return
        
        sorted_refs = sorted(list(self.selected_refs), key=lambda r: self.loader.get_verse_index(r))
        start_ref = sorted_refs[0]
        end_ref = sorted_refs[-1]
        
        dialog = OutlineDialog(None, title="Book Outline", start_ref=start_ref, end_ref=end_ref)
        if dialog.exec():
            data = dialog.get_data()
            if data["title"]:
                node = self.study_manager.outline_manager.create_outline(
                    data["start_ref"], data["end_ref"], data["title"]
                )
                self.studyDataChanged.emit()
                self._render_outline_overlays()
                self.outlineCreated.emit(node["id"])
                self.set_active_outline(node["id"])

    def _create_outline_from_selection(self):
        if not self.current_selection: return
        start, length = self.current_selection
        
        start_ref = self._get_ref_from_pos(start)
        end_ref = self._get_ref_from_pos(start + length - 1)
        
        if not start_ref or not end_ref: return
        
        dialog = OutlineDialog(None, title="New Outline", start_ref=start_ref, end_ref=end_ref)
        if dialog.exec():
            data = dialog.get_data()
            if data["title"]:
                self.study_manager.outline_manager.create_outline(
                    data["start_ref"], data["end_ref"], data["title"]
                )
                self.studyDataChanged.emit() 
                self._render_outline_overlays() 

    def _set_selected_verse_mark(self, mark_type):
        for ref in self.selected_refs:
            self.study_manager.set_verse_mark(ref, mark_type)
            
        self.render_verses()
        self.studyDataChanged.emit()

    def wheelEvent(self, event) -> None:
        if self.input_handler.handle_wheel(event):
            event.accept()
            return
        
        modifiers = event.modifiers(); delta = event.delta() 
        if delta == 0: 
            super().wheelEvent(event) 
            return
        
        if modifiers & (Qt.ControlModifier | Qt.AltModifier):
            self._zoom_accumulator += delta
            while abs(self._zoom_accumulator) >= 120:
                step = 120 if self._zoom_accumulator > 0 else -120
                if modifiers & Qt.ControlModifier: 
                    self.target_font_size = max(8, min(72, self.target_font_size + (2 if step > 0 else -2)))
                elif modifiers & Qt.AltModifier: 
                    self.target_line_spacing = max(1.0, min(3.0, self.target_line_spacing + (0.1 if step > 0 else -0.1)))
                self._zoom_accumulator -= step
            
            self.settingsPreview.emit(self.target_font_size, self.target_line_spacing); self.layout_timer.start(); event.accept(); return
        
        self._wheel_accumulator += delta
        while abs(self._wheel_accumulator) >= 30:
            step = 30 if self._wheel_accumulator > 0 else -30
            move = -(step / 120.0) * self.scroll_sens
            self.target_scroll_y = max(0, min(self.total_height - self.view_height, self.target_scroll_y + move))
            self._wheel_accumulator -= step
            
        if not self.scroll_timer.isActive(): self.scroll_timer.start()
        event.accept()
        
        super().wheelEvent(event) 

    def mousePressEvent(self, event):
        item = self.itemAt(event.scenePos(), self.views()[0].transform())
        if not isinstance(item, VerseNumberItem):
            self._clear_verse_selection()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self.active_outline_id and event.button() == Qt.LeftButton:
            scene_pos = event.scenePos()
            doc = self.main_text_item.document()
            layout = doc.documentLayout()
            tolerance = 10 
            
            for i in range(len(self.pos_verse_map) - 1):
                char_pos1, ref1 = self.pos_verse_map[i]
                char_pos2, ref2 = self.pos_verse_map[i+1]
                
                rect1 = layout.blockBoundingRect(doc.findBlock(char_pos1))
                rect2 = layout.blockBoundingRect(doc.findBlock(char_pos2))
                
                bottom1 = rect1.bottom()
                top2 = rect2.top()
                
                if bottom1 - tolerance <= scene_pos.y() <= top2 + tolerance:
                    if self.study_manager.outline_manager.add_split(ref1, ref2, self.loader):
                        self._render_outline_overlays()
                        self.studyDataChanged.emit()
                    
                    if self.ghost_line_item:
                        self.removeItem(self.ghost_line_item)
                        self.ghost_line_item = None
                    event.accept()
                    return
        super().mouseDoubleClickEvent(event)

    def _clear_selection(self):
        cursor = self.main_text_item.textCursor()
        cursor.clearSelection()
        self.main_text_item.setTextCursor(cursor)
        self.current_selection = None

    def _on_mark_selected(self, mark_type, color):
        if not self.current_selection: return
        start, length = self.current_selection
        
        if mark_type == "logical_mark":
            ref = self._get_ref_from_pos(start)
            if ref:
                verse_data = self.loader.get_verse_by_ref(ref)
                if verse_data:
                    v_start = self.verse_pos_map[ref]
                    rel_pos = start - v_start
                    word_idx = self._get_word_idx_from_pos(verse_data, rel_pos)
                    if word_idx != -1:
                        key = f"{verse_data['book']}|{verse_data['chapter']}|{verse_data['verse_num']}|{word_idx}"
                        self.study_manager.add_logical_mark(key, color) 
            
            self._clear_selection()
            self._render_study_overlays()
            self.studyDataChanged.emit()
            return

        doc = self.main_text_item.document()
        block = doc.findBlock(start)
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
        verse_data = self.loader.get_verse_by_ref(ref)
        if not verse_data: return
        
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
        elif modified:
            self.study_manager.save_study()

    def _on_add_bookmark_requested(self):
        if not self.current_selection: return
        start, _ = self.current_selection
        ref = self._get_ref_from_pos(start)
        if not ref: return
        verse_data = self.loader.get_verse_by_ref(ref)
        if verse_data:
            self.study_manager.add_bookmark(verse_data['book'], str(verse_data['chapter']), str(verse_data['verse_num']))
            self._clear_selection()
            self.bookmarksUpdated.emit()

    def _on_add_note_requested(self):
        if not self.current_selection: return
        start, _ = self.current_selection
        ref = self._get_ref_from_pos(start)
        if not ref: return
        verse_data = self.loader.get_verse_by_ref(ref)
        word_idx = self._get_word_idx_from_pos(verse_data, start - self.verse_pos_map[ref])
        note_key = f"{verse_data['book']}|{verse_data['chapter']}|{verse_data['verse_num']}|{word_idx}"
        
        self.open_note_by_key(note_key, ref)
        self._clear_selection()

    def _get_word_key_at_pos(self, scene_pos):
        pos = self.main_text_item.document().documentLayout().hitTest(self.main_text_item.mapFromScene(scene_pos), Qt.FuzzyHit)
        if pos != -1:
            ref = self._get_ref_from_pos(pos)
            if ref:
                verse_data = self.loader.get_verse_by_ref(ref)
                if verse_data:
                    word_idx = self._get_word_idx_from_pos(verse_data, pos - self.verse_pos_map[ref])
                    if word_idx != -1:
                        token_text = verse_data['tokens'][word_idx][0]
                        if any(c.isalnum() for c in token_text):
                            return f"{verse_data['book']}|{verse_data['chapter']}|{verse_data['verse_num']}|{word_idx}"
        return None

    def keyPressEvent(self, event):
        if self.input_handler.handle_key_press(event):
            return
        super().keyPressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_dragging_divider:
            from PySide6.QtGui import QPen
            from PySide6.QtWidgets import QGraphicsLineItem
            scene_pos = event.scenePos()
            doc = self.main_text_item.document()
            layout = doc.documentLayout()
            
            best_gap_y = -1
            best_dist = 1000
            
            for i in range(len(self.pos_verse_map) - 1):
                char_pos1, r1 = self.pos_verse_map[i]
                char_pos2, r2 = self.pos_verse_map[i+1]
                
                idx_before = self.loader.get_verse_index(r1)
                
                if idx_before < self.drag_bounds_min or idx_before > self.drag_bounds_max:
                    continue
                if self.drag_hard_min is not None and idx_before <= self.drag_hard_min:
                    continue
                if self.drag_hard_max is not None and idx_before >= self.drag_hard_max:
                    continue
                
                rect1 = layout.blockBoundingRect(doc.findBlock(char_pos1))
                rect2 = layout.blockBoundingRect(doc.findBlock(char_pos2))
                
                mid_y = (rect1.bottom() + rect2.top()) / 2
                dist = abs(scene_pos.y() - mid_y)
                
                if dist < 50 and dist < best_dist:
                    best_dist = dist
                    best_gap_y = mid_y
            
            if best_gap_y != -1:
                self.drag_divider_ghost.setLine(self.side_margin, best_gap_y, self.sceneRect().width() - 10, best_gap_y)
                self.drag_divider_ghost.show()
            else:
                self.drag_divider_ghost.hide()
            
            super().mouseMoveEvent(event)
            return

        if self.active_outline_id:
            from PySide6.QtGui import QPen
            from PySide6.QtWidgets import QGraphicsLineItem
            scene_pos = event.scenePos()
            doc = self.main_text_item.document()
            layout = doc.documentLayout()
            tolerance = 10
            found_gap = False
            
            for i in range(len(self.pos_verse_map) - 1):
                char_pos1, _ = self.pos_verse_map[i]
                char_pos2, _ = self.pos_verse_map[i+1]
                
                rect1 = layout.blockBoundingRect(doc.findBlock(char_pos1))
                rect2 = layout.blockBoundingRect(doc.findBlock(char_pos2))
                
                bottom1 = rect1.bottom()
                top2 = rect2.top()
                
                if bottom1 - tolerance <= scene_pos.y() <= top2 + tolerance:
                    mid_y = (bottom1 + top2) / 2
                    if not self.ghost_line_item:
                        pen = QPen(QColor("#AAAAAA"))
                        pen.setStyle(Qt.DotLine)
                        pen.setWidthF(1.0)
                        color = QColor("#AAAAAA")
                        color.setAlpha(80)
                        pen.setColor(color)
                        
                        self.ghost_line_item = QGraphicsLineItem(self.side_margin, mid_y, self.sceneRect().width() - 10, mid_y)
                        self.ghost_line_item.setPen(pen)
                        self.addItem(self.ghost_line_item)
                    else:
                        self.ghost_line_item.setLine(self.side_margin, mid_y, self.sceneRect().width() - 10, mid_y)
                    found_gap = True
                    break
            
            if not found_gap and self.ghost_line_item:
                self.removeItem(self.ghost_line_item)
                self.ghost_line_item = None
        elif self.ghost_line_item:
            self.removeItem(self.ghost_line_item)
            self.ghost_line_item = None

        self.input_handler.handle_mouse_move(event)
        super().mouseMoveEvent(event)

    def keyReleaseEvent(self, event):
        if self.input_handler.handle_key_release(event):
            return
        super().keyReleaseEvent(event)

    def _apply_symbol_at_mouse(self, number_key):
        view = self.views()[0]
        mouse_pos = view.mapToScene(view.mapFromGlobal(QCursor.pos()))
        
        key = self._get_word_key_at_pos(mouse_pos)
        if not key: return
        
        symbol_id = self.symbol_manager.get_binding(number_key)
        if symbol_id:
            parts = key.split('|')
            if len(parts) >= 4:
                self.study_manager.add_symbol(parts[0], parts[1], parts[2], int(parts[3]), symbol_id)
                self._render_study_overlays()
                self.studyDataChanged.emit()

    def set_scroll_y(self, value: float) -> None:
        self.target_scroll_y = float(value); self.scroll_y = self.target_scroll_y
        super().setSceneRect(QRectF(0, self.scroll_y, self.last_width, self.view_height))
        self.render_verses(); self.scrollChanged.emit(int(self.scroll_y))
        self._update_item_visibility()

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

    def cycle_divider_at_pos(self, scene_pos, delta):
        from src.scene.components.reader_items import OutlineDividerItem
        view = self.views()[0]
        item = self.itemAt(scene_pos, view.transform())
        
        if isinstance(item, OutlineDividerItem):
            if item.split_idx >= 0:
                if self.study_manager.outline_manager.cycle_level_by_id(item.parent_node["id"], item.split_idx, delta < 0):
                    self._render_outline_overlays()
                    self.studyDataChanged.emit()
                    return True
        
        doc = self.main_text_item.document()
        layout = doc.documentLayout()
        tolerance = 20
        
        for i in range(len(self.pos_verse_map) - 1):
            char_pos1, ref1 = self.pos_verse_map[i]
            char_pos2, ref2 = self.pos_verse_map[i+1]
            
            rect1 = layout.blockBoundingRect(doc.findBlock(char_pos1))
            rect2 = layout.blockBoundingRect(doc.findBlock(char_pos2))
            
            if rect1.bottom() - tolerance <= scene_pos.y() <= rect2.top() + tolerance:
                if self.study_manager.outline_manager.cycle_level(ref1, ref2, delta < 0, self.loader):
                    self._render_outline_overlays()
                    self.studyDataChanged.emit()
                    return True
        return False

    def apply_layout_changes(self) -> None:
        self.font_size = self.target_font_size
        self.line_spacing = self.target_line_spacing
        self.font_family = self.target_font_family
        self.verse_num_font_size = self.target_verse_num_size
        self.side_margin = self.target_side_margin
        self.tab_size = self.target_tab_size
        self.arrow_opacity = self.target_arrow_opacity
        self.verse_mark_size = self.target_verse_mark_size
        self.logical_mark_opacity = self.target_logical_mark_opacity
        
        self._update_fonts()
        self.save_settings()
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
        self._update_item_visibility()

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
        from PySide6.QtWidgets import QGraphicsRectItem
        from PySide6.QtGui import QBrush
        if ref not in self.verse_pos_map:
            return
            
        pos = self.verse_pos_map[ref]
        doc = self.main_text_item.document()
        block = doc.findBlock(pos)
        length = block.length()
        
        rects = self._get_text_rects(pos, length)
        for r in rects:
            item = QGraphicsRectItem(r)
            item.setBrush(QBrush(QColor(100, 200, 255, 100))) 
            item.setPen(Qt.NoPen)
            item.setZValue(-2) 
            self.addItem(item)
            self.flash_items.append([item, 1.0])
            
        if not self.flash_timer.isActive():
            self.flash_timer.start()

    def _update_flash_fade(self):
        to_remove = []
        for i, (item, opacity) in enumerate(self.flash_items):
            new_opacity = opacity - 0.05
            if new_opacity <= 0:
                self.removeItem(item)
                to_remove.append(i)
            else:
                item.setOpacity(new_opacity)
                self.flash_items[i][1] = new_opacity
                
        for i in sorted(to_remove, reverse=True):
            self.flash_items.pop(i)
            
        if not self.flash_items:
            self.flash_timer.stop()

    def _on_verse_num_clicked(self, item, shift):
        flat_refs = [v['ref'] for v in self.loader.flat_verses]
        item_idx = flat_refs.index(item.ref)

        if not shift:
            if not hasattr(self, "selected_refs"): self.selected_refs = set()
            
            if item.ref in self.selected_refs:
                return
            
            self._clear_verse_selection()
            self.selected_verse_items = [item]
            item.is_selected = True
            item.update()
            self.last_clicked_verse_idx = item_idx
            
            if not hasattr(self, "selected_refs"): self.selected_refs = set()
            self.selected_refs.add(item.ref)
        else:
            if self.last_clicked_verse_idx == -1:
                self.last_clicked_verse_idx = item_idx
                self.selected_verse_items = [item]
                item.is_selected = True
                item.update()
                if not hasattr(self, "selected_refs"): self.selected_refs = set()
                self.selected_refs.add(item.ref)
            else:
                start = min(self.last_clicked_verse_idx, item_idx)
                end = max(self.last_clicked_verse_idx, item_idx)
                
                for it in self.verse_number_items.values():
                    it.is_selected = False
                    it.update()
                
                if not hasattr(self, "selected_refs"): self.selected_refs = set()
                self.selected_refs.clear()
                self.selected_verse_items = []
                
                for i in range(start, end + 1):
                    ref = flat_refs[i]
                    self.selected_refs.add(ref)
                    it = self.verse_number_items.get(ref)
                    if it:
                        it.is_selected = True
                        it.update()
                        self.selected_verse_items.append(it)

    def _on_verse_num_dragged(self, item, dx):
        if item.ref not in self.selected_refs:
            self._on_verse_num_clicked(item, False)
            
        self._was_dragged = True 
        
        tabs_diff = round(dx / self.tab_size)
        
        if not hasattr(self, "_last_drag_tabs_diff") or self._last_drag_tabs_diff != tabs_diff:
            self._last_drag_tabs_diff = tabs_diff
            
            doc = self.main_text_item.document()
            layout = doc.documentLayout()
            verse_indents = self.study_manager.data.get("verse_indent", {})
            
            for ref in self.selected_refs:
                if not hasattr(self, "_drag_start_indents"):
                    self._drag_start_indents = {}
                
                if ref not in self._drag_start_indents:
                    self._drag_start_indents[ref] = verse_indents.get(ref, 0)
                
                start_indent = self._drag_start_indents[ref]
                new_indent = max(0, start_indent + tabs_diff)
                
                self.study_manager.data["verse_indent"][ref] = new_indent
                
                if ref in self.verse_pos_map:
                    pos = self.verse_pos_map[ref]
                    block = doc.findBlock(pos)
                    fmt = block.blockFormat()
                    fmt.setLeftMargin(new_indent * self.tab_size)
                    
                    cursor = QTextCursor(block)
                    cursor.setBlockFormat(fmt)

            self._update_all_verse_number_positions()
            self._render_study_overlays()
            if self.strongs_enabled:
                self.renderer._render_strongs_overlays()

    def _update_all_verse_number_positions(self):
        doc = self.main_text_item.document()
        layout = doc.documentLayout()
        verse_indents = self.study_manager.data.get("verse_indent", {})
        
        for ref, it in self.verse_number_items.items():
            if ref in self.verse_pos_map:
                pos = self.verse_pos_map[ref]
                block = doc.findBlock(pos)
                rect = layout.blockBoundingRect(block)
                
                indent_level = verse_indents.get(ref, 0)
                it.setPos(self.side_margin + (indent_level * self.tab_size), rect.top())

    def _on_verse_num_released(self):
        self.study_manager.save_study()
        
        if hasattr(self, "_last_drag_tabs_diff"):
            del self._last_drag_tabs_diff
        if hasattr(self, "_drag_start_indents"):
            del self._drag_start_indents
            
        if hasattr(self, "_was_dragged") and self._was_dragged:
            self._clear_verse_selection()
            self._was_dragged = False
            
        self.studyDataChanged.emit()

    def _get_heading_at_pos(self, scene_pos):
        doc_pos = self.main_text_item.mapFromScene(scene_pos)
        for rect, h_type, h_text in self.heading_rects:
            if rect.contains(doc_pos):
                return (h_type, h_text)
        return None

    def _show_suggested_symbols_dialog(self, heading_data):
        h_type, h_text = heading_data
        top_words = self.strongs_manager.get_top_strongs_words(h_type, h_text, self.loader.flat_verses)
        
        if top_words:
            dialog = SuggestedSymbolsDialog(top_words, h_text, self.views()[0])
            dialog.exec()

    def _start_divider_drag(self, pos):
        item = self.sender()
        from src.scene.components.reader_items import OutlineDividerItem
        from PySide6.QtGui import QPen
        from PySide6.QtWidgets import QGraphicsLineItem
        
        if not isinstance(item, OutlineDividerItem): return
        
        self.is_dragging_divider = True
        self.drag_divider_item = item
        
        parent = item.parent_node
        idx = item.split_idx
        loader = self.loader
        
        if idx == -2: 
            self.drag_bounds_min = 0.0 
            if parent.get("children"):
                self.drag_bounds_max = loader.get_verse_index(parent["children"][0]["range"]["end"]) - 1.0
            else:
                self.drag_bounds_max = loader.get_verse_index(parent["range"]["end"]) - 1.0
            
            start_idx = loader.get_verse_index(parent["range"]["start"])
            orig_split_idx = (start_idx - 1.0) if int(start_idx) == start_idx else (start_idx - 0.1)
            self.drag_divider_original_idx = orig_split_idx
            
            preceding, succeeding = self.study_manager.outline_manager.get_nearest_split_indices(orig_split_idx)
            self.drag_hard_min = preceding
            self.drag_hard_max = succeeding
            
        elif idx == -3: 
            if parent.get("children"):
                self.drag_bounds_min = loader.get_verse_index(parent["children"][-1]["range"]["start"])
            else:
                self.drag_bounds_min = loader.get_verse_index(parent["range"]["start"])
                
            self.drag_bounds_max = float(len(loader.flat_verses) - 1) 
            
            orig_split_idx = loader.get_verse_index(parent["range"]["end"])
            self.drag_divider_original_idx = orig_split_idx
            
            preceding, succeeding = self.study_manager.outline_manager.get_nearest_split_indices(orig_split_idx)
            self.drag_hard_min = preceding
            self.drag_hard_max = succeeding

        elif idx >= 0: 
            children = parent.get("children", [])
            if idx < len(children) - 1:
                c1 = children[idx]
                c2 = children[idx+1]
                
                sibling_min = self.loader.get_verse_index(c1["range"]["start"])
                sibling_max = self.loader.get_verse_index(c2["range"]["end"]) - 1.0
                
                current_split_idx_val = self.loader.get_verse_index(c1["range"]["end"])
                self.drag_divider_original_idx = current_split_idx_val
                
                preceding, succeeding = self.study_manager.outline_manager.get_nearest_split_indices(current_split_idx_val)
                
                self.drag_bounds_min = sibling_min
                self.drag_bounds_max = sibling_max
                self.drag_hard_min = preceding
                self.drag_hard_max = succeeding
        
        pen = QPen(QColor("#005a9e"))
        pen.setWidth(2)
        self.drag_divider_ghost = QGraphicsLineItem(self.side_margin, pos.y(), self.sceneRect().width() - 10, pos.y())
        self.drag_divider_ghost.setPen(pen)
        self.drag_divider_ghost.setZValue(100)
        self.addItem(self.drag_divider_ghost)
        
        self.views()[0].setCursor(Qt.SizeVerCursor)
