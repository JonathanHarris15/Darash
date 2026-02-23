from PySide6.QtWidgets import (
    QGraphicsScene, QGraphicsPixmapItem, QGraphicsRectItem, QDialog, 
    QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsItem, QMenu
)
from PySide6.QtCore import Qt, QRectF, QTimer, Signal, QPointF
from PySide6.QtGui import (
    QColor, QFont, QPixmap, QBrush, QPen, QTextCursor, QCursor,
    QTextBlockFormat, QTextCharFormat, QAction, QClipboard, QGuiApplication
)
from src.verse_loader import VerseLoader
from src.study_manager import StudyManager
from src.mark_popup import MarkPopup
from src.note_editor import NoteEditor
from src.symbol_manager import SymbolManager
from src.reader_items import NoFocusTextItem, NoteIcon, ArrowItem, VerseNumberItem, OutlineDividerItem
from src.reader_utils import (
    get_word_idx_from_pos, get_text_rects, 
    get_word_offset_in_verse
)
from src.strongs_manager import StrongsManager
from src.strongs_ui import StrongsTooltip, StrongsVerboseDialog
from src.suggested_symbols_dialog import SuggestedSymbolsDialog
from src.scene_input_handler import SceneInputHandler
from src.scene_overlay_manager import SceneOverlayManager
from src.constants import (
    APP_BACKGROUND_COLOR, TEXT_COLOR, REFERENCE_COLOR,
    DEFAULT_FONT_FAMILY, VERSE_FONT_FAMILY, DEFAULT_FONT_SIZE, 
    HEADER_FONT_SIZE, CHAPTER_FONT_SIZE,
    LINE_SPACING_DEFAULT, SCROLL_SENSITIVITY, SIDE_MARGIN, TOP_MARGIN,
    TAB_SIZE_DEFAULT, ARROW_OPACITY_DEFAULT, VERSE_MARK_SIZE_DEFAULT,
    LOGICAL_MARK_OPACITY_DEFAULT, LAYOUT_DEBOUNCE_INTERVAL, SEARCH_HIGHLIGHT_COLOR, SELECTION_COLOR,
    BIBLE_SECTIONS, LOGICAL_MARK_COLOR
)
import bisect
import os
import math
import time

