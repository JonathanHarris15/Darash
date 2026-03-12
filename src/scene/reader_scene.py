from PySide6.QtWidgets import QGraphicsScene
from PySide6.QtCore import Qt, QRectF, QTimer, Signal, QPointF
from PySide6.QtGui import QColor, QFont, QCursor, QTextCursor, QAction

from src.core.verse_loader import VerseLoader
from src.managers.study_manager import StudyManager
from src.managers.symbol_manager import SymbolManager
from src.managers.strongs_manager import StrongsManager
from src.core.constants import SCROLL_SENSITIVITY, OT_BOOKS, NT_BOOKS
from src.utils.path_utils import get_resource_path

from src.scene.scene_input_handler import SceneInputHandler
from src.scene.scene_overlay_manager import SceneOverlayManager
from src.scene.layout_engine import LayoutEngine
from src.scene.renderer import OverlayRenderer
from src.scene.scene_search_manager import SceneSearchManager
from src.scene.scene_interaction_manager import SceneInteractionManager
from src.scene.scene_indentation_manager import SceneIndentationManager
from src.scene.scene_outline_manager import SceneOutlineManager
from src.scene.scene_settings_manager import SceneSettingsManager
from src.scene.scene_state_manager import SceneStateManager
from src.scene.components.reader_items import NoFocusTextItem
from src.core.theme import Theme
import bisect

