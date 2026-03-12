from PySide6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QLabel, QPushButton
from PySide6.QtCore import Signal, Qt
import re
import difflib
from src.core.constants import OT_BOOKS, NT_BOOKS
from src.ui.theme import Theme

ALL_BOOKS = OT_BOOKS + NT_BOOKS

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
        self.results_label.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        
        # Navigation Buttons
        self.btn_prev = QPushButton("▲")
        self.btn_next = QPushButton("▼")
        self.btn_clear = QPushButton("✕")
        
        for btn in [self.btn_prev, self.btn_next, self.btn_clear]:
            btn.setFixedSize(24, 24)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Theme.BG_TERTIARY};
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {Theme.BORDER_LIGHT};
                }}
            """)

        self.btn_prev.clicked.connect(self.prevMatch.emit)
        self.btn_next.clicked.connect(self.nextMatch.emit)
        self.btn_clear.clicked.connect(self._on_clear_clicked)
        
        self.res_layout.addWidget(self.results_label)
        self.res_layout.addWidget(self.btn_prev)
        self.res_layout.addWidget(self.btn_next)
        self.res_layout.addWidget(self.btn_clear)
        
        self.layout.addWidget(self.input)
        self.layout.setStretch(0, 1) # Give input all available space
        self.layout.addWidget(self.results_container)
        
        self.results_container.hide() # Hide until results exist
        
        self.setStyleSheet(f"""
            SearchBar {{
                background-color: {Theme.BG_SECONDARY};
                border-bottom: 1px solid {Theme.BORDER_DEFAULT};
            }}
            QLineEdit {{
                background-color: {Theme.BG_TERTIARY};
                color: {Theme.TEXT_PRIMARY};
                border: 1px solid {Theme.BORDER_LIGHT};
                border-radius: 4px;
                padding: 4px 8px;
            }}
        """)

    def _resolve_book(self, book_input: str) -> str:
        """
        Attempts to resolve a book name from potentially typo-ridden or abbreviated input.
        """
        book_input = book_input.strip()
        if not book_input:
            return None
            
        # 1. Normalize numeric prefixes (1 -> I, 2 -> II, 3 -> III)
        prefix_map = {"1": "I", "2": "II", "3": "III"}
        match = re.match(r"^([123])\s*(.*)$", book_input)
        if match:
            num = match.group(1)
            rest = match.group(2)
            book_input = f"{prefix_map[num]} {rest}".strip()
            
        # 2. Case-insensitive exact match
        for b in ALL_BOOKS:
            if b.lower() == book_input.lower():
                return b
                
        # 3. Prefix match (e.g. "Gen" -> "Genesis")
        prefix_matches = [b for b in ALL_BOOKS if b.lower().startswith(book_input.lower())]
        if len(prefix_matches) == 1:
            return prefix_matches[0]
            
        # 4. Fuzzy match (e.g. "Genisis" -> "Genesis")
        matches = difflib.get_close_matches(book_input, ALL_BOOKS, n=1, cutoff=0.5)
        if matches:
            return matches[0]
            
        return None

    def on_search(self):
        text = self.input.text().strip()
        if not text:
            self._on_clear_clicked()
            return
            
        # More lenient regex for book, chapter, verse
        # Supports "John 3:16", "John 3 16", "John3:16", "John 3", etc.
        ref_match = re.match(r"^\s*((?:\d+|I+)?\s*[A-Za-z\s]+?)\s*(\d+)(?:[\s:]+(\d+))?\s*$", text, re.IGNORECASE)
        if ref_match:
            book_raw = ref_match.group(1).strip()
            chapter = ref_match.group(2)
            verse = ref_match.group(3) or "1"
            
            resolved_book = self._resolve_book(book_raw)
            if resolved_book:
                self.jumpToRef.emit(resolved_book, chapter, verse)
                self.results_container.hide()
                return
                
        # If not a reference or book not found, treat as text search
        self.searchText.emit(text)

    def set_results_status(self, current: int, total: int):
        if total > 0:
            self.results_label.setText(f"{current + 1} of {total}")
            self.results_container.show()
        else:
            self.results_label.setText("0 matches")
            self.results_container.hide()

    def _on_clear_clicked(self):
        self.input.clear()
        self.results_container.hide()
        self.clearSearch.emit()
