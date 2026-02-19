from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTextEdit, QHBoxLayout, 
    QPushButton, QLabel, QTabWidget, QTextBrowser
)
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QDesktopServices

class NoteEditor(QDialog):
    """
    A Markdown editor and previewer for verse notes.
    Supports bible: links to jump the reader to references.
    """
    noteSaved = Signal(str)
    jumpRequested = Signal(str, str, str) # book, chapter, verse
    DELETE_CODE = 10

    def __init__(self, initial_text="", ref="", parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Note - {ref}")
        self.resize(600, 500)
        # Qt.Tool makes it float on top of the parent window and avoids taskbar clutter
        self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setModal(False)
        
        layout = QVBoxLayout(self)
        self.label = QLabel(f"Note for: {ref}")
        self.label.setStyleSheet("font-weight: bold; color: #ddd;")
        layout.addWidget(self.label)

        self.tabs = QTabWidget()
        
        # --- Edit Tab ---
        self.editor = QTextEdit()
        self.editor.setPlainText(initial_text)
        self.editor.setPlaceholderText("Markdown here... Links: [Mark 11:1](bible:Mark+11:1)")
        self.editor.setStyleSheet("""
            background-color: #222; color: #eee; border: 1px solid #444;
            font-family: 'Consolas', 'Courier New', monospace;
        """)
        self.tabs.addTab(self.editor, "Edit")
        
        # --- Preview Tab ---
        self.preview = QTextBrowser()
        self.preview.setOpenLinks(False)
        self.preview.anchorClicked.connect(self._on_link_activated)
        self.preview.setStyleSheet("background-color: #282828; color: #ddd; border: 1px solid #444;")
        self.tabs.addTab(self.preview, "Preview")
        
        layout.addWidget(self.tabs)
        self.tabs.currentChanged.connect(self._update_preview)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Save")
        self.btn_cancel = QPushButton("Cancel")
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setStyleSheet("color: #ff6666;")
        
        self.btn_save.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_delete.clicked.connect(lambda: self.done(self.DELETE_CODE))
        
        btn_layout.addWidget(self.btn_delete); btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel); btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)
        
        self.setStyleSheet("background-color: #333;")
        self._update_preview()
        
        # If opening an existing note with text, show preview first
        if initial_text.strip():
            self.tabs.setCurrentIndex(1)

    def _update_preview(self):
        if self.tabs.currentIndex() == 1:
            self.preview.setMarkdown(self.editor.toPlainText().replace("bible://", "bible:"))

    def _on_link_activated(self, link):
        full_url_str = link.toString() if isinstance(link, QUrl) else str(link)
        if not full_url_str.startswith("bible:"):
            if full_url_str.startswith("http"): QDesktopServices.openUrl(QUrl(full_url_str))
            return

        # Smart Parsing: bible:Mark+6+12 or bible:Mark+6:12
        ref_str = full_url_str.split(":", 1)[-1].strip("/").replace("+", " ").replace("%20", " ")
        
        # Split by spaces or colons
        import re
        parts = re.split(r'[\s:]+', ref_str.strip())
        
        if len(parts) < 2:
            self.jumpRequested.emit(ref_str, "1", "1")
            return

        # Logic: 
        # Last part is likely Verse if there are 3+ parts or a colon was present
        # Second to last is likely Chapter
        # Everything before is Book
        
        verse = "1"
        chapter = "1"
        book = ""

        if ":" in ref_str:
            # Format "Book Chap:Verse" or "Book Chap: Verse"
            main_part, verse = ref_str.rsplit(":", 1)
            main_parts = main_part.strip().split()
            chapter = main_parts[-1]
            book = " ".join(main_parts[:-1])
        else:
            # Format "Book Chap Verse" or "Book Chap"
            # Check if the last two parts are numbers
            if parts[-1].isdigit() and parts[-2].isdigit():
                verse = parts[-1]
                chapter = parts[-2]
                book = " ".join(parts[:-2])
            elif parts[-1].isdigit():
                chapter = parts[-1]
                book = " ".join(parts[:-1])
            else:
                book = ref_str

        # print(f"DEBUG: Parsed '{ref_str}' -> Book: '{book}', Chap: '{chapter}', Verse: '{verse}'")
        self.jumpRequested.emit(book.strip(), chapter.strip(), verse.strip())

    def get_text(self): return self.editor.toPlainText()
