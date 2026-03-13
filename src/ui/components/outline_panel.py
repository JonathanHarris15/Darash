import re
import uuid
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, 
    QComboBox, QHBoxLayout, QPushButton, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QTimer
from src.ui.components.outline_cell import OutlineCell
from src.ui.components.spellcheck_title_edit import SpellcheckTitleEdit
from src.core.theme import Theme

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
        self.title_edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: {Theme.BG_SECONDARY};
                color: {Theme.TEXT_PRIMARY};
                border: 1px solid {Theme.BORDER_DEFAULT};
                border-radius: 4px;
                padding: 6px;
                font-size: 14px;
                font-weight: bold;
            }}
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
        if checked: self.editRequested.emit(self.root_node_id)
        else: self.editRequested.emit("") # Turn off

    def update_active_state(self, is_active):
        self.edit_btn.blockSignals(True); self.edit_btn.setChecked(is_active); self.edit_btn.blockSignals(False)
        if is_active:
            self.edit_btn.setText("Currently Editing in Reader")
            self.edit_btn.setStyleSheet(f"""
                QPushButton {{ background-color: {Theme.ACCENT_PRIMARY}; color: {Theme.BG_PRIMARY}; border: 1px solid {Theme.ACCENT_PRIMARY}; border-radius: 4px; padding: 0px 8px; font-weight: bold; }}
                QPushButton:hover {{ background-color: {Theme.ACCENT_PRIMARY}; filter: brightness(1.1); }}
            """)
        else:
            self.edit_btn.setText("Edit Outline in Reader")
            self.edit_btn.setStyleSheet(f"""
                QPushButton {{ background-color: {Theme.BG_TERTIARY}; color: {Theme.TEXT_SECONDARY}; border: 1px solid {Theme.BORDER_DEFAULT}; border-radius: 4px; padding: 0px 8px; }}
                QPushButton:hover {{ background-color: {Theme.BORDER_LIGHT}; color: {Theme.TEXT_PRIMARY}; border-color: {Theme.ACCENT_PRIMARY}; }}
            """)

    def refresh(self):
        """Rebuilds the cell list from the tree data."""
        if not self.root_node_id: return
        root = self.outline_manager.get_node(self.root_node_id)
        if not root: return
        new_hash = self._get_structure_hash(root) + "|" + self.ref_format_combo.currentText()
        if new_hash == self._structure_hash:
            if not self.title_edit.hasFocus():
                self._is_internal_change = True; self.title_edit.setText(root.get("title", "")); self._is_internal_change = False
            return
        self._structure_hash = new_hash
        while self.container_layout.count():
            item = self.container_layout.takeAt(0); widget = item.widget()
            if widget: widget.deleteLater()
        self._is_internal_change = True; self.title_edit.setText(root.get("title", "")); self._is_internal_change = False
        self._add_node_cells(root, level=0, index=0); self.container_layout.addStretch()

    def _add_node_cells(self, node, level, index):
        cell = OutlineCell(node, level, index, self)
        cell.jumpRequested.connect(self.jumpRequested.emit)
        cell.splitRequested.connect(self._on_split_requested)
        cell.contentChanged.connect(self.outlineChanged.emit)
        cell.focusNextRequested.connect(self._on_focus_next_requested)
        self.container_layout.addWidget(cell)
        for i, child in enumerate(node.get("children", [])): self._add_node_cells(child, level + 1, i)

    def _on_focus_next_requested(self, node_id, forward):
        cells = []
        for i in range(self.container_layout.count()):
            w = self.container_layout.itemAt(i).widget()
            if isinstance(w, OutlineCell): cells.append(w)
        for i, cell in enumerate(cells):
            if cell.node["id"] == node_id:
                target_idx = i + (1 if forward else -1)
                while 0 <= target_idx < len(cells):
                    if cells[target_idx].prefix_widget.focusPolicy() != Qt.NoFocus:
                        cells[target_idx].prefix_widget.setFocus(); break
                    target_idx += (1 if forward else -1)
                break

    def _on_split_requested(self, split_type, node_id):
        if split_type == "delete":
            if self.outline_manager.delete_node_smart(node_id):
                self._structure_hash = None; self.refresh(); self.outlineChanged.emit()
            return
        node = self.outline_manager.get_node(node_id)
        if not node: return
        split1, split2 = self.outline_manager._calculate_range_split(node["range"]["start"], node["range"]["end"])
        if not split1 or not split2: return
        if split_type == "child":
            c1 = {"id": str(uuid.uuid4()), "title": "", "summary": "", "range": {"start": node["range"]["start"], "end": self.outline_manager._get_end_ref_from_split(split1)}, "children": [], "expanded": True}
            c2 = {"id": str(uuid.uuid4()), "title": "", "summary": "", "range": {"start": self.outline_manager._get_start_ref_from_split(split2), "end": node["range"]["end"]}, "children": [], "expanded": True}
            node["children"] = [c1, c2]; node["split_levels"] = [self.outline_manager._get_node_level(self.outline_manager.get_outlines(), node_id) + 1]; focus_id = c1["id"]
        else:
            parent = self._find_parent(self.outline_manager.get_node(self.root_node_id), node_id)
            if not parent: return
            idx = -1
            for i, c in enumerate(parent["children"]):
                if c["id"] == node_id: idx = i; break
            if idx != -1:
                node["range"]["end"] = self.outline_manager._get_end_ref_from_split(split1)
                sibling = {"id": str(uuid.uuid4()), "title": "", "summary": "", "range": {"start": self.outline_manager._get_start_ref_from_split(split2), "end": parent["range"]["end"] if idx == len(parent["children"])-1 else parent["children"][idx+1]["range"]["start"]}, "children": [], "expanded": True}
                if idx == len(parent["children"]) - 1: sibling["range"]["end"] = parent["range"]["end"]
                parent["children"].insert(idx + 1, sibling); parent["split_levels"] = [1] * (len(parent["children"]) - 1); focus_id = sibling["id"]
        self.outline_manager.study_manager.save_data(); self._structure_hash = None; self.refresh(); self.outlineChanged.emit()
        QTimer.singleShot(50, lambda: self._focus_summary(focus_id))

    def _focus_summary(self, node_id):
        for i in range(self.container_layout.count()):
            w = self.container_layout.itemAt(i).widget()
            if isinstance(w, OutlineCell) and w.node["id"] == node_id:
                w.summary_edit.setFocus(); break

    def _find_parent(self, current, target_id):
        for child in current.get("children", []):
            if child["id"] == target_id: return current
            p = self._find_parent(child, target_id); 
            if p: return p
        return None

    def _on_title_changed(self, text=None):
        if self._is_internal_change: return
        self.title_save_timer.start(1000)

    def _save_title(self):
        if self.root_node_id:
            node = self.outline_manager.get_node(self.root_node_id)
            if node: node["title"] = self.title_edit.text(); self.outline_manager.study_manager.save_data(); self.outlineChanged.emit()

    def _format_ref_parts(self, start, end):
        fmt = self.ref_format_combo.currentText()
        def parse(ref):
            if not ref: return None, None, None, None
            m = re.match(r"(.*) (\d+):(\d+)([a-zA-Z]+)?", str(ref))
            if m: return m.groups()
            return None, None, None, None
        s_book, s_chap, s_verse, s_part = parse(start); e_book, e_chap, e_verse, e_part = parse(end)
        if not s_book: return f"{start}", f"{end}"
        s_v = f"{s_verse}{s_part if s_part else ''}"; e_v = f"{e_verse}{e_part if e_part else ''}"
        if fmt == "C:V":
            if s_chap == e_chap: return f"{s_chap}:{s_v}", f"{e_v}"
            return f"{s_chap}:{s_v}", f"{e_chap}:{e_v}"
        elif fmt == "v#": return f"v{s_v}", f"{e_v}"
        else:
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
                n = nodes_dict[w.node["id"]]; w.node = n; s_txt, e_txt = self._format_ref_parts(n["range"]["start"], n["range"]["end"])
                w.ref_widget.start_lbl.setText(s_txt if s_txt else ""); w.ref_widget.end_lbl.setText(e_txt if e_txt else "")
        self._structure_hash = self._get_structure_hash(root) + "|" + self.ref_format_combo.currentText()

    def normalize_text(self): self.refresh()

    def _get_structure_hash(self, node):
        s = node["id"] + f"[{node['range']['start']}-{node['range']['end']}]" + str(node.get("split_levels", []))
        for child in node.get("children", []): s += "|" + self._get_structure_hash(child)
        return s
