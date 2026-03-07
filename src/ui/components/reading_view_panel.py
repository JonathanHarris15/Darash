from PySide6.QtWidgets import QWidget, QGridLayout, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt
from src.ui.reader_widget import ReaderWidget
from src.ui.components.search_bar import SearchBar
from src.ui.components.bookmark_ui import BookmarkSidebar

class ReadingViewPanel(QWidget):
    """
    Bundles the ReaderWidget, SearchBar, and BookmarkSidebar into a single reusable panel.
    Can be instantiated multiple times in a splitter.
    """
    def __init__(self, scene, study_manager, parent=None):
        super().__init__(parent)
        self.scene = scene
        
        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        self.reader_widget = ReaderWidget(scene=scene)
        
        # --- Top HUD Layout (Translation Button + Search Bar) ---
        hud_container = QWidget()
        hud_layout = QHBoxLayout(hud_container)
        hud_layout.setContentsMargins(0, 0, 0, 0)
        hud_layout.setSpacing(0)
        
        self.trans_button = QPushButton(self.scene.primary_translation)
        self.trans_button.setCursor(Qt.PointingHandCursor)
        self.trans_button.setStyleSheet("""
            QPushButton {
                background-color: #252525;
                color: #888;
                border: 1px solid #333;
                border-right: none;
                border-radius: 0px;
                padding: 4px 8px;
                font-size: 10px;
                font-weight: bold;
                height: 28px;
            }
            QPushButton:hover {
                background-color: #333;
                color: #64c8ff;
            }
        """)
        self.trans_button.clicked.connect(self._show_translation_menu)
        
        self.search_bar = SearchBar()
        # Ensure search bar styling matches or integrates well
        self.search_bar.setStyleSheet(self.search_bar.styleSheet() + " QLineEdit { border-left: 1px solid #333; border-radius: 0px; }")
        
        hud_layout.addWidget(self.trans_button)
        hud_layout.addWidget(self.search_bar, 1) # Search bar takes remaining space
        
        # 1. HUD (Top)
        self.layout.addWidget(hud_container, 0, 0)
        
        # 2. Reader Widget (Bottom)
        self.layout.addWidget(self.reader_widget, 1, 0)
        self.layout.setRowStretch(1, 1)
        self.layout.setColumnStretch(0, 1)
        
        # 3. Bookmark Sidebar (Overlapping the reader widget in Row 1)
        self.bookmark_sidebar = BookmarkSidebar(study_manager)
        self.layout.addWidget(self.bookmark_sidebar, 1, 0, Qt.AlignLeft)
        self.bookmark_sidebar.raise_()
        
        # Internal Connections
        self.bookmark_sidebar.bookmarkJumpRequested.connect(self.reader_widget.scene.jump_to)
        
        self.search_bar.jumpToRef.connect(self.reader_widget.scene.jump_to)
        self.search_bar.searchText.connect(self.reader_widget.scene.handle_search)
        self.search_bar.nextMatch.connect(self.reader_widget.scene.next_match)
        self.search_bar.prevMatch.connect(self.reader_widget.scene.prev_match)
        self.search_bar.clearSearch.connect(self.reader_widget.scene.clear_search)
        
        # Connect to scene signals if scene is ready
        self._connect_scene()

    def _connect_scene(self):
        scene = self.reader_widget.scene
        # Core Reader connections
        scene.layoutChanged.connect(self.reader_widget.update_scrollbar_range)
        scene.scrollChanged.connect(self.reader_widget.update_scrollbar_value)
        scene.currentReferenceChanged.connect(self.reader_widget.update_ref_label)
        scene.layoutStarted.connect(self.reader_widget.show_generic_loading)
        scene.settingsPreview.connect(self.reader_widget.show_settings_loading)
        scene.layoutFinished.connect(self.reader_widget.hide_loading)
        self.reader_widget.scrollbar.valueChanged.connect(scene.set_scroll_y)
        
        # Bookmark
        scene.bookmarksUpdated.connect(self.bookmark_sidebar.refresh_bookmarks)
        
        # Search
        scene.searchStatusUpdated.connect(self.search_bar.set_results_status)
        scene.searchStatusUpdated.connect(self._update_scrollbar_matches)
        scene.sectionsUpdated.connect(self.reader_widget.scrollbar.set_sections)

    def _update_scrollbar_matches(self, current, total):
        scene = self.reader_widget.scene
        self.reader_widget.scrollbar.set_matches(scene.search_marks_y, len(scene.loader.flat_verses))

    def _show_translation_menu(self):
        from src.ui.components.translation_selector import TranslationSelector
        self.trans_selector = TranslationSelector(self.scene, self)
        self.trans_selector.settingsChanged.connect(self._on_translation_settings_changed)
        
        # Position below the button
        pos = self.trans_button.mapToGlobal(self.trans_button.rect().bottomLeft())
        self.trans_selector.move(pos)
        self.trans_selector.show()

    def _on_translation_settings_changed(self):
        self.reader_widget.show_loading()
        self.trans_button.setText(self.scene.target_primary_translation)
        self.trans_button.adjustSize()
        self.scene.settings_manager.apply_layout_changes()
