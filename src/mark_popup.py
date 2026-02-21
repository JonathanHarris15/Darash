from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QFrame
from PySide6.QtCore import Qt, Signal, QPoint, QEvent
from src.constants import HIGHLIGHT_COLORS

class ColorButton(QPushButton):
    def __init__(self, color_name, hex_code, parent=None):
        super().__init__(parent)
        self.color_name = color_name
        self.setFixedSize(24, 24)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"background-color: {hex_code}; border-radius: 12px; border: 1px solid #555;")

class MarkPopup(QWidget):
    """
    Popup menu for selecting mark types. 
    Integrated color panel that aligns with the hovered option.
    Uses a single window to ensure clicks are registered correctly.
    """
    markSelected = Signal(str, str) # type of mark, color (hex)
    addNoteRequested = Signal()
    addBookmarkRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.active_mark_type = "highlight"
        self.mark_buttons = {}
        
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # 1. Selection Container (Left)
        self.selection_container = QFrame()
        self.selection_container.setStyleSheet("""
            background-color: #333;
            border: 1px solid #555;
            border-radius: 6px;
        """)
        self.selection_layout = QVBoxLayout(self.selection_container)
        self.selection_layout.setContentsMargins(5, 5, 5, 5)
        self.selection_layout.setSpacing(2)
        
        # 2. Color Wrapper (Right)
        # This wrapper contains a spacer and the color container to allow vertical positioning
        self.color_wrapper = QWidget()
        self.color_wrapper_layout = QVBoxLayout(self.color_wrapper)
        self.color_wrapper_layout.setContentsMargins(5, 0, 5, 0)
        self.color_wrapper_layout.setSpacing(0)
        
        self.top_spacer = QWidget()
        self.color_wrapper_layout.addWidget(self.top_spacer)
        
        self.color_container = QFrame()
        self.color_container.setStyleSheet("""
            background-color: #333;
            border: 1px solid #555;
            border-radius: 6px;
        """)
        self.color_layout = QHBoxLayout(self.color_container)
        self.color_layout.setContentsMargins(8, 8, 8, 8)
        self.color_layout.setSpacing(8)
        self.color_container.hide()
        
        for name, hex_code in HIGHLIGHT_COLORS.items():
            btn = ColorButton(name, hex_code)
            # Use a slightly different approach for the lambda to ensure it captures correctly
            btn.clicked.connect(lambda checked=False, c=hex_code: self._on_color_clicked(c))
            self.color_layout.addWidget(btn)
            
        self.color_wrapper_layout.addWidget(self.color_container)
        self.color_wrapper_layout.addStretch()

        # Create Buttons
        self.btn_hl = self._create_btn("Highlight", "highlight")
        self.btn_ul = self._create_btn("Underline", "underline")
        self.btn_box = self._create_btn("Box", "box")
        self.btn_cir = self._create_btn("Circle", "circle")
        
        self.mark_buttons = {
            self.btn_hl: "highlight",
            self.btn_ul: "underline",
            self.btn_box: "box",
            self.btn_cir: "circle"
        }
        
        self.btn_bookmark = self._create_action_btn("Add Bookmark")
        self.btn_bookmark.clicked.connect(self.addBookmarkRequested.emit)
        self.btn_bookmark.clicked.connect(self.hide)
        
        self.btn_note = self._create_action_btn("Add Note")
        self.btn_note.clicked.connect(self.addNoteRequested.emit)
        self.btn_note.clicked.connect(self.hide)

        self.btn_clear = self._create_action_btn("Clear Marks")
        self.btn_clear.clicked.connect(lambda: self._on_select("clear", ""))
        
        self.btn_clear_symbols = self._create_action_btn("Clear Symbols")
        self.btn_clear_symbols.clicked.connect(lambda: self._on_select("clear_symbols", ""))
        
        self.btn_clear_all = self._create_action_btn("Clear All")
        self.btn_clear_all.clicked.connect(lambda: self._on_select("clear_all", ""))
        
        # Layout Assembly
        self.selection_layout.addWidget(self.btn_hl)
        self.selection_layout.addWidget(self.btn_ul)
        self.selection_layout.addWidget(self.btn_box)
        self.selection_layout.addWidget(self.btn_cir)
        self.selection_layout.addWidget(self._create_sep())
        self.selection_layout.addWidget(self.btn_bookmark)
        self.selection_layout.addWidget(self.btn_note)
        self.selection_layout.addWidget(self._create_sep())
        self.selection_layout.addWidget(self.btn_clear)
        self.selection_layout.addWidget(self.btn_clear_symbols)
        self.selection_layout.addWidget(self.btn_clear_all)
        
        self.main_layout.addWidget(self.selection_container)
        self.main_layout.addWidget(self.color_wrapper)

    def _create_btn(self, text, mark_type):
        btn = QPushButton(text)
        btn.setObjectName("action_btn")
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                padding: 6px 12px;
                text-align: left;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #444;
            }
        """)
        btn.installEventFilter(self)
        btn.clicked.connect(lambda: self._on_select(mark_type, HIGHLIGHT_COLORS["yellow"]))
        return btn

    def _create_action_btn(self, text):
        btn = QPushButton(text)
        btn.setObjectName("action_btn")
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                padding: 6px 12px;
                text-align: left;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #444;
            }
        """)
        # Ensure action buttons hide the color panel
        btn.installEventFilter(self)
        return btn

    def _create_sep(self):
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        sep.setStyleSheet("background-color: #555; min-height: 1px; max-height: 1px; margin: 4px 5px;")
        return sep

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Enter:
            if obj in self.mark_buttons:
                self.active_mark_type = self.mark_buttons[obj]
                self._show_color_panel(obj)
            else:
                self.color_container.hide()
                self.adjustSize()
        return super().eventFilter(obj, event)

    def _show_color_panel(self, target_btn):
        # Calculate vertical offset to center color panel with button
        # y() is relative to selection_container
        y_center_btn = target_btn.y() + (target_btn.height() // 2)
        # Margin of selection_container
        y_offset = y_center_btn - (self.color_container.sizeHint().height() // 2) + 5
        
        self.top_spacer.setFixedHeight(max(0, y_offset))
        self.color_container.show()
        self.adjustSize()

    def _on_color_clicked(self, hex_code):
        self._on_select(self.active_mark_type, hex_code)

    def _on_select(self, mark_type, color):
        self.markSelected.emit(mark_type, color)
        self.hide()

    def keyPressEvent(self, event):
        # Close popup on any key press (especially Esc or Ctrl+C)
        # but don't accept the event so it can bubble up to the main window/scene
        self.hide()
        event.ignore()

    def show_at(self, pos):
        self.color_container.hide()
        self.move(pos)
        self.show()
        self.adjustSize()
