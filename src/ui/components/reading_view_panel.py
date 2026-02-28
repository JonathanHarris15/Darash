from PySide6.QtWidgets import QWidget, QGridLayout
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
        
        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        self.reader_widget = ReaderWidget()
        # Ensure the reader widget uses the shared scene provided by the main window
        self.reader_widget.scene = scene
        self.reader_widget.view.setScene(scene)
        
        self.search_bar = SearchBar()
        
        # 1. Search Bar (Top)
        self.layout.addWidget(self.search_bar, 0, 0)
        
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
        self.reader_widget.scrollbar.set_matches(scene.search_marks_y, scene.total_height)
