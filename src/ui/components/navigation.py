from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal
from typing import List

class NavigationDock(QWidget):
    """
    A widget providing a hierarchical tree view of the Bible structure
    (Testament -> Book -> Chapter) for easy navigation.
    Styled to match the Study Panel.
    """
    jumpRequested = Signal(str, str, str) # book, chapter, verse
    strongsToggled = Signal(bool)
    outlinesToggled = Signal(bool)

    def __init__(self, loader, parent=None):
        """
        Initializes the Navigation Panel.
        
        Args:
            loader: A VerseLoader instance to retrieve Bible structure from.
            parent: Parent widget.
        """
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Header with Toggle buttons
        header_layout = QHBoxLayout()
        header_layout.addStretch()
        
        self.btn_strongs = QPushButton("א") # Aleph
        self.btn_strongs.setCheckable(True)
        self.btn_strongs.setToolTip("Toggle Strong's Underlines")
        self.btn_strongs.setFixedSize(28, 28)
        self.btn_strongs.setStyleSheet("""
            QPushButton {
                background-color: #333;
                color: #888;
                border: 1px solid #444;
                border-radius: 4px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #444;
                color: #bbb;
            }
            QPushButton:checked {
                background-color: #2a2a25;
                color: #ffcc00;
                border-color: #665500;
            }
        """)
        self.btn_strongs.toggled.connect(self.strongsToggled.emit)
        header_layout.addWidget(self.btn_strongs)

        self.btn_outlines = QPushButton("☰")
        self.btn_outlines.setCheckable(True)
        self.btn_outlines.setToolTip("Toggle Outlines")
        self.btn_outlines.setFixedSize(28, 28)
        self.btn_outlines.setStyleSheet("""
            QPushButton {
                background-color: #333;
                color: #888;
                border: 1px solid #444;
                border-radius: 4px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #444;
                color: #bbb;
            }
            QPushButton:checked {
                background-color: #2a2a25;
                color: #00ff00;
                border-color: #006600;
            }
        """)
        self.btn_outlines.toggled.connect(self.outlinesToggled.emit)
        header_layout.addWidget(self.btn_outlines)
        
        layout.addLayout(header_layout)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(15)
        self.tree.setStyleSheet("""
            QTreeWidget {
                background-color: #222;
                border: 1px solid #444;
                color: #ccc;
            }
            QTreeWidget::item {
                padding: 4px;
            }
            QTreeWidget::item:hover {
                background-color: #333;
            }
        """)
        layout.addWidget(self.tree)
        
        self.populate_tree(loader)
        self.tree.itemClicked.connect(self.on_item_clicked)

    def populate_tree(self, loader) -> None:
        """
        Populates the tree widget with Testaments, Books, and Chapters.
        
        Args:
            loader: The VerseLoader instance.
        """
        structure = loader.get_structure()
        
        for testament, books in structure.items():
            t_item = QTreeWidgetItem(self.tree)
            t_item.setText(0, testament)
            t_item.setExpanded(True)
            
            for book, chapters in books.items():
                b_item = QTreeWidgetItem(t_item)
                b_item.setText(0, book)
                # Store metadata in UserRole
                b_item.setData(0, Qt.UserRole, "book")
                b_item.setData(0, Qt.UserRole + 1, book)
                
                for chapter in chapters:
                    c_item = QTreeWidgetItem(b_item)
                    c_item.setText(0, f"{book} {chapter}")
                    c_item.setData(0, Qt.UserRole, "chapter")
                    c_item.setData(0, Qt.UserRole + 1, book)
                    c_item.setData(0, Qt.UserRole + 2, str(chapter))

    def on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """
        Handles tree item click events and emits jumpRequested signal.
        
        Args:
            item: The clicked QTreeWidgetItem.
            column: The clicked column index.
        """
        item_type = item.data(0, Qt.UserRole)
        
        if item_type == "book":
            book = item.data(0, Qt.UserRole + 1)
            # Jump to the beginning of the book
            self.jumpRequested.emit(book, "1", "1")
            
        elif item_type == "chapter":
            book = item.data(0, Qt.UserRole + 1)
            chapter = item.data(0, Qt.UserRole + 2)
            self.jumpRequested.emit(book, chapter, "1")
