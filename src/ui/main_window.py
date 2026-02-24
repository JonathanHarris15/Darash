import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QGridLayout, QInputDialog, QFileDialog
)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt
from src.ui.reader_widget import ReaderWidget
from src.ui.components.navigation import NavigationDock
from src.ui.components.search_bar import SearchBar
from src.ui.components.symbol_dialog import SymbolDialog
from src.ui.components.bookmark_ui import BookmarkSidebar
from src.ui.components.study_panel import StudyPanel
from src.ui.components.appearance_panel import AppearancePanel

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
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

        study_name = self.reader_widget.scene.study_manager.current_study_name
        self.setWindowTitle(f"Jehu Reader - {study_name}")

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
        self.nav_dock.outlinesToggled.connect(self.reader_widget.scene.set_outlines_enabled)
        self.bookmark_sidebar.bookmarkJumpRequested.connect(self.reader_widget.scene.jump_to)
        self.bookmark_sidebar.bookmarksChanged.connect(self.study_panel.refresh)
        self.reader_widget.scene.bookmarksUpdated.connect(self.bookmark_sidebar.refresh_bookmarks)
        self.reader_widget.scene.bookmarksUpdated.connect(self.study_panel.refresh)
        
        self.study_panel.jumpRequested.connect(self.reader_widget.scene.jump_to)
        self.study_panel.noteOpenRequested.connect(self.reader_widget.scene.open_note_by_key)
        self.study_panel.activeOutlineChanged.connect(self.reader_widget.scene.set_active_outline)
        self.study_panel.dataChanged.connect(self.reader_widget.scene._render_study_overlays)
        self.study_panel.dataChanged.connect(self.reader_widget.scene._render_outline_overlays)
        self.study_panel.dataChanged.connect(self.reader_widget.scene.render_verses)
        self.study_panel.dataChanged.connect(self.bookmark_sidebar.refresh_bookmarks)
        self.reader_widget.scene.studyDataChanged.connect(self.study_panel.refresh)
        self.reader_widget.scene.outlineCreated.connect(self.study_panel.set_active_outline)
        
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
