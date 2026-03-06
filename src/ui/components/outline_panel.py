import re
import uuid
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, 
    QComboBox, QHBoxLayout, QPushButton, QScrollArea,
    QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QRect, QEvent, QTimer
from PySide6.QtGui import QColor, QFont, QPalette

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
        if key == Qt.Key_Delete:
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
        from PySide6.QtWidgets import QTextEdit
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
        self.panel.outline_manager.study_manager.save_study()
        self.contentChanged.emit()

class OutlinePanel(QWidget):
    """
    A modern cell-based editor for hierarchical Bible outlines.
    """
    jumpRequested = Signal(str, str, str)
    outlineChanged = Signal()
    editRequested = Signal(str) # node_id

    def __init__(self, outline_manager, root_node_id=None, parent=None):
        super().__init__(parent)
        self.outline_manager = outline_manager
        self.root_node_id = root_node_id
        self._is_internal_change = False
        self._structure_hash = None
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(4)
        
        # 1. Header with Formatting Options & Edit Toggle
        header_layout = QHBoxLayout()
        
        self.edit_btn = QPushButton("Edit Outline in Reader")
        self.edit_btn.setCheckable(True)
        self.edit_btn.setToolTip("Enable visual editing in the reading view")
        self.edit_btn.setFixedHeight(24)
        self.edit_btn.clicked.connect(self._on_edit_toggled)
        header_layout.addWidget(self.edit_btn)
        
        header_layout.addStretch()
        
        self.ref_format_combo = QComboBox()
        self.ref_format_combo.addItems(["Book C:V", "C:V", "v#"])
        self.ref_format_combo.currentIndexChanged.connect(self.refresh)
        header_layout.addWidget(self.ref_format_combo)
        layout.addLayout(header_layout)

        # 2. Title Edit Bar
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Outline Title")
        self.title_edit.setStyleSheet("""
            QLineEdit {
                background-color: #252526;
                color: #eee;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 6px;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        self.title_edit.textChanged.connect(self._on_title_changed)
        layout.addWidget(self.title_edit)
        
        # 3. Scroll Area for Cells
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        self.container = QWidget()
        self.container.setStyleSheet("background-color: transparent;")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setAlignment(Qt.AlignTop)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(0)
        
        self.scroll_area.setWidget(self.container)
        layout.addWidget(self.scroll_area)
        
        self.title_save_timer = QTimer(self)
        self.title_save_timer.setSingleShot(True)
        self.title_save_timer.timeout.connect(self._save_title)
        
        self.update_active_state(False)
        self.refresh()

    def _on_edit_toggled(self, checked):
        if checked:
            self.editRequested.emit(self.root_node_id)
        else:
            self.editRequested.emit("") # Turn off

    def update_active_state(self, is_active):
        self.edit_btn.blockSignals(True)
        self.edit_btn.setChecked(is_active)
        self.edit_btn.blockSignals(False)
        
        if is_active:
            self.edit_btn.setText("Currently Editing in Reader")
            self.edit_btn.setStyleSheet("""
                QPushButton {
                    background-color: #005a9e;
                    color: white;
                    border: 1px solid #0078d4;
                    border-radius: 4px;
                    padding: 0px 8px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #0078d4; }
            """)
        else:
            self.edit_btn.setText("Edit Outline in Reader")
            self.edit_btn.setStyleSheet("""
                QPushButton {
                    background-color: #333;
                    color: #ccc;
                    border: 1px solid #555;
                    border-radius: 4px;
                    padding: 0px 8px;
                }
                QPushButton:hover { background-color: #444; color: white; border-color: #0078d4; }
            """)

    def refresh(self):
        """Rebuilds the cell list from the tree data."""
        if not self.root_node_id: return
        
        root = self.outline_manager.get_node(self.root_node_id)
        if not root: return

        # Only rebuild if structure or format changed
        new_hash = self._get_structure_hash(root) + "|" + self.ref_format_combo.currentText()
        if new_hash == self._structure_hash:
            # Structure same, just update title if not focused
            if not self.title_edit.hasFocus():
                self._is_internal_change = True
                self.title_edit.setText(root.get("title", ""))
                self._is_internal_change = False
            return

        self._structure_hash = new_hash

        # Clear current cells
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            
        self._is_internal_change = True
        self.title_edit.setText(root.get("title", ""))
        self._is_internal_change = False
        
        # Recursively add cells
        self._add_node_cells(root, level=0, index=0)
        
        # Add stretch to push everything to the top
        self.container_layout.addStretch()

    def _add_node_cells(self, node, level, index):
        cell = OutlineCell(node, level, index, self)
        cell.jumpRequested.connect(self.jumpRequested.emit)
        cell.splitRequested.connect(self._on_split_requested)
        cell.contentChanged.connect(self.outlineChanged.emit)
        cell.focusNextRequested.connect(self._on_focus_next_requested)
        self.container_layout.addWidget(cell)
        
        for i, child in enumerate(node.get("children", [])):
            self._add_node_cells(child, level + 1, i)

    def _on_focus_next_requested(self, node_id, forward):
        # Find all cells
        cells = []
        for i in range(self.container_layout.count()):
            w = self.container_layout.itemAt(i).widget()
            if isinstance(w, OutlineCell): cells.append(w)
            
        for i, cell in enumerate(cells):
            if cell.node["id"] == node_id:
                target_idx = i + (1 if forward else -1)
                while 0 <= target_idx < len(cells):
                    if cells[target_idx].prefix_widget.focusPolicy() != Qt.NoFocus:
                        cells[target_idx].prefix_widget.setFocus()
                        break
                    target_idx += (1 if forward else -1)
                break

    def _on_split_requested(self, split_type, node_id):
        # Implementation of splitting logic in the tree
        if split_type == "delete":
            if self.outline_manager.delete_node_smart(node_id):
                self._structure_hash = None # Force full rebuild
                self.refresh()
                self.outlineChanged.emit()
            return

        node = self.outline_manager.get_node(node_id)
        if not node: return
        
        split1, split2 = self.outline_manager._calculate_range_split(node["range"]["start"], node["range"]["end"])
        if not split1 or not split2: return
        
        if split_type == "child":
            # Tab behavior: Make current node a parent of two new children
            c1 = {
                "id": str(uuid.uuid4()),
                "title": "",
                "summary": "",
                "range": {"start": node["range"]["start"], "end": self.outline_manager._get_end_ref_from_split(split1)},
                "children": [], "expanded": True
            }
            c2 = {
                "id": str(uuid.uuid4()),
                "title": "",
                "summary": "",
                "range": {"start": self.outline_manager._get_start_ref_from_split(split2), "end": node["range"]["end"]},
                "children": [], "expanded": True
            }
            node["children"] = [c1, c2]
            node["split_levels"] = [self.outline_manager._get_node_level(self.outline_manager.get_outlines(), node_id) + 1]
            focus_id = c1["id"]
        else:
            # Enter behavior: Split current node's range with a new sibling
            # This is harder because we need the parent of node_id
            parent = self._find_parent(self.outline_manager.get_node(self.root_node_id), node_id)
            if not parent: return # Can't split root as sibling here
            
            # Find index of node in parent
            idx = -1
            for i, c in enumerate(parent["children"]):
                if c["id"] == node_id: idx = i; break
            
            if idx != -1:
                # Update current node
                node["range"]["end"] = self.outline_manager._get_end_ref_from_split(split1)
                # Create sibling
                sibling = {
                    "id": str(uuid.uuid4()),
                    "title": "",
                    "summary": "",
                    "range": {"start": self.outline_manager._get_start_ref_from_split(split2), "end": parent["range"]["end"] if idx == len(parent["children"])-1 else parent["children"][idx+1]["range"]["start"]},
                    "children": [], "expanded": True
                }
                # If splitting the last child, the sibling takes the rest of the parent's range
                if idx == len(parent["children"]) - 1:
                    sibling["range"]["end"] = parent["range"]["end"]
                    
                parent["children"].insert(idx + 1, sibling)
                # Rebuild split levels
                parent["split_levels"] = [1] * (len(parent["children"]) - 1)
                focus_id = sibling["id"]

        self.outline_manager.study_manager.save_study()
        self._structure_hash = None # Force rebuild to show new nodes
        self.refresh()
        self.outlineChanged.emit()
        
        # Focus the new item's summary
        QTimer.singleShot(50, lambda: self._focus_summary(focus_id))

    def _focus_summary(self, node_id):
        for i in range(self.container_layout.count()):
            w = self.container_layout.itemAt(i).widget()
            if isinstance(w, OutlineCell) and w.node["id"] == node_id:
                w.summary_edit.setFocus()
                break

    def _find_parent(self, current, target_id):
        for child in current.get("children", []):
            if child["id"] == target_id: return current
            p = self._find_parent(child, target_id)
            if p: return p
        return None

    def _on_title_changed(self, text):
        if self._is_internal_change: return
        self.title_save_timer.start(1000)

    def _save_title(self):
        if self.root_node_id:
            node = self.outline_manager.get_node(self.root_node_id)
            if node:
                node["title"] = self.title_edit.text()
                self.outline_manager.study_manager.save_study()
                self.outlineChanged.emit()

    def _format_ref_parts(self, start, end):
        fmt = self.ref_format_combo.currentText()
        def parse(ref):
            if not ref: return None, None, None, None
            m = re.match(r"(.*) (\d+):(\d+)([a-zA-Z]+)?", str(ref))
            if m: return m.groups()
            return None, None, None, None
        s_book, s_chap, s_verse, s_part = parse(start)
        e_book, e_chap, e_verse, e_part = parse(end)
        if not s_book: return f"{start}", f"{end}"
        s_v = f"{s_verse}{s_part if s_part else ''}"
        e_v = f"{e_verse}{e_part if e_part else ''}"
        if fmt == "C:V":
            if s_chap == e_chap: return f"{s_chap}:{s_v}", f"{e_v}"
            return f"{s_chap}:{s_v}", f"{e_chap}:{e_v}"
        elif fmt == "v#":
            return f"v{s_v}", f"{e_v}"
        else: # Full
            if s_book == e_book:
                if s_chap == e_chap: return f"{s_book} {s_chap}:{s_v}", f"{e_v}"
                return f"{s_book} {s_chap}:{s_v}", f"{e_chap}:{e_v}"
            return f"{start}", f"{end}"

    def refresh_labels(self):
        if not self.root_node_id: return
        root = self.outline_manager.get_node(self.root_node_id)
        if not root: return
        
        def get_all_nodes(n):
            res = [n]
            for c in n.get('children', []): res.extend(get_all_nodes(c))
            return res
            
        nodes_dict = {n['id']: n for n in get_all_nodes(root)}
        
        for i in range(self.container_layout.count()):
            w = self.container_layout.itemAt(i).widget()
            if isinstance(w, OutlineCell) and w.node["id"] in nodes_dict:
                n = nodes_dict[w.node["id"]]
                w.node = n
                s_txt, e_txt = self._format_ref_parts(n["range"]["start"], n["range"]["end"])
                w.ref_widget.start_lbl.setText(s_txt if s_txt else "")
                w.ref_widget.end_lbl.setText(e_txt if e_txt else "")
                
        self._structure_hash = self._get_structure_hash(root) + "|" + self.ref_format_combo.currentText()

    def normalize_text(self):
        # No longer used in cell system, but kept for compatibility if called
        self.refresh()

    def _get_structure_hash(self, node):
        """Returns a string representing the structure of the tree (ids, order, ranges, and split levels)."""
        s = node["id"]
        # Include range and split_levels in hash for structural/visual changes
        s += f"[{node['range']['start']}-{node['range']['end']}]"
        s += str(node.get("split_levels", []))
        for child in node.get("children", []):
            s += "|" + self._get_structure_hash(child)
        return s
