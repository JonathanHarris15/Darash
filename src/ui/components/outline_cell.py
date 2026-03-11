import re
from PySide6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QFrame, QSizePolicy, QTextEdit
)
from PySide6.QtCore import Qt, Signal, QTimer, QEvent

class DraggableLabel(QLabel):
    dragged = Signal(int, bool)
    jumpRequested = Signal()
    
    def __init__(self, text, is_start, parent=None):
        super().__init__(text, parent)
        self.is_start = is_start
        self.setCursor(Qt.SizeVerCursor)
        self.setStyleSheet("""
            QLabel { color: #569cd6; font-weight: bold; font-family: 'Consolas'; font-size: 14px; padding: 2px; }
            QLabel:hover { text-decoration: underline; background-color: rgba(255,255,255,0.1); border-radius: 2px;}
        """)
        self._drag_start_y = None
        self._last_delta_verses = 0
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_y = event.globalPosition().y()
            self._last_delta_verses = 0
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        if self._drag_start_y is not None:
            dy = event.globalPosition().y() - self._drag_start_y
            delta_verses = int(dy // 10) # 10 pixels per verse sensitivity
            if delta_verses != self._last_delta_verses:
                is_word_drag = bool(event.modifiers() & Qt.ControlModifier)
                self.dragged.emit(delta_verses - self._last_delta_verses, is_word_drag)
                self._last_delta_verses = delta_verses
                
    def mouseReleaseEvent(self, event):
        if self._drag_start_y is not None:
            if self._last_delta_verses == 0:
                self.jumpRequested.emit()
            self._drag_start_y = None
        super().mouseReleaseEvent(event)

class DraggableRefWidget(QWidget):
    jumpRequested = Signal()
    boundaryDragged = Signal(bool, int, bool)

    def __init__(self, start_text, end_text, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        b1 = QLabel("[")
        b1.setStyleSheet("color: #777; font-weight: bold; font-family: 'Consolas'; font-size: 14px;")
        
        self.start_lbl = DraggableLabel(start_text, True)
        self.start_lbl.jumpRequested.connect(self.jumpRequested)
        self.start_lbl.dragged.connect(lambda d, w: self.boundaryDragged.emit(True, d, w))
        
        sep_lbl = QLabel("-")
        sep_lbl.setStyleSheet("color: #777; font-weight: bold; font-family: 'Consolas'; font-size: 14px; margin: 0 2px;")
        
        self.end_lbl = DraggableLabel(end_text, False)
        self.end_lbl.jumpRequested.connect(self.jumpRequested)
        self.end_lbl.dragged.connect(lambda d, w: self.boundaryDragged.emit(False, d, w))
        
        b2 = QLabel("]")
        b2.setStyleSheet("color: #777; font-weight: bold; font-family: 'Consolas'; font-size: 14px;")
        
        layout.addWidget(b1)
        layout.addWidget(self.start_lbl)
        layout.addWidget(sep_lbl)
        layout.addWidget(self.end_lbl)
        layout.addWidget(b2)

class PrefixWidget(QLabel):
    """
    Focusable bullet label that handles outline manipulation keys.
    """
    focused = Signal()
    manipulateRequested = Signal(str) # "sibling", "child", "up", "down", "delete"

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFocusPolicy(Qt.StrongFocus if text else Qt.NoFocus)
        self.setCursor(Qt.PointingHandCursor)
        self._update_style(False)

    def _update_style(self, has_focus):
        if has_focus:
            self.setStyleSheet("""
                QLabel {
                    color: #ffffff; 
                    background-color: #555; 
                    border-radius: 2px;
                    font-weight: bold; 
                    font-family: 'Consolas'; 
                    font-size: 14px;
                    padding: 0px 4px;
                }
            """)
        else:
            self.setStyleSheet("""
                QLabel {
                    color: #ce9178; 
                    background-color: transparent;
                    font-weight: bold; 
                    font-family: 'Consolas'; 
                    font-size: 14px;
                    padding: 0px 4px;
                }
                QLabel:hover {
                    color: #ffffff;
                    background-color: #444;
                    border-radius: 2px;
                }
            """)

    def focusInEvent(self, event):
        self._update_style(True)
        self.focused.emit()
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self._update_style(False)
        super().focusOutEvent(event)

    def event(self, event):
        if event.type() == QEvent.KeyPress and event.key() == Qt.Key_Tab:
            self.manipulateRequested.emit("child")
            return True
        return super().event(event)

    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key_Return, Qt.Key_Enter):
            self.manipulateRequested.emit("sibling")
            return
        if key == Qt.Key_Up:
            self.manipulateRequested.emit("up")
            return
        if key == Qt.Key_Down:
            self.manipulateRequested.emit("down")
            return
        if key in (Qt.Key_Delete, Qt.Key_Backspace):
            self.manipulateRequested.emit("delete")
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        self.setFocus()
        super().mousePressEvent(event)

class OutlineCell(QFrame):
    """
    A single row in the outline cell system.
    """
    splitRequested = Signal(str, str)
    jumpRequested = Signal(str, str, str)
    contentChanged = Signal()
    focusNextRequested = Signal(str, bool) # node_id, forward

    def __init__(self, node, level, index, panel, parent=None):
        super().__init__(parent)
        self.node = node
        self.level = level
        self.index = index
        self.panel = panel
        
        self.setObjectName("OutlineCell")
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 1, 0, 1)
        layout.setSpacing(8)
        
        # 1. Indentation Spacer
        indent_spacer = QWidget()
        indent_spacer.setFixedWidth(level * 30)
        layout.addWidget(indent_spacer, alignment=Qt.AlignTop)
        
        # 2. Prefix (Focusable Bullet) Area
        prefix_area = QWidget()
        prefix_area.setFixedWidth(40)
        prefix_layout = QHBoxLayout(prefix_area)
        prefix_layout.setContentsMargins(0, 0, 0, 0)
        prefix_layout.setSpacing(0)
        prefix_layout.addStretch() # Push bullet to the right
        
        self.prefix_widget = PrefixWidget(self._get_prefix())
        self.prefix_widget.manipulateRequested.connect(self._on_manipulate)
        prefix_layout.addWidget(self.prefix_widget)
        
        layout.addWidget(prefix_area, alignment=Qt.AlignTop)
        
        # 3. Draggable Reference Link Widget
        start_txt, end_txt = self.panel._format_ref_parts(node["range"]["start"], node["range"]["end"])
        self.ref_widget = DraggableRefWidget(start_txt, end_txt)
        self.ref_widget.jumpRequested.connect(self._on_ref_clicked)
        self.ref_widget.boundaryDragged.connect(self._on_boundary_dragged)
        layout.addWidget(self.ref_widget, alignment=Qt.AlignTop)
        
        # 4. Summary Edit (Multi-line)
        self.summary_edit = QTextEdit()
        self.summary_edit.setPlainText(node.get("summary", ""))
        self.summary_edit.setPlaceholderText("Section summary...")
        self.summary_edit.setAcceptRichText(False)
        self.summary_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.summary_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Auto-height logic
        self.summary_edit.setFixedHeight(24) # Initial compact height
        self.summary_edit.textChanged.connect(self._adjust_height)
        
        self.summary_edit.setStyleSheet("""
            QTextEdit {
                background-color: transparent;
                color: #d4d4d4;
                border: none;
                border-bottom: 1px solid #333;
                font-size: 14px;
                padding: 0px 2px;
            }
            QTextEdit:focus {
                border-bottom: 1px solid #569cd6;
                background-color: #252526;
            }
        """)
        self.summary_edit.textChanged.connect(self._on_summary_changed)
        layout.addWidget(self.summary_edit, alignment=Qt.AlignTop)
        
        # Delay height adjustment slightly to ensure document is laid out
        QTimer.singleShot(10, self._adjust_height)

        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self._save_changes)
        
    def _adjust_height(self):
        # Ensure the document knows its width for wrapping to calculate height correctly
        width = self.summary_edit.viewport().width()
        if width > 0:
            self.summary_edit.document().setTextWidth(width)
            
        doc_height = self.summary_edit.document().size().height()
        # Tighten the height adjustment, ensuring it doesn't clip multi-line text
        new_height = max(24, int(doc_height) + 4)
        
        if self.summary_edit.height() != new_height:
            self.summary_edit.setFixedHeight(new_height)
            self.adjustSize() 
            if self.parentWidget():
                self.parentWidget().updateGeometry()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Re-adjust height when cell width changes (e.g. window resize)
        self._adjust_height()

    def _get_prefix(self):
        if self.level == 0: return ""
        if self.level == 1: return f"{self.index + 1}."
        if self.level == 2: return f"{chr(ord('a') + (self.index % 26))}."
        if self.level == 3:
            def to_roman(n):
                n += 1
                val = [10, 9, 5, 4, 1]
                syb = ["x", "ix", "v", "iv", "i"]
                res = ""
                for i in range(len(val)):
                    while n >= val[i]: res += syb[i]; n -= val[i]
                return res
            return f"{to_roman(self.index)}."
        return "-"

    def _on_manipulate(self, action):
        if action in ("sibling", "child", "delete"):
            self.splitRequested.emit(action, self.node["id"])
        elif action == "up":
            self.focusNextRequested.emit(self.node["id"], False)
        elif action == "down":
            self.focusNextRequested.emit(self.node["id"], True)

    def _on_ref_clicked(self):
        start_ref = self.node["range"]["start"]
        m = re.match(r"(.*) (\d+):(\d+)", start_ref)
        if m: self.jumpRequested.emit(m.group(1), m.group(2), m.group(3))

    def _on_boundary_dragged(self, is_start, delta, is_word_drag):
        loader = self.panel.outline_manager.study_manager.loader
        if self.panel.outline_manager.adjust_node_boundary(self.panel.root_node_id, self.node["id"], is_start, delta, loader, is_word_drag):
            self.panel.refresh_labels()
            self.contentChanged.emit()

    def _on_summary_changed(self):
        self.save_timer.start(1000) # Wait 1s after last character before emitting refresh

    def _save_changes(self):
        self.node["summary"] = self.summary_edit.toPlainText()
        self.panel.outline_manager.study_manager.save_data()
        self.contentChanged.emit()
