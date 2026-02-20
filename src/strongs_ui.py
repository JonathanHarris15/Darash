from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QDialog, QScrollArea, QPushButton,
    QHBoxLayout, QFrame, QTextEdit, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QFont, QColor, QPalette
from src.constants import APP_BACKGROUND_COLOR, TEXT_COLOR, REFERENCE_COLOR

class StrongsTooltip(QFrame):
    """Small hover popup for Strong's entries."""
    def __init__(self, parent=None):
        # Use Qt.ToolTip which is better for these types of windows
        super().__init__(parent, Qt.ToolTip | Qt.WindowTransparentForInput | Qt.NoDropShadowWindowHint)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFixedWidth(320)
        self.setStyleSheet(f"""
            StrongsTooltip {{
                background-color: #2a2a25;
                border: 1px solid #666;
                border-radius: 8px;
            }}
            QLabel {{
                color: #e0e0e0;
                background: transparent;
                padding: 2px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4)
        
        self.header_label = QLabel()
        self.header_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #888;")
        layout.addWidget(self.header_label)
        
        self.word_label = QLabel()
        self.word_label.setStyleSheet("font-size: 26px; color: #ffcc00; margin-top: 2px;")
        self.word_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.word_label)
        
        self.translit_label = QLabel()
        self.translit_label.setStyleSheet("font-style: italic; color: #aaa; font-size: 14px;")
        self.translit_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.translit_label)
        
        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #444;")
        layout.addWidget(line)
        
        self.def_label = QLabel()
        self.def_label.setWordWrap(True)
        self.def_label.setStyleSheet("font-size: 14px; line-height: 1.3; color: #ddd;")
        layout.addWidget(self.def_label)

    def show_entry(self, sn, entry, pos):
        self.header_label.setText(f"Strong's {sn}")
        self.word_label.setText(entry['word'])
        self.translit_label.setText(f"{{{entry['translit']}}}")
        
        full_def = entry['description']
        if entry['kjv_def']:
            # Truncate KJV def for tooltip if too long
            kjv = entry['kjv_def']
            if len(kjv) > 100:
                kjv = kjv[:97] + "..."
            full_def += f"\n\nKJV: {kjv}"
        
        self.def_label.setText(full_def)
        
        # Ensure the window size is updated for the new content before showing
        self.adjustSize()
        
        # Prevent tooltip from going off-screen (basic check)
        self.move(pos + QPoint(15, 15))
        if not self.isVisible():
            self.show()

class StrongsVerboseDialog(QDialog):
    """Detailed window for Strong's entries and usage list."""
    jumpRequested = Signal(str, str, str) # book, chap, verse

    def __init__(self, sn, entry, usages, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Strongs {sn} - {entry['word']}")
        self.resize(500, 700)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: #ddd; }
            QLabel { color: #ccc; }
            QTextEdit { background-color: #252525; border: 1px solid #444; color: #bbb; padding: 10px; }
            QListWidget { 
                background-color: #252525; 
                border: 1px solid #444; 
                color: #aaa; 
                outline: none;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #333;
            }
            QListWidget::item:hover {
                background-color: #333;
                color: white;
            }
            QPushButton { 
                background-color: #444; 
                border: 1px solid #555; 
                color: white; 
                padding: 8px; 
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #555; }
        """)
        
        layout = QVBoxLayout(self)
        
        # Dictionary Section
        layout.addWidget(QLabel(f"<b>{sn}</b> - {entry['lang'].upper()}"))
        
        word_box = QFrame()
        word_box.setStyleSheet("background-color: #252525; border-radius: 8px; margin: 10px 0;")
        word_layout = QVBoxLayout(word_box)
        
        word_label = QLabel(entry['word'])
        word_label.setStyleSheet("font-size: 48px; color: #ffcc00;")
        word_label.setAlignment(Qt.AlignCenter)
        word_layout.addWidget(word_label)
        
        trans_label = QLabel(f"{{{entry['translit']}}}")
        trans_label.setStyleSheet("font-size: 18px; color: #888;")
        trans_label.setAlignment(Qt.AlignCenter)
        word_layout.addWidget(trans_label)
        
        layout.addWidget(word_box)
        
        def_view = QTextEdit()
        def_view.setReadOnly(True)
        def_view.setFixedHeight(150)
        full_text = f"<b>Definition:</b><br>{entry['description']}"
        if entry['kjv_def']:
            full_text += f"<br><br><b>KJV Usage:</b><br>{entry['kjv_def']}"
        def_view.setHtml(full_text)
        layout.addWidget(def_view)
        
        # Usages Section
        layout.addWidget(QLabel(f"<b>Usages in ESV ({len(usages)})</b>"))
        layout.addWidget(QLabel("<small><i>Double-click a reference to jump to it</i></small>"))
        
        self.usage_list = QListWidget()
        for ref in usages:
            self.usage_list.addItem(ref)
        self.usage_list.itemDoubleClicked.connect(self._on_item_clicked)
        layout.addWidget(self.usage_list)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _on_item_clicked(self, item):
        ref = item.text()
        # Parse ref "Book Chap:Verse"
        parts = ref.rsplit(' ', 1)
        book = parts[0]
        chap_verse = parts[1].split(':')
        self.jumpRequested.emit(book, chap_verse[0], chap_verse[1])
