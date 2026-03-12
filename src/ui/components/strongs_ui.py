from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QDialog, QScrollArea, QPushButton,
    QHBoxLayout, QFrame, QTextEdit, QListWidget, QListWidgetItem,
    QStyledItemDelegate, QStyle
)
from PySide6.QtCore import Qt, QPoint, Signal, QRect, QSize
from PySide6.QtGui import (
    QFont, QColor, QPalette, QTextDocument, QAbstractTextDocumentLayout,
    QPainter
)
from src.core.theme import Theme

class HTMLItemDelegate(QStyledItemDelegate):
    """Custom delegate to render HTML in QListWidget items with word wrap."""
    def paint(self, painter, option, index):
        options = option
        self.initStyleOption(options, index)

        painter.save()

        doc = QTextDocument()
        doc.setTextWidth(options.rect.width())
        # Set text color based on selection state
        color = "white" if options.state & QStyle.State_Selected else "#aaa"
        # Combine ref and snippet if it was stored that way, or just use the text
        html = f"<div style='color:{color}; font-size: 13px;'>{options.text}</div>"
        doc.setHtml(html)

        # Remove selection background highlight (delegate will handle it)
        options.text = ""
        self.parent().style().drawControl(QStyle.CE_ItemViewItem, options, painter)

        painter.translate(options.rect.left(), options.rect.top())
        clip = QRect(0, 0, options.rect.width(), options.rect.height())
        doc.drawContents(painter, clip)

        painter.restore()

    def sizeHint(self, option, index):
        # Calculate dynamic height based on text wrapping
        doc = QTextDocument()
        doc.setTextWidth(option.rect.width())
        doc.setHtml(index.data(Qt.DisplayRole))
        return QSize(option.rect.width(), int(doc.size().height()) + 10)

class StrongsTooltip(QFrame):
    """Small hover popup for Strong's entries."""
    def __init__(self, parent=None):
        super().__init__(parent, Qt.ToolTip | Qt.WindowTransparentForInput | Qt.NoDropShadowWindowHint)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFixedWidth(350) # Slightly wider for better text flow
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        
        self.setStyleSheet(f"""
            StrongsTooltip {{
                background-color: {Theme.BG_SECONDARY};
                border: 1px solid {Theme.BORDER_DEFAULT};
                border-radius: 8px;
            }}
            QLabel {{
                color: {Theme.TEXT_PRIMARY};
                background: transparent;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)
        
        self.header_label = QLabel()
        self.header_label.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {Theme.TEXT_MUTED};")
        layout.addWidget(self.header_label)
        
        self.word_label = QLabel()
        self.word_label.setStyleSheet(f"font-size: 28px; color: {Theme.ACCENT_PRIMARY};")
        self.word_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.word_label)
        
        self.translit_label = QLabel()
        self.translit_label.setStyleSheet(f"font-style: italic; color: {Theme.TEXT_SECONDARY}; font-size: 15px;")
        self.translit_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.translit_label)
        
        self.def_label = QLabel()
        self.def_label.setWordWrap(True)
        self.def_label.setStyleSheet(f"font-size: 14px; line-height: 1.4; color: {Theme.TEXT_PRIMARY};")
        self.def_label.setTextFormat(Qt.RichText)
        layout.addWidget(self.def_label)

    def show_entry(self, sn, entry, pos):
        self.header_label.setText(f"Strong's {sn}")
        self.word_label.setText(entry['word'])
        self.translit_label.setText(f"{{{entry['translit']}}}")
        
        desc = entry['description']
        if entry['kjv_def']:
            kjv = entry['kjv_def']
            if len(kjv) > 120:
                kjv = kjv[:117] + "..."
            desc += f"<br><br><span style='color:#888;'>KJV: {kjv}</span>"
        
        self.def_label.setText(desc)
        
        # Reset geometry to minimum first to force a clean growth
        self.resize(self.width(), 50)
        
        # Move first
        self.move(pos + QPoint(15, 15))
        
        # Show and then adjust
        self.show()
        self.adjustSize()
        
        # Safety check: if adjustSize failed to give us enough height
        if self.height() < 100:
            self.adjustSize()

class StrongsVerboseDialog(QDialog):
    """Detailed window for Strong's entries and usage list."""
    jumpRequested = Signal(str, str, str) # book, chap, verse

    def __init__(self, sn, entry, usages, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Strongs {sn} - {entry['word']}")
        self.resize(500, 700)
        self.setStyleSheet(f"""
            QDialog {{ background-color: {Theme.BG_PRIMARY}; color: {Theme.TEXT_PRIMARY}; }}
            QLabel {{ color: {Theme.TEXT_SECONDARY}; }}
            QTextEdit {{ background-color: {Theme.BG_SECONDARY}; border: 1px solid {Theme.BORDER_DEFAULT}; color: {Theme.TEXT_PRIMARY}; padding: 10px; }}
            QListWidget {{ 
                background-color: {Theme.BG_SECONDARY}; 
                border: 1px solid {Theme.BORDER_DEFAULT}; 
                color: {Theme.TEXT_SECONDARY}; 
                outline: none;
            }}
            QListWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {Theme.BG_TERTIARY};
            }}
            QListWidget::item:hover {{
                background-color: {Theme.BG_TERTIARY};
                color: white;
            }}
            QPushButton {{ 
                background-color: {Theme.BG_TERTIARY}; 
                border: 1px solid {Theme.BORDER_LIGHT}; 
                color: white; 
                padding: 8px; 
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {Theme.BORDER_LIGHT}; }}
        """)
        
        layout = QVBoxLayout(self)
        
        # Dictionary Section
        layout.addWidget(QLabel(f"<b>{sn}</b> - {entry['lang'].upper()}"))
        
        word_box = QFrame()
        word_box.setStyleSheet(f"background-color: {Theme.BG_SECONDARY}; border-radius: 8px; margin: 10px 0;")
        word_layout = QVBoxLayout(word_box)
        
        word_label = QLabel(entry['word'])
        word_label.setStyleSheet(f"font-size: 48px; color: {Theme.ACCENT_PRIMARY};")
        word_label.setAlignment(Qt.AlignCenter)
        word_layout.addWidget(word_label)
        
        trans_label = QLabel(f"{{{entry['translit']}}}")
        trans_label.setStyleSheet(f"font-size: 18px; color: {Theme.TEXT_MUTED};")
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
        self.usage_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.usage_list.setItemDelegate(HTMLItemDelegate(self.usage_list))
        for usage_data in usages:
            ref = usage_data['ref']
            snippet = usage_data['snippet']
            item = QListWidgetItem(self.usage_list)
            # Combine ref and snippet into a single string for display
            # We'll use a data role to store the clean reference for jumping
            item.setText(f"{ref} - {snippet}")
            item.setData(Qt.UserRole, ref)
            self.usage_list.addItem(item)
            
        self.usage_list.itemDoubleClicked.connect(self._on_item_clicked)
        layout.addWidget(self.usage_list)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _on_item_clicked(self, item):
        ref = item.data(Qt.UserRole)
        # Parse ref "Book Chap:Verse"
        parts = ref.rsplit(' ', 1)
        book = parts[0]
        chap_verse = parts[1].split(':')
        self.jumpRequested.emit(book, chap_verse[0], chap_verse[1])
