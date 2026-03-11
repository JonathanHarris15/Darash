from PySide6.QtWidgets import QGraphicsScene
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

from src.scene.scene_search_manager import SceneSearchManager
from src.scene.scene_interaction_manager import SceneInteractionManager
from src.scene.scene_indentation_manager import SceneIndentationManager
from src.scene.scene_outline_manager import SceneOutlineManager
from src.scene.scene_settings_manager import SceneSettingsManager

from src.scene.components.reader_items import NoFocusTextItem, VerseNumberItem, SentenceHandleItem

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
from src.utils.menu_utils import create_menu

class ReaderScene(QGraphicsScene):
    """
    The main rendering engine for the Bible reader.
    Acts as a facade coordinating specialized sub-managers.
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
    noteOpenRequested = Signal(str, str) # note_key, ref
    
    # Domain-safe UI signals
    showMarkPopup = Signal(QPointF, str) # global_pos, ref
    showSuggestedSymbols = Signal(list, str) # top_words, heading_text
    showOutlineDialog = Signal(str, str) # start_ref, end_ref
    showStrongsTooltip = Signal(QPointF, str) # global_pos, text
    showStrongsVerboseDialog = Signal(str, dict, list) # sn, entry, usages

    def __init__(self, parent=None, shared_resources=None):
        super().__init__(parent)
        
        self.scroll_y = 0.0
        self.target_scroll_y = 0.0
        self.last_mouse_scene_pos = QPointF()
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
        self.sentence_break_enabled = False
        self.target_sentence_break_enabled = False
        if shared_resources:
            self.loader = shared_resources.get('loader')
            self.study_manager = shared_resources.get('study_manager')
            self.symbol_manager = shared_resources.get('symbol_manager')
            self.strongs_manager = shared_resources.get('strongs_manager')
        else:
            self.loader = VerseLoader()
            self.study_manager = StudyManager(loader=self.loader)
            self.symbol_manager = SymbolManager()
            self.strongs_manager = StrongsManager()
            self.strongs_manager.index_usages(self.loader)
        
        self.pixmap_cache = {} 
        self.verse_number_items = {} 
        self.sentence_handle_items = {}
        self.selected_verse_items = []
        self.selected_refs = set()
        self.last_clicked_verse_idx = -1
        
        self.main_text_item = NoFocusTextItem()
        self.main_text_item.setAcceptHoverEvents(True)
        self.main_text_item.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.addItem(self.main_text_item)
        
        self.strongs_enabled = False
        self.strongs_overlay_items = []
        
        self.outlines_enabled = False
        self.active_outline_id = None
        self.outline_overlay_items = []
        self.ghost_line_item = None
        
        self.is_dragging_divider = False
        self.drag_divider_item = None
        self.drag_divider_ghost = None
        self.drag_bounds_min = 0
        self.drag_bounds_max = 0
        self.drag_hard_min = None
        self.drag_hard_max = None
        
        self.verse_pos_map = {}
        self.verse_stack_end_pos = {} # Map of ref -> position of the last block in stack
        self.verse_y_map = {} # ref -> (y_top, y_bottom)
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
        
        self.last_width = 800
        self.view_height = 600
        self.total_height = 0
        self.layout_version = 0 
        
        self.virtual_scroll_y = 0.0 # 0.0 to float(len(total_verses))
        self.target_virtual_scroll_y = 0.0
        self.chunk_start_idx = 0
        self.chunk_end_idx = 0
        self.CHUNK_SIZE = 400 
        
        self._wheel_accumulator = 0.0
        self._zoom_accumulator = 0.0

        # Specialized Managers
        self.layout_engine = LayoutEngine(self)
        self.renderer = OverlayRenderer(self)
        self.input_handler = SceneInputHandler(self)
        self.overlay_manager = SceneOverlayManager(self)
        self.search_manager = SceneSearchManager(self)
        self.interaction_manager = SceneInteractionManager(self)
        self.indentation_manager = SceneIndentationManager(self)
        self.outline_manager = SceneOutlineManager(self)
        self.settings_manager = SceneSettingsManager(self)

        self.current_selection = None
        
        self._init_timers()
        self.settings_manager.load_settings()
        self.settings_manager.update_fonts()
        
        self.text_color = QColor(self.study_manager.data["settings"].get("text_color", TEXT_COLOR.name()))
        self.ref_color = QColor(self.study_manager.data["settings"].get("ref_color", REFERENCE_COLOR.name()))
        self.logical_mark_color = QColor(self.study_manager.data["settings"].get("logical_mark_color", LOGICAL_MARK_COLOR.name()))
        bg_color = QColor(self.study_manager.data["settings"].get("bg_color", APP_BACKGROUND_COLOR.name()))
        self.setBackgroundBrush(bg_color)

    def _init_timers(self):
        self.flash_timer = QTimer(self)
        self.flash_timer.setInterval(50)
        self.flash_timer.timeout.connect(self.renderer.update_flash_fade)
        
        self.layout_timer = QTimer(self)
        self.layout_timer.setSingleShot(True)
        self.layout_timer.setInterval(LAYOUT_DEBOUNCE_INTERVAL)
        self.layout_timer.timeout.connect(self.settings_manager.apply_layout_changes)
        
        self.scroll_timer = QTimer(self)
        self.scroll_timer.setInterval(16)
        self.scroll_timer.timeout.connect(self.update_scroll_step)

    def _is_rect_visible(self, r): return self.renderer._is_rect_visible(r)

    def _update_item_visibility(self):
        for item in self.study_overlay_items + self.search_overlay_items + self.outline_overlay_items:
            item.setVisible(self._is_rect_visible(item.sceneBoundingRect()))

    def _get_ref_from_pos(self, pos): return self.layout_engine.get_ref_from_pos(pos)
    def _get_sentence_ref_at_pos(self, scene_pos): return self.layout_engine.get_sentence_ref_at_pos(scene_pos)
    def _get_text_rects(self, start, length): return get_text_rects(self.main_text_item, start, length)
    def _get_word_offset_in_verse(self, v_data, w_idx): return get_word_offset_in_verse(v_data, w_idx)
    def _get_word_idx_from_pos(self, v_data, pos): return get_word_idx_from_pos(v_data, pos)

    def recalculate_layout(self, width: float, center_verse_idx: int = None) -> None:
        self.layout_engine.recalculate_layout(width, center_verse_idx=center_verse_idx)

    def apply_layout_changes(self): self.settings_manager.apply_layout_changes()
    def render_verses(self) -> None: self.renderer.render_verses()
    def _render_outline_overlays(self): self.renderer._render_outline_overlays()
    def _render_search_overlays(self): self.renderer._render_search_overlays()

    def set_outlines_enabled(self, enabled: bool):
        self.outlines_enabled = enabled
        if not enabled: self._clear_outline_overlays()
        else: self.renderer._render_outline_overlays()

    def set_active_outline(self, outline_id: str):
        self.active_outline_id = outline_id; self.renderer._render_outline_overlays()

    def _clear_outline_overlays(self):
        for it in self.outline_overlay_items:
            if it.scene() == self: self.removeItem(it)
        self.outline_overlay_items.clear()
        if self.ghost_line_item:
            if self.ghost_line_item.scene() == self: self.removeItem(self.ghost_line_item)
            self.ghost_line_item = None

    def set_strongs_enabled(self, enabled: bool):
        self.strongs_enabled = enabled
        if not enabled: self._clear_strongs_overlays()
        else: self.render_verses()

    def _clear_strongs_overlays(self):
        for it in self.strongs_overlay_items:
            if it.scene() == self: self.removeItem(it)
        self.strongs_overlay_items.clear()

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
                    if rects: return rects[0].center()
        return None

    def _render_study_overlays(self): self.overlay_manager.render_study_overlays()
    def _create_symbol_item(self, name, rect, opacity): return self.renderer.create_symbol_item(name, rect, opacity)
    def open_note_by_key(self, note_key, ref): self.noteOpenRequested.emit(note_key, ref)
    def _on_note_editor_finished(self, r, ed, key): self.interaction_manager.on_note_editor_finished(r, ed, key)

    def handle_search(self, text: str): self.search_manager.handle_search(text)
    def scroll_to_current_match(self): self.search_manager.scroll_to_current_match()
    def next_match(self): self.search_manager.next_match()
    def prev_match(self): self.search_manager.prev_match()
    def clear_search(self): self.search_manager.clear_search()

    def contextMenuEvent(self, event):
        view = self.views()[0]; global_pos = event.screenPos()
        h_data = self.interaction_manager.get_heading_at_pos(event.scenePos())
        if h_data:
            menu = create_menu(view); suggest_act = QAction("Get suggested symbols", menu)
            suggest_act.triggered.connect(lambda: self.interaction_manager.show_suggested_symbols_dialog(h_data))
            menu.addAction(suggest_act); menu.exec(global_pos); event.accept(); return
        item = self.itemAt(event.scenePos(), view.transform())
        if isinstance(item, VerseNumberItem):
            item.contextMenuRequested.emit(QPointF(global_pos)); event.accept(); return
        cursor = self.main_text_item.textCursor()
        if not cursor.hasSelection():
            pos = self.main_text_item.document().documentLayout().hitTest(self.main_text_item.mapFromScene(event.scenePos()), Qt.FuzzyHit)
            if pos != -1:
                cursor.setPosition(pos); cursor.select(QTextCursor.WordUnderCursor); self.main_text_item.setTextCursor(cursor)
        if cursor.hasSelection():
            self.current_selection = (cursor.selectionStart(), cursor.selectionEnd() - cursor.selectionStart())
            self.showMarkPopup.emit(global_pos, self._get_ref_from_pos(cursor.selectionStart()))
            self.render_verses(); event.accept(); return
        super().contextMenuEvent(event)

    def mouseReleaseEvent(self, event):
        if self.outline_manager.handle_mouse_release(event): event.accept(); return
        if event.button() != Qt.LeftButton: super().mouseReleaseEvent(event); return
        cursor = self.main_text_item.textCursor()
        if cursor.hasSelection():
            self.current_selection = (cursor.selectionStart(), cursor.selectionEnd() - cursor.selectionStart())
            view = self.views()[0]; screen_pos = view.viewport().mapToGlobal(view.mapFromScene(event.scenePos()))
            self.showMarkPopup.emit(screen_pos, self._get_ref_from_pos(cursor.selectionStart()))
        else: self.current_selection = None
        self.render_verses(); super().mouseReleaseEvent(event)

    def _clear_verse_selection(self): self.interaction_manager.clear_verse_selection()
    def _on_verse_num_context_menu(self, item, screen_pos): self.interaction_manager.on_verse_num_context_menu(item, screen_pos)
    def _set_selected_verse_mark(self, mark_type): self.interaction_manager.set_selected_verse_mark(mark_type)

    def wheelEvent(self, event) -> None:
        if self.input_handler.handle_wheel(event): event.accept(); return
        modifiers = event.modifiers(); delta = event.delta() 
        if delta == 0: super().wheelEvent(event); return
        if modifiers & (Qt.ControlModifier | Qt.AltModifier):
            self._zoom_accumulator += delta
            while abs(self._zoom_accumulator) >= 120:
                step = 120 if self._zoom_accumulator > 0 else -120
                if modifiers & Qt.ControlModifier: self.target_font_size = max(8, min(72, self.target_font_size + (2 if step > 0 else -2)))
                elif modifiers & Qt.AltModifier: self.target_line_spacing = max(1.0, min(3.0, self.target_line_spacing + (0.1 if step > 0 else -0.1)))
                self._zoom_accumulator -= step
            self.settingsPreview.emit(self.target_font_size, self.target_line_spacing); self.layout_timer.start(); event.accept(); return
        self._wheel_accumulator += delta
        while abs(self._wheel_accumulator) >= 30:
            step = 30 if self._wheel_accumulator > 0 else -30
            move = -(step / 120.0) * (self.scroll_sens / 100.0) 
            self.target_virtual_scroll_y = max(0, min(len(self.loader.flat_verses) - 1, self.target_virtual_scroll_y + move))
            self._wheel_accumulator -= step
        if not self.scroll_timer.isActive(): self.scroll_timer.start()
        event.accept(); super().wheelEvent(event) 

    def mousePressEvent(self, event):
        item = self.itemAt(event.scenePos(), self.views()[0].transform())
        if not isinstance(item, VerseNumberItem) and not isinstance(item, SentenceHandleItem): self._clear_verse_selection()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if not self.outline_manager.handle_double_click(event): super().mouseDoubleClickEvent(event)

    def _clear_selection(self):
        cursor = self.main_text_item.textCursor(); cursor.clearSelection(); self.main_text_item.setTextCursor(cursor); self.current_selection = None

    def _on_add_bookmark_requested(self): self.interaction_manager.on_add_bookmark_requested()
    def _on_add_note_requested(self): self.interaction_manager.on_add_note_requested()
    def keyPressEvent(self, event):
        if not self.input_handler.handle_key_press(event): super().keyPressEvent(event)

    def mouseMoveEvent(self, event):
        self.last_mouse_scene_pos = event.scenePos()
        if self.outline_manager.handle_mouse_move(event): super().mouseMoveEvent(event); return
        self.input_handler.handle_mouse_move(event); super().mouseMoveEvent(event)

    def keyReleaseEvent(self, event):
        if not self.input_handler.handle_key_release(event): super().keyReleaseEvent(event)

    def _apply_symbol_at_mouse(self, number_key): self.interaction_manager.apply_symbol_at_mouse(number_key)

    def check_chunk_boundaries(self):
        buffer = 100 
        if (self.virtual_scroll_y < self.chunk_start_idx + buffer or self.virtual_scroll_y > self.chunk_end_idx - buffer):
            if (self.chunk_start_idx > 0 and self.virtual_scroll_y < self.chunk_start_idx + buffer) or \
               (self.chunk_end_idx < len(self.loader.flat_verses) and self.virtual_scroll_y > self.chunk_end_idx - buffer):
                self.recalculate_layout(self.last_width, center_verse_idx=int(self.virtual_scroll_y))

    def _sync_physical_scroll(self):
        v_idx = int(self.virtual_scroll_y); frac = self.virtual_scroll_y - v_idx
        if 0 <= v_idx < len(self.loader.flat_verses):
            ref = self.loader.flat_verses[v_idx]['ref']
            if ref in self.verse_y_map:
                y_top, y_bottom = self.verse_y_map[ref]
                self.scroll_y = y_top + (frac * (y_bottom - y_top))
        super().setSceneRect(QRectF(0, self.scroll_y, self.last_width, self.view_height)); self.render_verses()
        self.scrollChanged.emit(int(self.virtual_scroll_y)); self._update_item_visibility()

    def set_scroll_y(self, value: float) -> None:
        self.target_virtual_scroll_y = float(value); self.virtual_scroll_y = self.target_virtual_scroll_y
        self.check_chunk_boundaries(); self._sync_physical_scroll()

    def update_scroll_step(self) -> None:
        diff = self.target_virtual_scroll_y - self.virtual_scroll_y
        if abs(diff) < 0.001: self.virtual_scroll_y = self.target_virtual_scroll_y; self.scroll_timer.stop()
        else: self.virtual_scroll_y += diff * 0.15
        self.check_chunk_boundaries(); self._sync_physical_scroll()

    def setSceneRect(self, *args) -> None:
        if len(args) == 1: rect = args[0]
        else: rect = QRectF(args[0], args[1], args[2], args[3])
        if abs(rect.width() - self.last_width) > 2:
            self.last_width = rect.width(); self.recalculate_layout(self.last_width, center_verse_idx=int(self.virtual_scroll_y))
            self._render_study_overlays(); self._render_search_overlays()
        self.view_height = rect.height()
        super().setSceneRect(QRectF(0, self.scroll_y, self.last_width, self.view_height)); self.render_verses()

    def jump_to(self, book: str, chapter: str, verse: str = "1") -> None:
        if verse is None: verse = "1"
        target_idx = self.loader.get_verse_index(f"{book} {chapter}:{verse}")
        if target_idx != -1: self.set_scroll_y(target_idx); self.flash_verse(f"{book} {chapter}:{verse}")

    def flash_verse(self, ref): self.renderer.flash_verse(ref)
    def _on_verse_num_clicked(self, item, shift): self.interaction_manager.on_verse_num_clicked(item, shift)
    def _show_suggested_symbols_dialog(self, heading_data): self.interaction_manager.show_suggested_symbols_dialog(heading_data)
    def _start_divider_drag(self, pos): self.outline_manager.start_divider_drag(pos)

    def _get_word_key_at_pos(self, scene_pos):
        pos = self.main_text_item.document().documentLayout().hitTest(self.main_text_item.mapFromScene(scene_pos), Qt.FuzzyHit)
        if pos != -1:
            ref = self._get_ref_from_pos(pos)
            if ref:
                verse_data = self.loader.get_verse_by_ref(ref)
                if verse_data:
                    word_idx = self._get_word_idx_from_pos(verse_data, pos - self.verse_pos_map[ref])
                    if word_idx != -1 and any(c.isalnum() for c in verse_data['tokens'][word_idx][0]):
                        return f"{verse_data['book']}|{verse_data['chapter']}|{verse_data['verse_num']}|{word_idx}"
        return None

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
                        if len(token) > 1 and token[1]: return token[1], None
        return None, None