from src.outline_dialog import OutlineDialog

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
    outlineCreated = Signal(str) # node_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.input_handler = SceneInputHandler(self)
        self.overlay_manager = SceneOverlayManager(self)
        
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
        self.pixmap_cache = {} # Cache for symbol pixmaps
        self.verse_number_items = {} # ref: VerseNumberItem
        self.selected_verse_items = []
        self.selected_refs = set()
        self.last_clicked_verse_idx = -1
        
        # Unified Text Item
        self.main_text_item = NoFocusTextItem()
        self.main_text_item.setAcceptHoverEvents(True)
        self.main_text_item.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.addItem(self.main_text_item)
        
        # Strongs UI
        self.strongs_enabled = False
        self.strongs_tooltip = StrongsTooltip()
        self.strongs_overlay_items = []
        
        # Outlines UI
        self.outlines_enabled = False
        self.active_outline_id = None
        self.outline_overlay_items = []
        self.ghost_line_item = None
        
        self.is_dragging_divider = False
        self.drag_divider_item = None
        self.drag_divider_ghost = None
        self.drag_min_idx = float('-inf')
        self.drag_max_idx = float('inf')
        
        # Popups
        self.mark_popup = MarkPopup()
        self.mark_popup.markSelected.connect(self._on_mark_selected)
        self.mark_popup.addNoteRequested.connect(self._on_add_note_requested)
        self.mark_popup.addBookmarkRequested.connect(self._on_add_bookmark_requested)
        self.mark_popup.createOutlineRequested.connect(self._create_outline_from_selection)
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
        
        self.heading_rects = [] # (QRectF, "book"|"chapter", text)
        self._pending_headings = [] # (block_num, type, text)
        
        # Arrow Drawing State
        self.is_drawing_arrow = False
        self.arrow_start_key = None
        self.arrow_start_center = None
        self.temp_arrow_item = None
        
        # Timer Management
        self._init_timers()
        
        # Appearance Initialization (Load from study if available)
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
        self.layout_version = 0 # For cache invalidation in pathfinder
        
        # Wheel/Zoom accumulators to discretize trackpad input
        self._wheel_accumulator = 0.0
        self._zoom_accumulator = 0.0

    def load_settings(self):
        """Loads appearance settings from study manager or defaults."""
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
        
        # Targets for smooth transitions/delayed apply
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
        """Saves current appearance settings to study manager."""
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

    def _update_fonts(self):
        """Updates the internal font objects based on current size settings."""
        self.font = QFont(self.font_family, self.font_size)
        self.header_font = QFont(DEFAULT_FONT_FAMILY, HEADER_FONT_SIZE, QFont.Bold)
        self.chapter_font = QFont(DEFAULT_FONT_FAMILY, CHAPTER_FONT_SIZE, QFont.Bold)
        self.verse_num_font = QFont(self.font_family, self.verse_num_font_size)
        self.verse_mark_font = QFont(self.font_family, self.verse_mark_size)

    def _is_rect_visible(self, r):
        # Increased buffer to ensure items are visible before they enter the viewport
        buffer = 800 
        return not (r.bottom() < self.scroll_y - buffer or r.top() > self.scroll_y + self.view_height + buffer)

    def _update_item_visibility(self):
        """Updates the visible state of all study and search items based on scroll."""
        for item in self.study_overlay_items + self.search_overlay_items + self.outline_overlay_items:
            item.setVisible(self._is_rect_visible(item.sceneBoundingRect()))

    def _get_ref_from_pos(self, pos):
        def _get_ref_from_pos(self, pos):
            """Finds the verse reference corresponding to a document position."""
            import bisect
            if not self.pos_verse_map: return None
            # pos_verse_map is a list of (char_pos, ref). Find the index where char_pos > pos.
            # Then the verse is at the previous index.
            idx = bisect.bisect_right(self.pos_verse_map, (pos, "zzzzzz")) - 1
            return self.pos_verse_map[idx][1] if idx >= 0 else None
    
    def _get_text_rects(self, start, length):
        return get_text_rects(self.main_text_item, start, length)

    def _get_word_offset_in_verse(self, verse_data, word_idx):
        return get_word_offset_in_verse(verse_data, word_idx)

    def _get_word_idx_from_pos(self, verse_data, pos):
        return get_word_idx_from_pos(verse_data, pos)

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
                self.studyDataChanged.emit() # Refresh panel
                self._render_outline_overlays() # Refresh view

    def _get_heading_at_pos(self, scene_pos):
        """Returns (type, text) of heading at scene_pos, or None."""
        # Use mapFromScene to ensure we are in document coordinates
        doc_pos = self.main_text_item.mapFromScene(scene_pos)
        for rect, h_type, h_text in self.heading_rects:
            if rect.contains(doc_pos):
                print(f"Detected heading at {doc_pos}: {h_type}, {h_text}") # Debug print
                return (h_type, h_text)
        return None

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
        
        # Clear old verse number items
        for it in self.verse_number_items.values():
            self.removeItem(it)
        self.verse_number_items.clear()
        self.selected_verse_items.clear()
        self.last_clicked_verse_idx = -1
        
        doc = self.main_text_item.document()
        layout = doc.documentLayout() # Define layout here
        doc.clear()
        doc.setDocumentMargin(self.side_margin)
        
        doc.setTextWidth(width)
        self.main_text_item.setTextWidth(width)

        cursor = QTextCursor(doc)
        cursor.beginEditBlock() # Optimization
        
        last_book, last_chap = None, None
        
        header_fmt = QTextBlockFormat()
        header_fmt.setAlignment(Qt.AlignCenter)
        header_fmt.setTopMargin(40); header_fmt.setBottomMargin(20)
        
        chap_fmt = QTextBlockFormat()
        chap_fmt.setAlignment(Qt.AlignCenter)
        chap_fmt.setTopMargin(20); chap_fmt.setBottomMargin(20)
        
        header_char_fmt = QTextCharFormat()
        header_char_fmt.setFont(self.header_font); header_char_fmt.setForeground(self.text_color)
        
        chap_char_fmt = QTextCharFormat()
        chap_char_fmt.setFont(self.chapter_font); chap_char_fmt.setForeground(self.text_color)
        
        verse_char_fmt = QTextCharFormat()
        verse_char_fmt.setFont(self.font); verse_char_fmt.setForeground(self.text_color)
        
        verse_indents = self.study_manager.data.get("verse_indent", {})

        # Clear previous heading data
        self.last_width = width
        self.heading_rects = []
        self._pending_headings = [] # (block_num, type, text)

        for verse in self.loader.flat_verses:
            if verse['book'] != last_book:
                cursor.insertBlock(header_fmt)
                cursor.setCharFormat(header_char_fmt)
                cursor.insertText(verse['book'])
                
                # Store for post-layout resolution
                self._pending_headings.append((cursor.block().blockNumber(), "book", verse['book']))
                last_book, last_chap = verse['book'], None

            if verse['chapter'] != last_chap:
                cursor.insertBlock(chap_fmt)
                cursor.setCharFormat(chap_char_fmt)
                cursor.insertText(f"{verse['book']} {verse['chapter']}")
                
                # Store for post-layout resolution
                self._pending_headings.append((cursor.block().blockNumber(), "chapter", f"{verse['book']} {verse['chapter']}"))
                last_chap = verse['chapter']
                
            indent_level = verse_indents.get(verse['ref'], 0)
            
            verse_fmt = QTextBlockFormat()
            verse_fmt.setLineHeight(float(self.line_spacing * 100), int(QTextBlockFormat.ProportionalHeight.value))
            verse_fmt.setBottomMargin(self.font_size * 0.5)
            verse_fmt.setLeftMargin(indent_level * self.tab_size)
            verse_fmt.setTextIndent(30) # Space for the verse number
            
            cursor.insertBlock(verse_fmt)
            cursor.setCharFormat(verse_char_fmt)
            self.verse_pos_map[verse['ref']] = cursor.position()
            self.pos_verse_map.append((cursor.position(), verse['ref']))
            
            cursor.insertText(verse['text'])

        cursor.endEditBlock()

        # Finalize layout and resolve heading rects
        self.total_height = layout.documentSize().height() + 200
        self._update_heading_rects()
        
        self.layoutChanged.emit(int(self.total_height))
        self.layoutFinished.emit()
        self.calculate_section_positions()
        self.render_verses()
        self.layout_version += 1 # Increment layout version

    def _update_heading_rects(self):
        """Resolves absolute scene rects for headings after layout is stable."""
        self.heading_rects = []
        doc = self.main_text_item.document()
        layout = doc.documentLayout()
        
        for block_num, h_type, h_text in self._pending_headings:
            block = doc.findBlockByNumber(block_num)
            if block.isValid():
                # Get actual layout height
                block_height = block.layout().boundingRect().height()
                if block_height <= 0:
                    font = self.header_font if h_type == "book" else self.chapter_font
                    block_height = font.pointSize() * 2.0
                
                block_rect = layout.blockBoundingRect(block)
                # Expand to full width to catch clicks anywhere on the line
                full_width_rect = QRectF(0, block_rect.y(), self.last_width, block_height)
                self.heading_rects.append((full_width_rect, h_type, h_text))

    def render_verses(self) -> None:
        """Updates transient UI elements (like HUD) and lazy-renders verse numbers."""
        doc = self.main_text_item.document()
        layout = doc.documentLayout()
        
        pos = layout.hitTest(QPointF(self.side_margin + 10, self.scroll_y + 100), Qt.FuzzyHit)
        if pos != -1:
            ref = self._get_ref_from_pos(pos)
            if ref and ref != self.last_emitted_ref:
                self.last_emitted_ref = ref
                self.currentReferenceChanged.emit(ref)
        
        self._render_visible_verse_numbers()
        
        if self.strongs_enabled:
            self._render_strongs_overlays()
            
        if self.outlines_enabled or self.active_outline_id:
            self._render_outline_overlays()

    def _render_visible_verse_numbers(self):
        """Creates or updates VerseNumberItems only for visible verses."""
        doc = self.main_text_item.document()
        layout = doc.documentLayout()
        
        buffer = 200
        start_pos = layout.hitTest(QPointF(self.side_margin + 10, max(0, self.scroll_y - buffer)), Qt.FuzzyHit)
        end_pos = layout.hitTest(QPointF(self.side_margin + 10, self.scroll_y + self.view_height + buffer), Qt.FuzzyHit)
        
        if start_pos == -1: start_pos = 0
        if end_pos == -1: end_pos = doc.characterCount()
        
        visible_refs = set()
        start_idx = bisect.bisect_left(self.pos_verse_map, (start_pos, ""))
        end_idx = bisect.bisect_right(self.pos_verse_map, (end_pos, "zzzzzz"))
        
        start_idx = max(0, start_idx - 1)
        end_idx = min(len(self.pos_verse_map), end_idx + 1)
        
        verse_indents = self.study_manager.data.get("verse_indent", {})
        verse_marks = self.study_manager.data.get("verse_marks", {})
        
        for i in range(start_idx, end_idx):
            char_pos, ref = self.pos_verse_map[i]
            visible_refs.add(ref)
            
            mark_type = verse_marks.get(ref)
            is_selected = hasattr(self, "selected_refs") and ref in self.selected_refs

            if ref not in self.verse_number_items:
                verse_data = self.loader.get_verse_by_ref(ref)
                if not verse_data: continue
                
                block = doc.findBlock(char_pos)
                rect = layout.blockBoundingRect(block)
                indent_level = verse_indents.get(ref, 0)
                
                v_item = VerseNumberItem(verse_data['verse_num'], ref, self.verse_num_font, self.ref_color, mark_font=self.verse_mark_font)
                v_item.setPos(self.side_margin + (indent_level * self.tab_size), rect.top())
                v_item.setZValue(10)
                v_item.mark_type = mark_type
                v_item.is_selected = is_selected
                
                v_item.clicked.connect(lambda shift, v=v_item: self._on_verse_num_clicked(v, shift))
                v_item.doubleClicked.connect(self._clear_verse_selection)
                v_item.contextMenuRequested.connect(lambda pos, v=v_item: self._on_verse_num_context_menu(v, pos))
                v_item.dragged.connect(lambda dx, v=v_item: self._on_verse_num_dragged(v, dx))
                v_item.released.connect(self._on_verse_num_released)
                
                self.addItem(v_item)
                self.verse_number_items[ref] = v_item
            else:
                # Update existing item state
                it = self.verse_number_items[ref]
                if it.mark_type != mark_type or it.is_selected != is_selected:
                    it.mark_type = mark_type
                    it.is_selected = is_selected
                    it.update()

        to_remove = []
        for ref, it in self.verse_number_items.items():
            if ref not in visible_refs and not it.is_selected:
                to_remove.append(ref)
        
        for ref in to_remove:
            it = self.verse_number_items.pop(ref)
            self.removeItem(it)

    def set_outlines_enabled(self, enabled: bool):
        self.outlines_enabled = enabled
        if not enabled:
            self._clear_outline_overlays()
        else:
            self._render_outline_overlays()

    def set_active_outline(self, outline_id: str):
        """Enables editing mode for a specific outline."""
        self.active_outline_id = outline_id
        self._render_outline_overlays()

    def _is_descendant_of(self, node, root_id):
        """Returns True if node is the root_id or a child/descendant of it."""
        if not node or not root_id: return False
        if node.get("id") == root_id: return True
        # Note: This is expensive if called frequently; we might prefer passing a flag down render_node
        return False # Fallback for now, will improve via render_node flag

    def _clear_outline_overlays(self):
        for it in self.outline_overlay_items:
            if it.scene() == self:
                self.removeItem(it)
        self.outline_overlay_items.clear()
        if self.ghost_line_item:
            if self.ghost_line_item.scene() == self:
                self.removeItem(self.ghost_line_item)
            self.ghost_line_item = None

    def _start_divider_drag(self, pos):
        item = self.sender()
        if not isinstance(item, OutlineDividerItem): return
        
        self.is_dragging_divider = True
        self.drag_divider_item = item
        
        # Calculate valid index range based on siblings
        parent = item.parent_node
        idx = item.split_idx
        loader = self.loader
        
        if idx == -2: # TOP OUTER BOUNDARY
            self.drag_bounds_min = 0.0 # Start of Bible
            if parent.get("children"):
                # Cannot move past the end of the first child (must have at least one verse)
                self.drag_bounds_max = loader.get_verse_index(parent["children"][0]["range"]["end"]) - 1.0
            else:
                # Leaf node: cannot move past its own end (must have at least one verse)
                self.drag_bounds_max = loader.get_verse_index(parent["range"]["end"]) - 1.0
            
            # Divider is BEFORE the start verse, so index is start - 1.0 (or -0.1)
            start_idx = loader.get_verse_index(parent["range"]["start"])
            orig_split_idx = (start_idx - 1.0) if int(start_idx) == start_idx else (start_idx - 0.1)
            self.drag_divider_original_idx = orig_split_idx
            
            preceding, succeeding = self.study_manager.outline_manager.get_nearest_split_indices(orig_split_idx)
            # The top boundary must stay ABOVE all other splits and within Bible start
            self.drag_hard_min = preceding
            self.drag_hard_max = succeeding
            
        elif idx == -3: # BOTTOM OUTER BOUNDARY
            # Cannot move past start of the last child (must have at least one verse)
            if parent.get("children"):
                self.drag_bounds_min = loader.get_verse_index(parent["children"][-1]["range"]["start"])
            else:
                self.drag_bounds_min = loader.get_verse_index(parent["range"]["start"])
                
            self.drag_bounds_max = float(len(loader.flat_verses) - 1) # End of Bible
            
            # Divider is AFTER the end verse, so index is just the end index
            orig_split_idx = loader.get_verse_index(parent["range"]["end"])
            self.drag_divider_original_idx = orig_split_idx
            
            preceding, succeeding = self.study_manager.outline_manager.get_nearest_split_indices(orig_split_idx)
            # The bottom boundary must stay BELOW all other splits and within Bible end
            self.drag_hard_min = preceding
            self.drag_hard_max = succeeding

        elif idx >= 0: # INTERNAL SPLIT
            children = parent.get("children", [])
            if idx < len(children) - 1:
                c1 = children[idx]
                c2 = children[idx+1]
                
                # Sibling boundaries
                sibling_min = self.loader.get_verse_index(c1["range"]["start"])
                sibling_max = self.loader.get_verse_index(c2["range"]["end"]) - 1.0
                
                # Original position
                current_split_idx_val = self.loader.get_verse_index(c1["range"]["end"])
                self.drag_divider_original_idx = current_split_idx_val
                
                # Hard obstacles from OTHER splits
                preceding, succeeding = self.study_manager.outline_manager.get_nearest_split_indices(current_split_idx_val)
                
                # Final constraints are the tightest of sibling bounds and nearest obstacles
                self.drag_bounds_min = sibling_min
                self.drag_bounds_max = sibling_max
                self.drag_hard_min = preceding
                self.drag_hard_max = succeeding
        
        # Create a ghost line to show potential new position
        pen = QPen(QColor("#005a9e"))
        pen.setWidth(2)
        self.drag_divider_ghost = QGraphicsLineItem(self.side_margin, pos.y(), self.sceneRect().width() - 10, pos.y())
        self.drag_divider_ghost.setPen(pen)
        self.drag_divider_ghost.setZValue(100)
        self.addItem(self.drag_divider_ghost)
        
        # Capture current mouse position
        self.views()[0].setCursor(Qt.SizeVerCursor)

    def _render_outline_overlays(self):
        self._clear_outline_overlays()
        # If neither is enabled/active, nothing to render
        if not self.outlines_enabled and not self.active_outline_id: return
        
        outlines = self.study_manager.outline_manager.get_outlines()
        
        # If global toggle is off, only render the active one
        if not self.outlines_enabled and self.active_outline_id:
            outlines = [o for o in outlines if o["id"] == self.active_outline_id]
            
        doc = self.main_text_item.document()
        layout = doc.documentLayout()
        
        def get_verse_y_range(ref):
            # Strip suffixes like 'a', 'b' for position lookup in the verse_pos_map
            base_ref = ref
            if len(ref) > 1 and ref[-1].isalpha() and (ref[-2].isdigit() or ref[-2] == ':'):
                base_ref = ref[:-1]
                
            if base_ref in self.verse_pos_map:
                pos = self.verse_pos_map[base_ref]
                block = doc.findBlock(pos)
                rect = layout.blockBoundingRect(block)
                return rect.top(), rect.bottom()
            return None, None

        def get_line_style(level):
            """Returns (QPen, is_double, text_level) for a given depth level."""
            color = QColor("#AAAAAA")
            if level == 0: # Outer Boundary
                pen = QPen(color, 2)
                return pen, True, None
            elif level == 1: # Section
                pen = QPen(color, 2, Qt.SolidLine)
                return pen, False, None
            elif level == 2: # Sub-Section
                pen = QPen(color, 1.5, Qt.CustomDashLine)
                pen.setDashPattern([4, 4]) # Dash, Gap (Closer than level 3)
                return pen, False, None
            elif level == 3: # Sub-Sub-Section
                pen = QPen(color, 1.5, Qt.CustomDashLine)
                pen.setDashPattern([4, 10, 1, 10]) # Dash, Gap, Dot, Gap
                return pen, False, None
            elif level == 4: # Sub-Sub-Sub-Section
                pen = QPen(color, 1.5, Qt.CustomDashLine)
                pen.setDashPattern([1, 14]) # Dot, Gap
                return pen, False, None
            else: # Lower: spaced numbers
                pen = QPen(color, 1, Qt.SolidLine)
                return pen, False, level

        def render_node(node, level=0, is_active=False):
            start_ref = node["range"]["start"]
            end_ref = node["range"]["end"]
            
            # This node is active if its parent was, or if it is the active root itself
            node_is_active = is_active or (self.active_outline_id and node.get("id") == self.active_outline_id)
            
            s_top, s_bottom = get_verse_y_range(start_ref)
            e_top, e_bottom = get_verse_y_range(end_ref)
            
            if s_top is None or e_bottom is None: return

            # Calculate mid-points for boundaries
            y_start = s_top
            y_end = e_bottom

            # For centering boundaries in gaps
            s_idx = self.loader.get_verse_index(start_ref)
            if s_idx >= 1.0:
                prev_ref = self.loader.flat_verses[int(s_idx) - 1]['ref']
                _, prev_bottom = get_verse_y_range(prev_ref)
                if prev_bottom is not None: y_start = (prev_bottom + s_top) / 2
                else: y_start -= 5
            else: y_start -= 5

            e_idx = self.loader.get_verse_index(end_ref)
            if e_idx < len(self.loader.flat_verses) - 1:
                next_ref = self.loader.flat_verses[int(e_idx) + 1]['ref']
                next_top, _ = get_verse_y_range(next_ref)
                if next_top is not None: y_end = (e_bottom + next_top) / 2
                else: y_end += 5
            else: y_end += 5

            base_x = self.sceneRect().width() - 10
            x_pos = base_x - (level * 10)
            
            # (Vertical Bracket logic removed as requested)
            
            def draw_h_line(y, h_level, summary_node=None, split_parent=None, split_idx=-1):
                pen, is_double, text_level = get_line_style(h_level)
                # Extend line nearly to the margin
                x_end = self.sceneRect().width() - 10
                
                # Use specialized draggable divider item for all levels
                item = OutlineDividerItem(split_parent, split_idx, y, self.side_margin, x_end, pen, is_double, text_level=text_level)
                item.setVisible(self._is_rect_visible(item.boundingRect()))
                if summary_node:
                    tip = f"[{summary_node['title']}]\n{summary_node.get('summary', '')}"
                    item.setToolTip(tip)
                
                # Only enable dragging if we are in active editing mode for this specific outline
                if node_is_active and split_idx != -1:
                    item.dragStarted.connect(self._start_divider_drag)
                else:
                    item.setCursor(Qt.ArrowCursor) # Standard cursor if not draggable
                
                self.addItem(item)
                self.outline_overlay_items.append(item)

            # Draw outer boundaries for level 0
            if level == 0:
                draw_h_line(y_start, 0, node, split_parent=node, split_idx=-2) # Top Boundary
                draw_h_line(y_end, 0, node, split_parent=node, split_idx=-3) # Bottom Boundary
            
            if "children" in node:
                children = node["children"]
                
                # Visual style is strictly dependent on tree structure.
                # If parent is level L, the divider between its children is level L+1.
                child_divider_level = level + 1
                
                for i in range(len(children) - 1):
                    _, child_bottom = get_verse_y_range(children[i]["range"]["end"])
                    next_child_top, _ = get_verse_y_range(children[i+1]["range"]["start"])
                    
                    if child_bottom is not None and next_child_top is not None:
                        mid_y = (child_bottom + next_child_top) / 2
                        # Pass split information to enable dragging
                        draw_h_line(mid_y, child_divider_level, node, split_parent=node, split_idx=i)
            

                for child in children:
                    render_node(child, level + 1, node_is_active)
                    
        for outline in outlines:
            render_node(outline)

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

    def _render_strongs_overlays(self):
        """Renders feint underlines for words with Strongs numbers in visible area."""
        self._clear_strongs_overlays()
        
        # Find visible verses
        doc = self.main_text_item.document()
        layout = doc.documentLayout()
        
        # Hit test with a buffer to ensure we catch verses slightly off screen
        buffer = 100
        start_pos = layout.hitTest(QPointF(self.side_margin + 10, max(0, self.scroll_y - buffer)), Qt.FuzzyHit)
        end_pos = layout.hitTest(QPointF(self.side_margin + 10, self.scroll_y + self.view_height + buffer), Qt.FuzzyHit)
        
        if start_pos == -1: start_pos = 0
        if end_pos == -1: end_pos = doc.characterCount()
        
        # Using binary search for efficiency on the large list
        start_idx = bisect.bisect_left(self.pos_verse_map, (start_pos, ""))
        end_idx = bisect.bisect_right(self.pos_verse_map, (end_pos, "zzzzzz"))
        
        # Adjust indices to be safe
        start_idx = max(0, start_idx - 1)
        end_idx = min(len(self.pos_verse_map), end_idx + 1)
        
        # Slightly more noticeable underline: Gray with 120 opacity and 1.5 width
        pen = QPen(QColor(120, 120, 120, 120), 1.5) 
        
        # Map refs to verse data for faster lookup
        flat_refs = [v['ref'] for v in self.loader.flat_verses]
        
        for i in range(start_idx, end_idx):
            char_pos, ref = self.pos_verse_map[i]
            
            # Find verse data
            verse = self.loader.get_verse_by_ref(ref)
            if not verse: continue
            
            v_start = self.verse_pos_map[ref]
            
            for word_idx, token in enumerate(verse['tokens']):
                if len(token) > 1: # Has Strongs
                    start_pos_in_v = self._get_word_offset_in_verse(verse, word_idx)
                    rects = self._get_text_rects(v_start + start_pos_in_v, len(token[0]))
                    for r in rects:
                        line = QGraphicsLineItem(r.left(), r.bottom() + 1, r.right(), r.bottom() + 1)
                        line.setPen(pen)
                        line.setZValue(-1)
                        line.setAcceptedMouseButtons(Qt.NoButton)
                        self.addItem(line)
                        self.strongs_overlay_items.append(line)

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
                            return token[1], ref # Strongs number(s)
        return None, None

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
        """Main rendering pass for all study data."""
        self.overlay_manager.render_study_overlays()

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
        # 1. Check for Heading right-click
        heading_data = self._get_heading_at_pos(event.scenePos())
        if heading_data:
            print(f"Detected heading right-click: {heading_data}") # Debug print
            menu = QMenu()
            menu.setStyleSheet("QMenu { background-color: #333; color: white; } QMenu::item:selected { background-color: #555; }")
            suggest_act = QAction("Get suggested symbols", menu)
            suggest_act.triggered.connect(lambda: self._show_suggested_symbols_dialog(heading_data))
            menu.addAction(suggest_act)
            menu.exec(event.screenPos())
            event.accept() # Accept the event to prevent further processing
            return
            
        # 2. Prioritize VerseNumberItem
        item = self.itemAt(event.scenePos(), self.views()[0].transform())
        if isinstance(item, VerseNumberItem):
            # The VerseNumberItem handles its own context menu logic via a signal
            # We explicitly emit the signal from the item to trigger its menu
            item.contextMenuRequested.emit(event.screenPos())
            event.accept() # Accept the event to prevent further processing
            return

        # 3. Fallback to text selection/marking logic
        cursor = self.main_text_item.textCursor()
        if not cursor.hasSelection():
            # If no text is selected, try to select the word under the cursor
            pos = self.main_text_item.document().documentLayout().hitTest(self.main_text_item.mapFromScene(event.scenePos()), Qt.FuzzyHit)
            if pos != -1:
                cursor.setPosition(pos); cursor.select(QTextCursor.WordUnderCursor); self.main_text_item.setTextCursor(cursor)
        
        if cursor.hasSelection():
            self.current_selection = (cursor.selectionStart(), cursor.selectionEnd() - cursor.selectionStart())
            view = self.views()[0]
            # Use mapToGlobal from the view's viewport, not the scene
            screen_pos = view.viewport().mapToGlobal(view.mapFromScene(event.scenePos()))
            self.mark_popup.show_at(screen_pos)
            self.render_verses() # Rerender to show selection if any
            event.accept()
            return
        super().contextMenuEvent(event)

    def mouseReleaseEvent(self, event):
        if self.is_dragging_divider:
            self.is_dragging_divider = False
            if self.drag_divider_ghost: # Check if ghost exists before checking visibility
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
                    if abs(new_y - mid_y) < 2: # Very small tolerance as it should be snapped
                        ref_before, ref_after = r1, r2
                        break
                
                if ref_before and ref_after:
                    item = self.drag_divider_item
                    if item.split_idx == -2: # Top boundary
                        # Line is BEFORE ref_after, so ref_after is the new start
                        if self.study_manager.outline_manager.update_outline_boundary(item.parent_node["id"], True, ref_after, self.loader):
                            self._render_outline_overlays()
                            self.studyDataChanged.emit()
                    elif item.split_idx == -3: # Bottom boundary
                        # Line is AFTER ref_before, so ref_before is the new end
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

        # If not dragging, handle text selection/marking
        if event.button() != Qt.LeftButton: 
            super().mouseReleaseEvent(event) # Pass to base if not left button
            return

        cursor = self.main_text_item.textCursor()
        if cursor.hasSelection():
            self.current_selection = (cursor.selectionStart(), cursor.selectionEnd() - cursor.selectionStart())
            view = self.views()[0]
            screen_pos = view.viewport().mapToGlobal(view.mapFromScene(event.scenePos()))
            self.mark_popup.show_at(screen_pos)
        else: 
            self.current_selection = None
        
        self.render_verses() # Always re-render to update UI if selection changed
        
        super().mouseReleaseEvent(event) # Call base class for other handling


    def _clear_verse_selection(self):
        """Clears the selection of verse numbers."""
        for it in self.verse_number_items.values():
            it.is_selected = False
            it.update()
        self.selected_verse_items = []
        if hasattr(self, "selected_refs"): self.selected_refs.clear()
        self.last_clicked_verse_idx = -1

    def _on_verse_num_context_menu(self, item, screen_pos):
        # If item is not in selection, select it first
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
        
        # Sort selected refs by flat index
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

    def _set_selected_verse_mark(self, mark_type):
        for ref in self.selected_refs:
            self.study_manager.set_verse_mark(ref, mark_type)
            
        self.render_verses()
        self.studyDataChanged.emit()

    def wheelEvent(self, event) -> None:
        # 1. Delegate to input_handler first
        if self.input_handler.handle_wheel(event):
            event.accept()
            return
        
        # 2. Check for zoom/spacing modifications (Control/Alt)
        modifiers = event.modifiers(); delta = event.delta() # Reverted to event.delta() for QGraphicsSceneWheelEvent
        if delta == 0: 
            super().wheelEvent(event) # Pass to base if no delta
            return
        
        if modifiers & (Qt.ControlModifier | Qt.AltModifier):
            self._zoom_accumulator += delta
            # Trigger zoom/spacing adjustment for every 120 units (one mouse click)
            while abs(self._zoom_accumulator) >= 120:
                step = 120 if self._zoom_accumulator > 0 else -120
                if modifiers & Qt.ControlModifier: 
                    self.target_font_size = max(8, min(72, self.target_font_size + (2 if step > 0 else -2)))
                elif modifiers & Qt.AltModifier: 
                    self.target_line_spacing = max(1.0, min(3.0, self.target_line_spacing + (0.1 if step > 0 else -0.1)))
                self._zoom_accumulator -= step
            
            self.settingsPreview.emit(self.target_font_size, self.target_line_spacing); self.layout_timer.start(); event.accept(); return
        
        # 3. Normal scrolling
        self._wheel_accumulator += delta
        # Discretize scroll to prevent tiny deltas from overwhelming the smoothing logic
        # 30 units (1/4 of a mouse click) is a good balance between responsiveness and discretization
        while abs(self._wheel_accumulator) >= 30:
            step = 30 if self._wheel_accumulator > 0 else -30
            move = -(step / 120.0) * self.scroll_sens
            self.target_scroll_y = max(0, min(self.total_height - self.view_height, self.target_scroll_y + move))
            self._wheel_accumulator -= step
            
        if not self.scroll_timer.isActive(): self.scroll_timer.start()
        event.accept()
        
        super().wheelEvent(event) # Call base class for any unhandled events

    def mousePressEvent(self, event):
        # 1. Check if we clicked on a verse number item
        item = self.itemAt(event.scenePos(), self.views()[0].transform())
        if not isinstance(item, VerseNumberItem):
            self._clear_verse_selection()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        # Check for outline splits if in editing mode
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
                    
                    # Even if add_split returns None (e.g. already a split point),
                    # we found the intended gap, so stop searching to avoid 
                    # accidental splits of adjacent verses due to tolerance.
                    if self.ghost_line_item:
                        self.removeItem(self.ghost_line_item)
                        self.ghost_line_item = None
                    event.accept()
                    return
        super().mouseDoubleClickEvent(event)

    def _clear_selection(self):
        """Clears the current text selection and resets state."""
        cursor = self.main_text_item.textCursor()
        cursor.clearSelection()
        self.main_text_item.setTextCursor(cursor)
        self.current_selection = None

    def _on_mark_selected(self, mark_type, color):
        if not self.current_selection: return
        start, length = self.current_selection
        
        if mark_type == "logical_mark":
            # Logical marks apply to a single word
            # Find the word key at the start of selection
            view = self.views()[0]
            # Map text cursor position to scene position
            cursor_rect = self.main_text_item.document().documentLayout().blockBoundingRect(self.main_text_item.document().findBlock(start))
            # This is block rect, not exact char pos. Better to use hitTest or get_word_idx logic
            
            # Use existing helper to get key from pos
            # We need scene pos for _get_word_key_at_pos, but we have text position 'start'
            # Let's convert text pos to word key
            ref = self._get_ref_from_pos(start)
            if ref:
                verse_data = self.loader.get_verse_by_ref(ref)
                if verse_data:
                    v_start = self.verse_pos_map[ref]
                    rel_pos = start - v_start
                    word_idx = self._get_word_idx_from_pos(verse_data, rel_pos)
                    if word_idx != -1:
                        key = f"{verse_data['book']}|{verse_data['chapter']}|{verse_data['verse_num']}|{word_idx}"
                        self.study_manager.add_logical_mark(key, color) # color contains the mark type key
            
            self._clear_selection()
            self._render_study_overlays()
            self.studyDataChanged.emit()
            return

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
        verse_data = self.loader.get_verse_by_ref(ref)
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
        
        # Use the unified open_note_by_key to ensure consistency
        self.open_note_by_key(note_key, ref)
        self._clear_selection()

    def _get_word_key_at_pos(self, scene_pos):
        """Returns the word key (str) at the given scene position, or None."""
        pos = self.main_text_item.document().documentLayout().hitTest(self.main_text_item.mapFromScene(scene_pos), Qt.FuzzyHit)
        if pos != -1:
            ref = self._get_ref_from_pos(pos)
            if ref:
                verse_data = self.loader.get_verse_by_ref(ref)
                if verse_data:
                    word_idx = self._get_word_idx_from_pos(verse_data, pos - self.verse_pos_map[ref])
                    if word_idx != -1:
                        # Punctuation check
                        token_text = verse_data['tokens'][word_idx][0]
                        if any(c.isalnum() for c in token_text):
                            return f"{verse_data['book']}|{verse_data['chapter']}|{verse_data['verse_num']}|{word_idx}"
        return None

    def keyPressEvent(self, event):
        if self.input_handler.handle_key_press(event):
            return
        super().keyPressEvent(event)

    def mouseMoveEvent(self, event):
        # 1. Handle divider dragging
        if self.is_dragging_divider:
            scene_pos = event.scenePos()
            # Snap to closest verse gap within allowed range
            doc = self.main_text_item.document()
            layout = doc.documentLayout()
            
            best_gap_y = -1
            best_dist = 1000
            
            for i in range(len(self.pos_verse_map) - 1):
                char_pos1, r1 = self.pos_verse_map[i]
                char_pos2, r2 = self.pos_verse_map[i+1]
                
                idx_before = self.loader.get_verse_index(r1)
                idx_after = self.loader.get_verse_index(r2)
                
                # 1. Must be within immediate sibling bounds
                # If idx_before is X, Child 1 ends at X, Child 2 starts at X+1.
                # To ensure Child 2 has at least one verse, Child 2's end (drag_bounds_max)
                # must be >= Child 2's start (X+1). So X <= drag_bounds_max - 1.0.
                # Since drag_bounds_max was already adjusted by -1.0 in _start_drag for internal splits,
                # we just check idx_before <= drag_bounds_max.
                if idx_before < self.drag_bounds_min or idx_before > self.drag_bounds_max:
                    continue
                    
                # 2. Must not touch or pass other divisions (regardless of level)
                if self.drag_hard_min is not None and idx_before <= self.drag_hard_min:
                    continue
                if self.drag_hard_max is not None and idx_before >= self.drag_hard_max:
                    continue
                
                rect1 = layout.blockBoundingRect(doc.findBlock(char_pos1))
                rect2 = layout.blockBoundingRect(doc.findBlock(char_pos2))
                
                mid_y = (rect1.bottom() + rect2.top()) / 2
                dist = abs(scene_pos.y() - mid_y)
                
                # Use a generous but reasonable snapping distance
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

        # 2. Handle ghost line for outline editing
        if self.active_outline_id:
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
                        # Ensure color is faint
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

    def _handle_strongs_lookup(self):
        # Logic moved to SceneInputHandler
        pass

    def _handle_delete_key(self):
        # Logic moved to SceneInputHandler
        pass

    def _start_arrow_drawing(self):
        # Logic moved to SceneInputHandler
        pass

    def _finish_arrow_drawing(self):
        # Logic moved to SceneInputHandler
        pass

    def _on_strongs_hover_timeout(self):
        # Logic moved to SceneInputHandler
        pass

    def _draw_temp_arrow(self, end_pos):
        # Logic moved to SceneInputHandler
        pass

    def _clear_temp_arrow(self):
        # Logic moved to SceneInputHandler
        pass

    def _apply_symbol_at_mouse(self, number_key):
        view = self.views()[0]
        mouse_pos = view.mapToScene(view.mapFromGlobal(QCursor.pos()))
        
        # Get word key at mouse position
        key = self._get_word_key_at_pos(mouse_pos)
        if not key: return
        
        # Get symbol ID from manager using binding
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
        """Finds the divider near scene_pos and cycles its level based on wheel delta."""
        # 1. First, check if there's an actual divider item at this position
        view = self.views()[0]
        item = self.itemAt(scene_pos, view.transform())
        
        if isinstance(item, OutlineDividerItem):
            # Internal splits have split_idx >= 0. Outer boundaries (-2, -3) are not cycled.
            if item.split_idx >= 0:
                if self.study_manager.outline_manager.cycle_level_by_id(item.parent_node["id"], item.split_idx, delta < 0):
                    self._render_outline_overlays()
                    self.studyDataChanged.emit()
                    return True
        
        # 2. Fallback: Find which gap we are in (if item not directly hit)
        doc = self.main_text_item.document()
        layout = doc.documentLayout()
        tolerance = 20
        
        for i in range(len(self.pos_verse_map) - 1):
            char_pos1, ref1 = self.pos_verse_map[i]
            char_pos2, ref2 = self.pos_verse_map[i+1]
            
            rect1 = layout.blockBoundingRect(doc.findBlock(char_pos1))
            rect2 = layout.blockBoundingRect(doc.findBlock(char_pos2))
            
            if rect1.bottom() - tolerance <= scene_pos.y() <= rect2.top() + tolerance:
                # Found the gap! Tell OutlineManager to cycle level
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
        self.layout_version += 1 # Increment layout version

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

    def _on_verse_num_clicked(self, item, shift):
        # We need a stable index for range selection. 
        flat_refs = [v['ref'] for v in self.loader.flat_verses]
        item_idx = flat_refs.index(item.ref)

        if not shift:
            # Single selection or Grab group
            if not hasattr(self, "selected_refs"): self.selected_refs = set()
            
            if item.ref in self.selected_refs:
                # Item is already selected, don't clear others so we can "grab the group"
                return
            
            # Not in selection, clear and select single
            self._clear_verse_selection()
            self.selected_verse_items = [item]
            item.is_selected = True
            item.update()
            self.last_clicked_verse_idx = item_idx
            
            if not hasattr(self, "selected_refs"): self.selected_refs = set()
            self.selected_refs.add(item.ref)
        else:
            # Range selection
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
                
                # Clear previous selection visual
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
        # If the item being dragged is not in selection, select it
        if item.ref not in self.selected_refs:
            self._on_verse_num_clicked(item, False)
            
        self._was_dragged = True # Track that a drag occurred
        
        # Calculate snap displacement
        tabs_diff = round(dx / self.tab_size)
        
        # Track if we actually changed the tab count to avoid redundant updates
        if not hasattr(self, "_last_drag_tabs_diff") or self._last_drag_tabs_diff != tabs_diff:
            self._last_drag_tabs_diff = tabs_diff
            
            doc = self.main_text_item.document()
            layout = doc.documentLayout()
            verse_indents = self.study_manager.data.get("verse_indent", {})
            
            # Update indentation for all selected verses
            for ref in self.selected_refs:
                # Find the starting indent for this drag
                if not hasattr(self, "_drag_start_indents"):
                    self._drag_start_indents = {}
                
                if ref not in self._drag_start_indents:
                    self._drag_start_indents[ref] = verse_indents.get(ref, 0)
                
                start_indent = self._drag_start_indents[ref]
                new_indent = max(0, start_indent + tabs_diff)
                
                # Apply to data (temporarily)
                self.study_manager.data["verse_indent"][ref] = new_indent
                
                # Apply to document live
                if ref in self.verse_pos_map:
                    pos = self.verse_pos_map[ref]
                    block = doc.findBlock(pos)
                    fmt = block.blockFormat()
                    fmt.setLeftMargin(new_indent * self.tab_size)
                    
                    cursor = QTextCursor(block)
                    cursor.setBlockFormat(fmt)

            # After updating text margins, block positions might have changed
            # We need to refresh all visible verse numbers' positions
            self._update_all_verse_number_positions()
            
            # Live update other overlays (marks, symbols, arrows)
            self._render_study_overlays()
            if self.strongs_enabled:
                self._render_strongs_overlays()

    def _update_all_verse_number_positions(self):
        """Updates the Y (and X) positions of all currently rendered verse numbers."""
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
        # Save the final state to disk
        self.study_manager.save_study()
        
        # Cleanup drag tracking state
        if hasattr(self, "_last_drag_tabs_diff"):
            del self._last_drag_tabs_diff
        if hasattr(self, "_drag_start_indents"):
            del self._drag_start_indents
            
        # If we were dragging, de-select automatically after letting go
        if hasattr(self, "_was_dragged") and self._was_dragged:
            self._clear_verse_selection()
            self._was_dragged = False
            
        # Optional: Final full layout to ensure everything is perfect
        # But live updates should have already done the work.
        self.studyDataChanged.emit()

    def _show_suggested_symbols_dialog(self, heading_data):
        # Calculate top 10 most frequent Strong's words for the given heading
        h_type, h_text = heading_data
        
        # This will be implemented in StrongsManager
        top_words = self.strongs_manager.get_top_strongs_words(h_type, h_text, self.loader.flat_verses)
        
        if top_words:
            dialog = SuggestedSymbolsDialog(top_words, h_text, self.views()[0])
            dialog.exec()
        else:
            print(f"No Strong's words found for {h_type}: {h_text}")
