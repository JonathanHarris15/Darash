from PySide6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QLabel, QPushButton
from PySide6.QtCore import Signal, Qt
import re

class SearchBar(QWidget):
    """
    Search bar for scripture references, words, or phrases.
    Includes navigation for cycling through results and clearing search.
    """
    jumpToRef = Signal(str, str, str) # book, chapter, verse
    searchText = Signal(str)
    nextMatch = Signal()
    prevMatch = Signal()
    clearSearch = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 5, 10, 5)
        self.layout.setSpacing(10)
        
        # Input
        self.input = QLineEdit()
        self.input.setPlaceholderText("Search reference (e.g. John 3:16) or word/phrase...")
        self.input.returnPressed.connect(self.on_search)
        
        # Results Display
        self.results_container = QWidget()
        self.res_layout = QHBoxLayout(self.results_container)
        self.res_layout.setContentsMargins(0, 0, 0, 0)
        
        self.results_label = QLabel("0 matches")
        self.results_label.setStyleSheet("color: #aaa;")
        
        # Navigation Buttons
        self.btn_prev = QPushButton("▲")
        self.btn_next = QPushButton("▼")
        self.btn_clear = QPushButton("✕")
        
        for btn in [self.btn_prev, self.btn_next, self.btn_clear]:
            btn.setFixedSize(24, 24)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #444;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #555;
                }
            """)

        self.btn_prev.clicked.connect(self.prevMatch.emit)
        self.btn_next.clicked.connect(self.nextMatch.emit)
        self.btn_clear.clicked.connect(self._on_clear_clicked)
        
        self.res_layout.addWidget(self.results_label)
        self.res_layout.addWidget(self.btn_prev)
        self.res_layout.addWidget(self.btn_next)
        self.res_layout.addWidget(self.btn_clear)
        
        self.layout.addWidget(self.input)
        self.layout.addWidget(self.results_container)
        
        self.results_container.hide() # Hide until results exist
        
        self.setStyleSheet("""
            SearchBar {
                background-color: #252525;
                border-bottom: 1px solid #333;
            }
            QLineEdit {
                background-color: #333;
                color: white;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 4px 8px;
            }
        """)

    def on_search(self):
        text = self.input.text().strip()
        if not text:
            self._on_clear_clicked()
            return
            
        ref_match = re.match(r"^((?:\d\s|I+\s)?[A-Za-z\s]+)\s(\d+)(?::(\d+))?$", text)
        if ref_match:
            book = ref_match.group(1).strip()
            chapter = ref_match.group(2)
            verse = ref_match.group(3) or "1"
            self.jumpToRef.emit(book, chapter, verse)
            self.results_container.hide()
        else:
            self.searchText.emit(text)

    def set_results_status(self, current: int, total: int):
        if total > 0:
            self.results_label.setText(f"{current + 1} of {total}")
            self.results_container.show()
        else:
            self.results_label.setText("0 matches")
            self.results_container.show()

    def _on_clear_clicked(self):
        self.input.clear()
        self.results_container.hide()
        self.clearSearch.emit()