class ReaderScene(QGraphicsScene):
    """Bible reader rendering engine. Facade for specialized sub-managers."""
    scrollChanged = Signal(int); layoutChanged = Signal(int); currentReferenceChanged = Signal(str)
    settingsPreview = Signal(int, float); layoutStarted = Signal(); layoutFinished = Signal()
    searchResultsFound = Signal(int); searchStatusUpdated = Signal(int, int); sectionsUpdated = Signal(list, int)
    bookmarksUpdated = Signal(); studyDataChanged = Signal(); outlineCreated = Signal(str)
    noteOpenRequested = Signal(str, str); showMarkPopup = Signal(QPointF, str)
    showSuggestedSymbols = Signal(list, str); showOutlineDialog = Signal(str, str)
    showStrongsTooltip = Signal(QPointF, str); showStrongsVerboseDialog = Signal(str, dict, list)

    def __init__(self, parent=None, shared_resources=None):
        super().__init__(parent)
        self.scroll_y, self.target_scroll_y, self.last_mouse_scene_pos = 0.0, 0.0, QPointF()
        self._wheel_accumulator, self._zoom_accumulator = 0, 0
        self.font_size, self.line_spacing, self.font_family = Theme.SIZE_READER_DEFAULT, 1.5, Theme.FONT_READER
        self.scroll_sens = SCROLL_SENSITIVITY
        self.verse_num_font_size, self.side_margin, self.tab_size = Theme.SIZE_READER_DEFAULT - 4, 40, 40
        self.arrow_opacity, self.verse_mark_size, self.logical_mark_opacity = 0.6, 18, 0.5
        self.sentence_break_enabled = self.target_sentence_break_enabled = False
        
        if shared_resources:
            self.loader = shared_resources.get('loader'); self.study_manager = shared_resources.get('study_manager')
            self.symbol_manager = shared_resources.get('symbol_manager'); self.strongs_manager = shared_resources.get('strongs_manager')
        else:
            self.loader = VerseLoader(); self.study_manager = StudyManager(loader=self.loader); self.symbol_manager = SymbolManager()
            self.strongs_manager = StrongsManager(); self.strongs_manager.index_usages(self.loader)
        
        self.pixmap_cache, self.verse_number_items, self.sentence_handle_items = {}, {}, {}
        self.selected_verse_items, self.selected_refs, self.last_clicked_verse_idx = [], set(), -1
        self.main_text_item = NoFocusTextItem(); self.main_text_item.setAcceptHoverEvents(True)
        self.main_text_item.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.addItem(self.main_text_item)
        
        self.strongs_enabled, self.strongs_overlay_items = False, []
        self.outlines_enabled, self.active_outline_id, self.outline_overlay_items = False, None, []
        self.ghost_line_item = self.is_dragging_divider = self.drag_divider_item = self.drag_divider_ghost = None
        
        self.verse_pos_map, self.verse_stack_end_pos, self.verse_y_map, self.pos_verse_map = {}, {}, {}, []
        self.search_results, self.search_marks_y, self.current_search_idx = [], [], -1
        self.open_editors, self.flash_items = {}, []
        self.study_overlay_items, self.search_overlay_items, self.heading_rects, self._pending_headings = [], [], [], []
        self.is_drawing_arrow, self.arrow_start_key, self.arrow_start_center, self.temp_arrow_item = False, None, None, None
        self.last_width, self.view_height, self.total_height, self.layout_version = 800, 600, 0, 0
        self.last_emitted_ref = ""

        self.state_manager = SceneStateManager(self); self.layout_engine = LayoutEngine(self); self.renderer = OverlayRenderer(self)
        self.input_handler = SceneInputHandler(self); self.overlay_manager = SceneOverlayManager(self)
        self.search_manager = SceneSearchManager(self); self.interaction_manager = SceneInteractionManager(self)
        self.indentation_manager = SceneIndentationManager(self); self.outline_manager = SceneOutlineManager(self)
        self.settings_manager = SceneSettingsManager(self)

        self.flash_timer = QTimer(self); self.flash_timer.setInterval(50); self.flash_timer.timeout.connect(self.renderer.update_flash_fade)
        self.layout_timer = QTimer(self); self.layout_timer.setSingleShot(True); self.layout_timer.setInterval(50); self.layout_timer.timeout.connect(self.settings_manager.apply_layout_changes)
        
        self.settings_manager.load_settings(); self.settings_manager.update_fonts()
        self.text_color = QColor(self.study_manager.data["settings"].get("text_color", Theme.TEXT_PRIMARY))
        self.ref_color = QColor(self.study_manager.data["settings"].get("ref_color", Theme.ACCENT_PRIMARY))
        self.logical_mark_color = QColor(self.study_manager.data["settings"].get("logical_mark_color", "#ffffff"))
        self.setBackgroundBrush(QColor(self.study_manager.data["settings"].get("bg_color", Theme.BG_PRIMARY)))

    @property
    def virtual_scroll_y(self): return self.state_manager.virtual_scroll_y
    @virtual_scroll_y.setter
    def virtual_scroll_y(self, v): self.state_manager.virtual_scroll_y = v
    @property
    def chunk_start_idx(self): return self.state_manager.chunk_start_idx
    @chunk_start_idx.setter
    def chunk_start_idx(self, v): self.state_manager.chunk_start_idx = v
    @property
    def chunk_end_idx(self): return self.state_manager.chunk_end_idx
    @chunk_end_idx.setter
    def chunk_end_idx(self, v): self.state_manager.chunk_end_idx = v
    @property
    def target_virtual_scroll_y(self): return self.state_manager.target_virtual_scroll_y
    @target_virtual_scroll_y.setter
    def target_virtual_scroll_y(self, v): self.state_manager.target_virtual_scroll_y = v
    @property
    def CHUNK_SIZE(self): return self.state_manager.CHUNK_SIZE

    def _update_item_visibility(self):
        for item in self.study_overlay_items + self.search_overlay_items + self.outline_overlay_items:
            item.setVisible(self.renderer._is_rect_visible(item.sceneBoundingRect()))

    def recalculate_layout(self, w, center_verse_idx=None): self.layout_engine.recalculate_layout(w, center_verse_idx)
    def render_verses(self): self.renderer.render_verses()
    def _render_outline_overlays(self): self.renderer._render_outline_overlays()
    def set_outlines_enabled(self, e):
        self.outlines_enabled = e; self._clear_outline_overlays(); self.renderer._render_outline_overlays() if e else None
    def set_active_outline(self, i): self.active_outline_id = i; self.renderer._render_outline_overlays()
    def _clear_outline_overlays(self):
        for it in list(self.outline_overlay_items): self.removeItem(it) if it.scene() == self else None
        self.outline_overlay_items.clear()
        if self.ghost_line_item: self.removeItem(self.ghost_line_item) if self.ghost_line_item.scene() == self else None; self.ghost_line_item = None
    def set_strongs_enabled(self, e): self.strongs_enabled = e; self._clear_strongs_overlays() if not e else self.render_verses()
    def _clear_strongs_overlays(self):
        for it in list(self.strongs_overlay_items): self.removeItem(it) if it.scene() == self else None
        self.strongs_overlay_items.clear()
    def _render_study_overlays(self): self.overlay_manager.render_study_overlays()
    def _render_search_overlays(self): self.renderer._render_search_overlays()
    def handle_search(self, t): self.search_manager.handle_search(t)
    def next_match(self): self.search_manager.next_match()
    def prev_match(self): self.search_manager.prev_match()
    def clear_search(self): self.search_manager.clear_search()

    def _get_text_rects(self, p, l): return self.layout_engine._get_text_rects(p, l)
    def _get_word_offset_in_verse(self, v, w): return self.layout_engine._get_word_offset_in_verse(v, w)
    def _get_word_center(self, k): return self.layout_engine._get_word_center(k)
    def _create_symbol_item(self, n, r, o): return self.renderer.create_symbol_item(n, r, o)
    def _is_rect_visible(self, r): return self.renderer._is_rect_visible(r)
    def _get_ref_from_pos(self, p): return self.layout_engine._get_ref_from_pos(p)
    def _on_verse_num_clicked(self, v, s): self.interaction_manager.on_verse_num_clicked(v, s)
    def _clear_verse_selection(self): self.interaction_manager.clear_verse_selection()
    def _on_verse_num_context_menu(self, v, p): self.interaction_manager.on_verse_num_context_menu(v, p)
    
    def _clear_selection(self):
        self.main_text_item.setTextCursor(QTextCursor(self.main_text_item.document()))
        self.current_selection = None
        self.render_verses()

    def open_note_by_key(self, key, ref):
        self.noteOpenRequested.emit(key, ref)

    def _get_word_idx_from_pos(self, v, r): return self.layout_engine._get_word_idx_from_pos(v, r)
    def _get_word_key_at_pos(self, p): return self.layout_engine._get_word_key_at_pos(p)
    def _get_strongs_at_pos(self, p): return self.layout_engine._get_strongs_at_pos(p)
    def _apply_symbol_at_mouse(self, k): self.interaction_manager.apply_symbol_at_mouse(k)
    def save_settings(self): self.settings_manager.save_settings()
    def apply_layout_changes(self): self.settings_manager.apply_layout_changes()

    def set_scroll_y(self, v): self.state_manager.set_scroll_y(v)
    def jump_to(self, b, c, v="1"):
        idx = self.loader.get_verse_index(f"{b} {c}:{v if v else '1'}"); self.set_scroll_y(idx) if idx != -1 else None; self.flash_verse(f"{b} {c}:{v if v else '1'}")
    def flash_verse(self, r): self.renderer.flash_verse(r)
    def setSceneRect(self, *args):
        rect = args[0] if len(args)==1 else QRectF(*args); self.state_manager.handle_resize(rect.width(), rect.height())
    def update_scene_rect_only(self): super().setSceneRect(QRectF(0, self.scroll_y, self.last_width, self.view_height))
    
    def wheelEvent(self, e):
        if not self.input_handler.handle_wheel(e):
            super().wheelEvent(e)

    def keyPressEvent(self, e):
        if not self.input_handler.handle_key_press(e):
            super().keyPressEvent(e)

    def mousePressEvent(self, e):
        self.input_handler.handle_mouse_press(e)
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self.input_handler.handle_mouse_release(e)
        super().mouseReleaseEvent(e)

    def mouseMoveEvent(self, e):
        self.input_handler.handle_mouse_move(e)
        super().mouseMoveEvent(e)

    def mouseDoubleClickEvent(self, e):
        if not self.input_handler.handle_mouse_double_click(e):
            super().mouseDoubleClickEvent(e)

    def contextMenuEvent(self, e):
        if not self.input_handler.handle_context_menu(e):
            super().contextMenuEvent(e)
