from PySide6.QtWidgets import QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QLabel
from PySide6.QtCore import Qt, Signal
from typing import List

class NavigationDock(QWidget):
    """
    A widget providing a hierarchical tree view of the Bible structure
    (Testament -> Book -> Chapter) for easy navigation.
    Styled to match the Study Panel.
    """
    jumpRequested = Signal(str, str, str) # book, chapter, verse

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
        
        title = QLabel("BIBLE NAVIGATION")
        title.setStyleSheet("font-weight: bold; color: #aaa; margin-bottom: 5px;")
        layout.addWidget(title)
        
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
