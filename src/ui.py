from PySide6.QtWidgets import (
    QMainWindow, QGraphicsView, QVBoxLayout, QHBoxLayout, QGridLayout,
    QWidget, QScrollBar, QStyle, QStyleOptionSlider, QLabel, QMenuBar, QMenu
)
from PySide6.QtGui import QPainter, QColor, QAction, QFont
from PySide6.QtCore import Qt, QTimer, QRect, Signal, QPoint
from src.reader_scene import ReaderScene
from src.navigation import NavigationDock
from src.search_bar import SearchBar
from src.symbol_dialog import SymbolDialog
from src.bookmark_ui import BookmarkSidebar
from src.study_panel import StudyPanel
from src.appearance_panel import AppearancePanel
from src.constants import (
    HUD_BACKGROUND_COLOR, TEXT_COLOR, OVERLAY_BACKGROUND_COLOR,
    RESIZE_DEBOUNCE_INTERVAL, SEARCH_HIGHLIGHT_COLOR, SELECTION_COLOR
)

class ClickableLabel(QLabel):
    clicked = Signal()
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self.setStyleSheet(self.styleSheet().replace("background-color: rgba(30, 30, 30, 200)", "background-color: rgba(60, 60, 60, 220)"))
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet(self.styleSheet().replace("background-color: rgba(60, 60, 60, 220)", "background-color: rgba(30, 30, 30, 200)"))
        super().leaveEvent(event)

