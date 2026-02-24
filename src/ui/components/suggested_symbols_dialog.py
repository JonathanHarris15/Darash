from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QListWidget, QListWidgetItem
from PySide6.QtCore import Qt

class SuggestedSymbolsDialog(QDialog):
    def __init__(self, top_words, heading_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Suggested Symbols for {heading_text}")
        self.setMinimumWidth(300)
        
        layout = QVBoxLayout(self)
        
        label = QLabel(f"Top 10 most frequent Strong's words in {heading_text}:")
        layout.addWidget(label)
        
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: #222;
                border: 1px solid #444;
                color: #ccc;
            }
            QListWidget::item {
                padding: 4px;
            }
            QListWidget::item:hover {
                background-color: #333;
            }
            QListWidget::item:selected {
                background-color: #444;
                color: white;
            }
        """)
        
        for word, count in top_words:
            item = QListWidgetItem(f"{word} ({count})")
            item.setData(Qt.UserRole, word) # Store the word itself in UserRole
            self.list_widget.addItem(item)
            
        layout.addWidget(self.list_widget)