class JumpScrollBar(QScrollBar):
    """
    A custom vertical scrollbar that allows clicking on the track to jump 
    directly to a position and renders search match markers and bible sections.
    """
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.match_y_positions = [] # Normalized 0.0 to 1.0
        self.sections = [] # List of {y_start, y_end, color, name} (normalized)
        self.is_hovered = False
        self.setMouseTracking(True)
        
        # Custom Tooltip that follows mouse smoothly
        self.floating_label = QLabel(None, Qt.ToolTip | Qt.WindowTransparentForInput)
        self.floating_label.setStyleSheet("""
            background-color: #333;
            color: white;
            border: 1px solid #555;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 13px;
        """)
        self.floating_label.hide()

    def set_matches(self, y_positions, total_height):
        if total_height > 0:
            self.match_y_positions = [y / total_height for y in y_positions]
        else:
            self.match_y_positions = []
        self.update()

    def set_sections(self, section_data, total_height):
        """Sets the normalized ranges for bible sections."""
        self.sections = []
        if total_height > 0:
            for s in section_data:
                self.sections.append({
                    "y_start": s["y_start"] / total_height,
                    "y_end": s["y_end"] / total_height,
                    "color": s["color"],
                    "name": s["name"]
                })
        self.update()

    def enterEvent(self, event):
        self.is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.is_hovered = False
        self.floating_label.hide()
        self.update()
        super().leaveEvent(event)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        groove_rect = self.style().subControlRect(QStyle.CC_ScrollBar, opt, QStyle.SC_ScrollBarGroove, self)
        if groove_rect.isEmpty():
            groove_rect = self.rect()
            
        if groove_rect.contains(event.pos()):
            rel_y = (event.pos().y() - groove_rect.y()) / max(1, groove_rect.height())
            for s in self.sections:
                if s["y_start"] <= rel_y <= s["y_end"]:
                    self.floating_label.setText(s["name"])
                    self.floating_label.adjustSize()
                    # Offset to the left of the scrollbar
                    self.floating_label.move(event.globalPos().x() - self.floating_label.width() - 20, 
                                           event.globalPos().y() - self.floating_label.height() // 2)
                    self.floating_label.show()
                    return
        self.floating_label.hide()

    def paintEvent(self, event):
        super().paintEvent(event)
        
        painter = QPainter(self)
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        groove_rect = self.style().subControlRect(QStyle.CC_ScrollBar, opt, QStyle.SC_ScrollBarGroove, self)
        if groove_rect.isEmpty():
            groove_rect = self.rect()
        
        # 1. Paint Sections (Only when hovering)
        if self.is_hovered:
            for s in self.sections:
                y_start = groove_rect.y() + (s["y_start"] * groove_rect.height())
                
                from PySide6.QtGui import QPen
                color = QColor(s["color"])
                color.setAlpha(255) 
                painter.setPen(QPen(color, 2))
                painter.drawLine(groove_rect.left(), int(y_start), groove_rect.right(), int(y_start))

        # 2. Paint Search Matches (Always visible)
        if self.match_y_positions:
            painter.setPen(SEARCH_HIGHLIGHT_COLOR)
            for rel_y in self.match_y_positions:
                y = groove_rect.y() + (rel_y * groove_rect.height())
                painter.drawLine(groove_rect.left(), int(y), groove_rect.right(), int(y))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            opt = QStyleOptionSlider()
            self.initStyleOption(opt)
            control = self.style().hitTestComplexControl(QStyle.CC_ScrollBar, opt, event.pos(), self)
            
            if control in [QStyle.SC_ScrollBarAddPage, QStyle.SC_ScrollBarSubPage, QStyle.SC_ScrollBarGroove]:
                groove_rect = self.style().subControlRect(QStyle.CC_ScrollBar, opt, QStyle.SC_ScrollBarGroove, self)
                slider_rect = self.style().subControlRect(QStyle.CC_ScrollBar, opt, QStyle.SC_ScrollBarSlider, self)
                
                if self.orientation() == Qt.Vertical:
                    click_pos = event.pos().y()
                    groove_start = groove_rect.y()
                    groove_len = groove_rect.height()
                    slider_len = slider_rect.height()
                    target_handle_pos = click_pos - groove_start - (slider_len / 2)
                    available_span = max(1, groove_len - slider_len)
                    val = self.style().sliderValueFromPosition(self.minimum(), self.maximum(), int(target_handle_pos), available_span, opt.upsideDown)
                    self.setValue(val)
        super().mousePressEvent(event)

class ReaderWidget(QWidget):
    """
    The main container widget for the Bible reader.
    Integrates the GraphicsView, custom scrollbar, HUD, and loading overlay.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = ReaderScene()
        
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setFrameShape(QGraphicsView.NoFrame)
        self.view.setFocusPolicy(Qt.StrongFocus)
        self.view.setMouseTracking(True)
        self.view.setStyleSheet("QGraphicsView { outline: none; border: none; background: transparent; }")
        
        # Set selection color on view palette
        palette = self.view.palette()
        palette.setColor(palette.ColorGroup.Active, palette.ColorRole.Highlight, SELECTION_COLOR)
        palette.setColor(palette.ColorGroup.Inactive, palette.ColorRole.Highlight, SELECTION_COLOR)
        self.view.setPalette(palette)
        
        self.scrollbar = JumpScrollBar(Qt.Vertical)
        self.scrollbar.setSingleStep(20)
        
        # HUD Label
        self.ref_label = ClickableLabel(self.view)
        self.ref_label.setCursor(Qt.PointingHandCursor)
        self.ref_label.setToolTip("Click to Bookmark")
        self.ref_label.setStyleSheet(f"background-color: rgba(30, 30, 30, 200); color: {TEXT_COLOR.name()}; padding: 8px 12px; border-radius: 4px; font-size: 14px; font-weight: bold;")
        self.ref_label.hide()
        
        # --- Professional Loading Overlay ---
        self.overlay = QWidget(self.view)
        self.overlay.setStyleSheet(f"background-color: {OVERLAY_BACKGROUND_COLOR};")
        self.overlay.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        overlay_layout = QVBoxLayout(self.overlay)
        overlay_layout.setAlignment(Qt.AlignCenter)
        
        self.loading_title = QLabel("JEHU READER")
        self.loading_title.setStyleSheet("color: white; font-size: 32px; font-weight: bold; letter-spacing: 4px;")
        self.loading_title.setAlignment(Qt.AlignCenter)
        
        self.loading_subtitle = QLabel("Preparing the Holy Scriptures...")
        self.loading_subtitle.setStyleSheet("color: #aaa; font-size: 16px; font-style: italic;")
        self.loading_subtitle.setAlignment(Qt.AlignCenter)
        
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #888; font-size: 13px; margin-top: 20px;")
        self.info_label.setAlignment(Qt.AlignCenter)
        
        overlay_layout.addStretch()
        overlay_layout.addWidget(self.loading_title)
        overlay_layout.addWidget(self.loading_subtitle)
        overlay_layout.addWidget(self.info_label)
        overlay_layout.addStretch()
        
        self.overlay.hide()
        
        self.resize_timer = QTimer(self)
        self.resize_timer.setSingleShot(True)
        self.resize_timer.setInterval(RESIZE_DEBOUNCE_INTERVAL)
        self.resize_timer.timeout.connect(self.apply_delayed_resize)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.view)
        layout.addWidget(self.scrollbar)
        
        # Connections
        self.scene.layoutChanged.connect(self.update_scrollbar_range)
        self.scene.scrollChanged.connect(self.update_scrollbar_value)
        self.scene.currentReferenceChanged.connect(self.update_ref_label)
        self.scene.layoutStarted.connect(self.show_generic_loading)
        self.scene.settingsPreview.connect(self.show_settings_loading)
        self.scene.layoutFinished.connect(self.hide_loading)
        self.scrollbar.valueChanged.connect(self.scene.set_scroll_y)
        self.ref_label.clicked.connect(self._on_ref_label_clicked)
        
        self.total_height = self.scene.total_height
        self.scrollbar.setMaximum(int(self.total_height))

    def _on_ref_label_clicked(self):
        ref = self.ref_label.text()
        if ref:
            # Parse ref "Book Chap:Verse"
            import re
            match = re.match(r"(.*) (\d+):(\d+)", ref)
            if match:
                book, chap, verse = match.groups()
                self.scene.study_manager.add_bookmark(book, chap, verse)
                self.scene.bookmarksUpdated.emit()

    def update_scrollbar_range(self, total_height: int) -> None:
        self.total_height = total_height
        self._recalc_scrollbar()

    def update_scrollbar_value(self, value: int) -> None:
        self.scrollbar.blockSignals(True)
        self.scrollbar.setValue(value)
        self.scrollbar.blockSignals(False)
    
    def update_ref_label(self, text: str) -> None:
        self.ref_label.setText(text)
        self.ref_label.adjustSize()
        self.ref_label.show()
        self.reposition_ref_label()

    def reposition_ref_label(self) -> None:
        if not self.ref_label.isVisible(): return
        margin = 20
        self.ref_label.move(margin, self.view.height() - self.ref_label.height() - margin)

    def show_generic_loading(self):
        self.loading_subtitle.setText("Recalculating Layout...")
        self.info_label.setText("")
        self._display_overlay()

    def show_settings_loading(self, font_size: int, line_spacing: float) -> None:
        self.loading_subtitle.setText("Updating Typography...")
        self.info_label.setText(f"Font: {font_size}px  |  Spacing: {line_spacing:.1f}")
        self._display_overlay()

    def _display_overlay(self):
        self.overlay.resize(self.view.size())
        self.overlay.show()

    def hide_loading(self) -> None:
        self.overlay.hide()

    def _recalc_scrollbar(self) -> None:
        view_height = self.view.viewport().height()
        self.scrollbar.setMaximum(max(0, self.total_height - view_height))
        self.scrollbar.setPageStep(view_height)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        
        # Show loading screen immediately when resize starts
        self.loading_subtitle.setText("Adjusting to Window Size...")
        self.info_label.setText("")
        self._display_overlay()
        
        self.reposition_ref_label()
        
        # Reset the timer - layout recalculation will only happen 200ms after the last resize event
        self.resize_timer.start()

    def apply_delayed_resize(self) -> None:
        # Get actual viewport rect
        rect = self.view.viewport().rect()
        if rect.width() <= 0:
            self.hide_loading()
            return
            
        # This will trigger scene.recalculate_layout if width changed
        if abs(rect.width() - self.scene.last_width) > 2:
            self.scene.setSceneRect(rect)
            # hide_loading will be called by layoutFinished signal
        else:
            self.hide_loading()
            
        self._recalc_scrollbar()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Jehu Reader")
        self.resize(1400, 900)

        # Main Widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QGridLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # 1. Reader components
        self.reader_widget = ReaderWidget()
        self.search_bar = SearchBar()

        # 2. Navigation (Left, Fixed Width, Spans both rows)
        self.nav_dock = NavigationDock(self.reader_widget.scene.loader)
        self.nav_dock.setFixedWidth(200)
        self.main_layout.addWidget(self.nav_dock, 0, 0, 2, 1)

        # 3. Search Bar (Top Right)
        self.main_layout.addWidget(self.search_bar, 0, 1)
        
        # 4. Reader Widget (Bottom Right)
        self.main_layout.addWidget(self.reader_widget, 1, 1)
        self.main_layout.setRowStretch(1, 1)
        self.main_layout.setColumnStretch(1, 1)
        
        # 5. Bookmark Sidebar (Overlapping the reader widget in Row 1)
        self.bookmark_sidebar = BookmarkSidebar(self.reader_widget.scene.study_manager)
        self.main_layout.addWidget(self.bookmark_sidebar, 1, 1, Qt.AlignLeft)
        self.bookmark_sidebar.raise_()
        
        # 6. Study Panel (Far Right, Fixed Width, Spans both rows)
        self.study_panel = StudyPanel(self.reader_widget.scene.study_manager, self.reader_widget.scene.symbol_manager)
        self.study_panel.setFixedWidth(250)
        self.main_layout.addWidget(self.study_panel, 0, 2, 2, 1)
        
        # Appearance Dialog (Standalone window)
        self.appearance_dialog = AppearancePanel(self.reader_widget.scene, self)
        
        # Menu Bar
        self.setup_menu()
        
        # Connections
        self.nav_dock.jumpRequested.connect(self.reader_widget.scene.jump_to)
        self.nav_dock.strongsToggled.connect(self.reader_widget.scene.set_strongs_enabled)
        self.bookmark_sidebar.bookmarkJumpRequested.connect(self.reader_widget.scene.jump_to)
        self.bookmark_sidebar.bookmarksChanged.connect(self.study_panel.refresh)
        self.reader_widget.scene.bookmarksUpdated.connect(self.bookmark_sidebar.refresh_bookmarks)
        self.reader_widget.scene.bookmarksUpdated.connect(self.study_panel.refresh)
        
        self.study_panel.jumpRequested.connect(self.reader_widget.scene.jump_to)
        self.study_panel.noteOpenRequested.connect(self.reader_widget.scene.open_note_by_key)
        self.study_panel.dataChanged.connect(self.reader_widget.scene._render_study_overlays)
        self.study_panel.dataChanged.connect(self.reader_widget.scene.render_verses)
        self.study_panel.dataChanged.connect(self.bookmark_sidebar.refresh_bookmarks)
        self.reader_widget.scene.studyDataChanged.connect(self.study_panel.refresh)
        
        self.search_bar.jumpToRef.connect(self.reader_widget.scene.jump_to)
        self.search_bar.searchText.connect(self.reader_widget.scene.handle_search)
        self.search_bar.nextMatch.connect(self.reader_widget.scene.next_match)
        self.search_bar.prevMatch.connect(self.reader_widget.scene.prev_match)
        self.search_bar.clearSearch.connect(self.reader_widget.scene.clear_search)
        
        self.reader_widget.scene.searchStatusUpdated.connect(self.search_bar.set_results_status)
        self.reader_widget.scene.searchStatusUpdated.connect(self._update_scrollbar_matches_v2)
        self.reader_widget.scene.sectionsUpdated.connect(self.reader_widget.scrollbar.set_sections)

    def _update_scrollbar_matches_v2(self, current, total):
        scene = self.reader_widget.scene
        self.reader_widget.scrollbar.set_matches(scene.search_marks_y, scene.total_height)

    def setup_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        edit_menu = menubar.addMenu("&Edit")
        symbols_menu = menubar.addMenu("&Symbols")
        
        appearance_act = QAction("Appearance Settings", self)
        appearance_act.triggered.connect(self._show_appearance_settings)
        edit_menu.addAction(appearance_act)

        file_menu.addSeparator()
        new_study_act = QAction("New Study", self)
        new_study_act.triggered.connect(self._on_new_study)
        file_menu.addAction(new_study_act)
        
        open_study_act = QAction("Open Study", self)
        open_study_act.triggered.connect(self._on_open_study)
        file_menu.addAction(open_study_act)
        
        file_menu.addSeparator()
        exit_act = QAction("Exit", self)
        exit_act.triggered.connect(self.close)
        file_menu.addAction(exit_act)

        manage_symbols_act = QAction("Manage Symbols...", self)
        manage_symbols_act.triggered.connect(self._open_symbols_dialog)
        symbols_menu.addAction(manage_symbols_act)

    def _on_new_study(self):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "New Study", "Enter study name:")
        if ok and name:
            self.reader_widget.scene.study_manager.load_study(name)
            self.reader_widget.scene.load_settings()
            self.reader_widget.scene.recalculate_layout(self.reader_widget.scene.last_width)
            self.reader_widget.scene._render_study_overlays()
            self.bookmark_sidebar.refresh_bookmarks()
            self.study_panel.refresh()
            self.setWindowTitle(f"Jehu Reader - {name}")

    def _on_open_study(self):
        from PySide6.QtWidgets import QFileDialog
        import os
        base_dir = self.reader_widget.scene.study_manager.base_dir
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
            
        study_dir = QFileDialog.getExistingDirectory(self, "Open Study", base_dir)
        if study_dir:
            name = os.path.basename(study_dir)
            self.reader_widget.scene.study_manager.load_study(name)
            self.reader_widget.scene.load_settings()
            self.reader_widget.scene.recalculate_layout(self.reader_widget.scene.last_width)
            self.reader_widget.scene._render_study_overlays()
            self.bookmark_sidebar.refresh_bookmarks()
            self.study_panel.refresh()
            self.setWindowTitle(f"Jehu Reader - {name}")

    def _open_symbols_dialog(self):
        dialog = SymbolDialog(self.reader_widget.scene.symbol_manager, self)
        dialog.symbolsChanged.connect(self.reader_widget.scene._render_study_overlays)
        dialog.exec()

    def _show_appearance_settings(self):
        self.appearance_dialog.show()
        self.appearance_dialog.raise_()
        self.appearance_dialog.activateWindow()

    def _update_scrollbar_matches(self, count):
        scene = self.reader_widget.scene
        self.reader_widget.scrollbar.set_matches(scene.search_marks_y, scene.total_height)
