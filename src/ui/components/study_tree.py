from PySide6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QStyle, QColorDialog, 
    QInputDialog, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QAction, QColor
from src.utils.menu_utils import create_menu
from src.ui.theme import Theme

class StudyTreeWidget(QTreeWidget):
    jumpRequested = Signal(str, str, str)
    noteOpenRequested = Signal(str, str)
    outlineOpenRequested = Signal(str)
    outlineDeleted = Signal(str)
    dataChanged = Signal()

    def __init__(self, study_manager, symbol_manager, parent=None):
        super().__init__(parent)
        self.study_manager = study_manager
        self.symbol_manager = symbol_manager
        
        self.setHeaderHidden(True)
        self.setIndentation(15)
        self.setSelectionMode(QTreeWidget.ExtendedSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QTreeWidget.InternalMove)
        self.setDropIndicatorShown(True)
        
        self.setStyleSheet(f"""
            QTreeWidget {{ background-color: {Theme.BG_PRIMARY}; border: 1px solid {Theme.BORDER_DEFAULT}; color: {Theme.TEXT_SECONDARY}; }}
            QTreeWidget::item {{ padding: 4px; }}
            QTreeWidget::item:hover {{ background-color: {Theme.BG_SECONDARY}; }}
            QTreeWidget::item:selected {{ background-color: {Theme.BG_TERTIARY}; color: {Theme.TEXT_PRIMARY}; }}
        """)
        
        self.itemDoubleClicked.connect(self._on_item_clicked)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)

    def dropEvent(self, event):
        source_item = self.currentItem()
        if not source_item:
            super().dropEvent(event); return
        target_item = self.itemAt(event.pos())
        if not target_item:
            event.ignore(); return
        source_type = source_item.data(0, Qt.UserRole)
        target_type = target_item.data(0, Qt.UserRole)
        if source_type == "note":
            note_key = source_item.data(0, Qt.UserRole + 1)
            if target_type == "note_folder":
                self.study_manager.move_note(note_key, target_item.data(0, Qt.UserRole + 1))
                self.refresh(); event.accept()
            elif target_type == "notes_header":
                self.study_manager.move_note(note_key, "")
                self.refresh(); event.accept()
            else: event.ignore()
        elif source_type == "note_folder":
            source_path = source_item.data(0, Qt.UserRole + 1)
            if target_type == "notes_header":
                self.study_manager.move_folder(source_path, "")
                self.refresh(); event.accept()
            elif target_type == "note_folder":
                target_path = target_item.data(0, Qt.UserRole + 1)
                if source_path != target_path and not target_path.startswith(f"{source_path}/"):
                    self.study_manager.move_folder(source_path, target_path)
                    self.refresh(); event.accept()
                else: event.ignore()
            else: event.ignore()
        else: event.ignore()

    def _get_range_string(self, group_marks):
        if not group_marks: return ""
        m0 = group_marks[0]
        if len(group_marks) == 1: return f"{m0['book']} {m0['chapter']}:{m0['verse_num']}"
        sorted_marks = sorted(group_marks, key=lambda x: int(x['verse_num']))
        start = sorted_marks[0]; end = sorted_marks[-1]
        if start['book'] == end['book'] and start['chapter'] == end['chapter']:
            return f"{start['book']} {start['chapter']}:{start['verse_num']}-{end['verse_num']}"
        return f"{start['book']} {start['chapter']}:{start['verse_num']} - {end['book']} {end['chapter']}:{end['verse_num']}"

    def refresh(self):
        expanded_paths = set()
        def save_state(item, path=""):
            current_path = f"{path}/{item.text(0)}" if path else item.text(0)
            if item.isExpanded(): expanded_paths.add(current_path)
            for i in range(item.childCount()): save_state(item.child(i), current_path)
        for i in range(self.topLevelItemCount()): save_state(self.topLevelItem(i))
        self.clear()

        # 1. Outlines
        outlines_root = QTreeWidgetItem(self, ["Outlines"])
        outlines = self.study_manager.outline_manager.get_outlines()
        for outline in outlines:
            item = QTreeWidgetItem(outlines_root, [outline["title"]])
            item.setData(0, Qt.UserRole, "outline"); item.setData(0, Qt.UserRole + 1, outline["id"])

        # 2. Marks
        marks_root = QTreeWidgetItem(self, ["Marks"])
        mark_categories = {
            "highlight": QTreeWidgetItem(marks_root, ["Highlights"]),
            "underline": QTreeWidgetItem(marks_root, ["Underlines"]),
            "box": QTreeWidgetItem(marks_root, ["Boxes"]),
            "circle": QTreeWidgetItem(marks_root, ["Circles"]),
            "arrow": QTreeWidgetItem(marks_root, ["Arrows"]),
            "verse_mark": QTreeWidgetItem(marks_root, ["Verse Marks"])
        }
        all_marks = self.study_manager.data.get("marks", [])
        type_grouped_marks = {}
        for i, m in enumerate(all_marks):
            m_type = m.get("type", "highlight")
            if m_type not in type_grouped_marks: type_grouped_marks[m_type] = {"ungrouped": []}
            gid = m.get("group_id")
            if gid:
                if gid not in type_grouped_marks[m_type]: type_grouped_marks[m_type][gid] = []
                type_grouped_marks[m_type][gid].append(i)
            else: type_grouped_marks[m_type]["ungrouped"].append(i)
        for m_type, groups in type_grouped_marks.items():
            parent = mark_categories.get(m_type, marks_root)
            for gid, indices in groups.items():
                if gid == "ungrouped": continue
                group_data = [all_marks[i] for i in indices]
                item = QTreeWidgetItem(parent, [self._get_range_string(group_data)])
                item.setData(0, Qt.UserRole, "mark_group"); item.setData(0, Qt.UserRole + 1, indices); item.setData(0, Qt.UserRole + 2, group_data[0])
            for i in groups["ungrouped"]:
                m = all_marks[i]
                item = QTreeWidgetItem(parent, [f"{m['book']} {m['chapter']}:{m['verse_num']}"])
                item.setData(0, Qt.UserRole, "mark"); item.setData(0, Qt.UserRole + 1, m); item.setData(0, Qt.UserRole + 2, i)
        
        # Arrows
        arrow_parent = mark_categories["arrow"]
        verse_arrow_counts = {}
        sorted_keys = sorted(self.study_manager.data.get("arrows", {}).keys())
        for key in sorted_keys:
            parts = key.split('|')
            if len(parts) < 3: continue
            ref = f"{parts[0]} {parts[1]}:{parts[2]}"
            if ref not in verse_arrow_counts: verse_arrow_counts[ref] = 0
            for i, a in enumerate(self.study_manager.data["arrows"][key]):
                verse_arrow_counts[ref] += 1
                item = QTreeWidgetItem(arrow_parent, [f"{ref} Arrow {verse_arrow_counts[ref]}"])
                item.setData(0, Qt.UserRole, "arrow"); item.setData(0, Qt.UserRole + 1, key); item.setData(0, Qt.UserRole + 2, i)

        # Verse Marks
        vm_parent = mark_categories["verse_mark"]
        verse_marks_data = self.study_manager.data.get("verse_marks", {})
        vm_types = {"heart": "Hearts", "question": "Questions", "attention": "Attention (!!)", "star": "Stars"}
        vm_type_nodes = {}
        for ref, m_type in sorted(verse_marks_data.items()):
            if m_type not in vm_type_nodes:
                vm_type_nodes[m_type] = QTreeWidgetItem(vm_parent, [vm_types.get(m_type, m_type.title())]); vm_type_nodes[m_type].setExpanded(True)
            item = QTreeWidgetItem(vm_type_nodes[m_type], [ref]); item.setData(0, Qt.UserRole, "verse_mark"); item.setData(0, Qt.UserRole + 1, ref)
        for cat in list(mark_categories.values()):
            if cat.childCount() == 0: marks_root.removeChild(cat)

        # 3. Logical Marks
        logical_root = QTreeWidgetItem(self, ["Logical Marks"])
        logical_marks_data = self.study_manager.data.get("logical_marks", {})
        if logical_marks_data:
            type_groups = {}
            for key, m_type in logical_marks_data.items():
                if m_type not in type_groups: type_groups[m_type] = []
                type_groups[m_type].append(key)
            for m_type, keys in type_groups.items():
                group_item = QTreeWidgetItem(logical_root, [m_type.replace("_", " ").title()])
                def sort_key(k):
                    p = k.split('|'); return (p[0], int(p[1]), int(p[2]), int(p[3])) if len(p) >= 4 else (p[0], 0, 0, 0)
                for key in sorted(keys, key=sort_key):
                    parts = key.split('|')
                    if len(parts) >= 3:
                        item = QTreeWidgetItem(group_item, [f"{parts[0]} {parts[1]}:{parts[2]}"])
                        item.setData(0, Qt.UserRole, "logical_mark"); item.setData(0, Qt.UserRole + 1, key)
        if logical_root.childCount() == 0:
            idx = self.indexOfTopLevelItem(logical_root)
            if idx != -1: self.takeTopLevelItem(idx)

        # 4. Symbols
        symbols_root = QTreeWidgetItem(self, ["Symbols"])
        symbol_groups = {}
        for key, s_file in self.study_manager.data.get("symbols", {}).items():
            name = self.symbol_manager.get_symbol_name(s_file)
            if name not in symbol_groups: symbol_groups[name] = []
            symbol_groups[name].append((key, s_file))
        for name in sorted(symbol_groups.keys()):
            group_item = QTreeWidgetItem(symbols_root, [name]); group_item.setData(0, Qt.UserRole, "symbol_type_group")
            def sort_key(x):
                p = x[0].split('|'); return (p[0], int(p[1]), int(p[2]), int(p[3])) if len(p) >= 4 else (p[0], 0, 0, 0)
            for key, s_file in sorted(symbol_groups[name], key=sort_key):
                p = key.split('|'); label = f"{p[0]} {p[1]}:{p[2]}" if len(p) >= 3 else key
                item = QTreeWidgetItem(group_item, [label]); item.setData(0, Qt.UserRole, "symbol"); item.setData(0, Qt.UserRole + 1, key); item.setData(0, Qt.UserRole + 2, s_file)

        # 5. Notes
        notes_root = QTreeWidgetItem(self, ["Notes"]); notes_root.setData(0, Qt.UserRole, "notes_header")
        folder_items = {"": notes_root}
        for f_path in sorted(self.study_manager.data.get("note_folders", [])):
            parts = f_path.split("/"); curr = ""
            for part in parts:
                prev = curr; curr = f"{curr}/{part}" if curr else part
                if curr not in folder_items:
                    item = QTreeWidgetItem(folder_items[prev], [part]); item.setIcon(0, self.style().standardIcon(QStyle.SP_DirIcon))
                    item.setData(0, Qt.UserRole, "note_folder"); item.setData(0, Qt.UserRole + 1, curr); folder_items[curr] = item
        for key, data in self.study_manager.data.get("notes", {}).items():
            folder = data.get("folder", "") if isinstance(data, dict) else ""; parent = folder_items.get(folder, notes_root)
            title = data.get("title", "") if isinstance(data, dict) else data
            if key.startswith("standalone_"): label = title if title else "Untitled Note"
            else:
                p = key.split('|'); label = f"{p[0]} {p[1]}:{p[2]} - {title}" if len(p) >= 3 and title else f"{p[0]} {p[1]}:{p[2]}" if len(p) >= 3 else title or key
            item = QTreeWidgetItem(parent, [label]); item.setData(0, Qt.UserRole, "note"); item.setData(0, Qt.UserRole + 1, key)

        # 6. Bookmarks
        bookmarks_root = QTreeWidgetItem(self, ["Bookmarks"])
        for b in self.study_manager.data.get("bookmarks", []):
            item = QTreeWidgetItem(bookmarks_root, [f"{b['title']} ({b['ref']})" if b.get('title') else b['ref']])
            item.setData(0, Qt.UserRole, "bookmark"); item.setData(0, Qt.UserRole + 1, b)

        # 7. Restore expansion
        if not expanded_paths:
            for i in range(self.topLevelItemCount()): self.topLevelItem(i).setExpanded(True)
        else:
            def restore_state(item, path=""):
                current_path = f"{path}/{item.text(0)}" if path else item.text(0)
                item.setExpanded(current_path in expanded_paths)
                for i in range(item.childCount()): restore_state(item.child(i), current_path)
            for i in range(self.topLevelItemCount()): restore_state(self.topLevelItem(i))

    def _on_item_clicked(self, item, col):
        itype = item.data(0, Qt.UserRole)
        if itype == "outline":
            self.outlineOpenRequested.emit(item.data(0, Qt.UserRole + 1))
        elif itype == "mark":
            m = item.data(0, Qt.UserRole + 1); self.jumpRequested.emit(m['book'], str(m['chapter']), str(m['verse_num']))
        elif itype == "mark_group":
            m = item.data(0, Qt.UserRole + 2); self.jumpRequested.emit(m['book'], str(m['chapter']), str(m['verse_num']))
        elif itype == "bookmark":
            b = item.data(0, Qt.UserRole + 1); self.jumpRequested.emit(b['book'], b['chapter'], b['verse'])
        elif itype == "note":
            key = item.data(0, Qt.UserRole + 1)
            if key.startswith("standalone_"): self.noteOpenRequested.emit(key, "General Note")
            else:
                p = key.split('|')
                if len(p) >= 3: self.jumpRequested.emit(p[0], p[1], p[2]); self.noteOpenRequested.emit(key, f"{p[0]} {p[1]}:{p[2]}")
        elif itype in ["symbol", "arrow", "logical_mark"]:
            p = item.data(0, Qt.UserRole + 1).split('|')
            if len(p) >= 3: self.jumpRequested.emit(p[0], p[1], p[2])
        elif itype == "verse_mark":
            import re
            m = re.match(r"(.*) (\d+):(\d+)", item.data(0, Qt.UserRole + 1))
            if m: self.jumpRequested.emit(m.group(1), m.group(2), m.group(3))

    def _on_context_menu(self, pos):
        selected_items = self.selectedItems()
        if not selected_items: return
        menu = create_menu(self)
        if len(selected_items) > 1:
            symbol_items = []
            for item in selected_items:
                itype = item.data(0, Qt.UserRole)
                if itype == "symbol": symbol_items.append(item)
                elif itype == "symbol_type_group":
                    for i in range(item.childCount()): symbol_items.append(item.child(i))
            if symbol_items:
                act = QAction("Create Symbol List Note", self); act.triggered.connect(lambda: self._create_symbol_list_note(list(set(symbol_items)))); menu.addAction(act)
            del_act = QAction(f"Delete Selected ({len(selected_items)})", self); del_act.triggered.connect(self._delete_selected_items); menu.addAction(del_act)
            menu.exec(self.mapToGlobal(pos)); return
        item = selected_items[0]; itype = item.data(0, Qt.UserRole)
        if itype == "notes_header":
            add_n = QAction("New Standalone Note", self); add_n.triggered.connect(lambda: self._add_standalone_note()); menu.addAction(add_n)
            add_f = QAction("New Folder", self); add_f.triggered.connect(lambda: self._add_folder()); menu.addAction(add_f)
        elif itype == "note_folder":
            f_path = item.data(0, Qt.UserRole + 1)
            add_n = QAction("New Note in Folder", self); add_n.triggered.connect(lambda: self._add_standalone_note(f_path)); menu.addAction(add_n)
            add_f = QAction("New Sub-folder", self); add_f.triggered.connect(lambda: self._add_folder(f_path)); menu.addAction(add_f)
            menu.addSeparator(); del_f = QAction("Delete Folder", self); del_f.triggered.connect(lambda: self._delete_folder(f_path)); menu.addAction(del_f)
        elif itype == "mark":
            m_data = item.data(0, Qt.UserRole + 1); col_act = QAction("Change Color", self); col_act.triggered.connect(lambda: self._change_mark_color(m_data)); menu.addAction(col_act)
            del_act = QAction("Delete Mark", self); del_act.triggered.connect(lambda: self._delete_mark(m_data)); menu.addAction(del_act)
        elif itype == "mark_group":
            indices = item.data(0, Qt.UserRole + 1); col_act = QAction("Change Group Color", self); col_act.triggered.connect(lambda: self._change_group_color(indices)); menu.addAction(col_act)
            del_act = QAction("Delete Group", self); del_act.triggered.connect(lambda: self._delete_group(indices)); menu.addAction(del_act)
        elif itype == "symbol":
            key = item.data(0, Qt.UserRole + 1); del_act = QAction("Delete Symbol", self); del_act.triggered.connect(lambda: self._delete_symbol(key)); menu.addAction(del_act)
        elif itype == "note":
            key = item.data(0, Qt.UserRole + 1)
            if not key.startswith("standalone_"):
                p = key.split('|'); go_act = QAction("Go to Reference", self); go_act.triggered.connect(lambda: self.jumpRequested.emit(p[0], p[1], p[2])); menu.addAction(go_act)
            open_act = QAction("Open Note Editor", self); open_act.triggered.connect(lambda: self.noteOpenRequested.emit(key, "")); menu.addAction(open_act)
            move_m = create_menu(self, "Move to Folder"); root_act = QAction("(Notes Root)", self); root_act.triggered.connect(lambda: self.study_manager.move_note(key, "")); move_m.addAction(root_act)
            for f in sorted(self.study_manager.data.get("note_folders", [])):
                f_act = QAction(f, self); f_act.triggered.connect(lambda c=False, p=f: self.study_manager.move_note(key, p)); move_m.addAction(f_act)
            menu.addMenu(move_m); del_act = QAction("Delete Note", self); del_act.triggered.connect(lambda: self._delete_note(key)); menu.addAction(del_act)
        elif itype == "arrow":
            key = item.data(0, Qt.UserRole + 1); idx = item.data(0, Qt.UserRole + 2); del_act = QAction("Delete Arrow", self); del_act.triggered.connect(lambda: self._delete_arrow(key, idx)); menu.addAction(del_act)
        elif itype == "logical_mark":
            key = item.data(0, Qt.UserRole + 1); del_act = QAction("Delete Logical Mark", self); del_act.triggered.connect(lambda: self._delete_logical_mark(key)); menu.addAction(del_act)
        elif itype == "verse_mark":
            ref = item.data(0, Qt.UserRole + 1); del_act = QAction("Delete Verse Mark", self); del_act.triggered.connect(lambda: self.study_manager.set_verse_mark(ref, None)); menu.addAction(del_act)
        elif itype == "outline":
            node_id = item.data(0, Qt.UserRole + 1); del_act = QAction("Delete Outline", self); del_act.triggered.connect(lambda: self._delete_outline(node_id)); menu.addAction(del_act)
        if menu.actions(): menu.exec(self.mapToGlobal(pos))

    def _delete_selected_items(self):
        items = self.selectedItems()
        if not items: return
        if len(items) > 5 or any(i.data(0, Qt.UserRole) in ["note_folder", "symbol_type_group"] for i in items):
            if QMessageBox.question(self, "Confirm Bulk Deletion", f"Delete {len(items)} items?", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes: return
        self.study_manager.save_state(); to_del = {"marks": [], "symbols": [], "notes": [], "folders": [], "arrows": [], "bookmarks": [], "vmarks": [], "lmarks": [], "outlines": []}
        expanded = []
        for i in items:
            if i.data(0, Qt.UserRole) == "symbol_type_group":
                for j in range(i.childCount()): expanded.append(i.child(j))
            else: expanded.append(i)
        for i in expanded:
            t = i.data(0, Qt.UserRole); d1 = i.data(0, Qt.UserRole + 1)
            if t == "mark": to_del["marks"].append(d1)
            elif t == "mark_group":
                for idx in d1: 
                    if idx < len(self.study_manager.data["marks"]): to_del["marks"].append(self.study_manager.data["marks"][idx])
            elif t == "symbol": to_del["symbols"].append(d1)
            elif t == "note": to_del["notes"].append(d1)
            elif t == "note_folder": to_del["folders"].append(d1)
            elif t == "arrow": to_del["arrows"].append((d1, i.data(0, Qt.UserRole + 2)))
            elif t == "bookmark": to_del["bookmarks"].append(d1['ref'])
            elif t == "verse_mark": to_del["vmarks"].append(d1)
            elif t == "logical_mark": to_del["lmarks"].append(d1)
            elif t == "outline": to_del["outlines"].append(d1); self.outlineDeleted.emit(d1)
        m_ids = set(id(m) for m in to_del["marks"])
        self.study_manager.data["marks"] = [m for m in self.study_manager.data["marks"] if id(m) not in m_ids]
        for k in to_del["symbols"]: self.study_manager.data["symbols"].pop(k, None)
        for k in to_del["lmarks"]: self.study_manager.data.get("logical_marks", {}).pop(k, None)
        for nid in to_del["outlines"]: self.study_manager.outline_manager.delete_node(nid)
        for k in to_del["notes"]: self.study_manager.delete_note(k)
        for p in to_del["folders"]: self.study_manager.delete_folder(p)
        for k, idx in sorted(to_del["arrows"], key=lambda x: x[1], reverse=True):
            if k in self.study_manager.data["arrows"]:
                self.study_manager.data["arrows"][k].pop(idx)
                if not self.study_manager.data["arrows"][k]: del self.study_manager.data["arrows"][k]
        for r in to_del["bookmarks"]: self.study_manager.delete_bookmark(r)
        for r in to_del["vmarks"]: self.study_manager.set_verse_mark(r, None)
        self.study_manager.save_data(); self.dataChanged.emit(); self.refresh()

    def _delete_outline(self, node_id):
        if QMessageBox.question(self, "Delete Outline", "Are you sure?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.study_manager.outline_manager.delete_node(node_id); self.outlineDeleted.emit(node_id); self.dataChanged.emit(); self.refresh()
    def _add_standalone_note(self, folder=""):
        key = self.study_manager.add_standalone_note("", "", folder); self.refresh(); self.noteOpenRequested.emit(key, "General Note")
    def _add_folder(self, parent=""):
        name, ok = QInputDialog.getText(self, "New Folder", "Name:"); 
        if ok and name: self.study_manager.add_folder(f"{parent}/{name}" if parent else name); self.refresh()
    def _delete_folder(self, path):
        if QMessageBox.question(self, "Delete Folder", f"Delete {path} and all contents?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.study_manager.delete_folder(path); self.refresh()
    def _change_mark_color(self, m):
        c = QColorDialog.getColor(Qt.yellow, self, "Color"); 
        if c.isValid(): self.study_manager.save_state(); m["color"] = c.name(); self.study_manager.save_data(); self.refresh()
    def _delete_mark(self, m_data):
        self.study_manager.save_state(); self.study_manager.data["marks"] = [m for m in self.study_manager.data["marks"] if m is not m_data]; self.study_manager.save_data(); self.refresh()
    def _change_group_color(self, idxs):
        c = QColorDialog.getColor(Qt.yellow, self, "Color"); 
        if c.isValid():
            self.study_manager.save_state()
            for i in idxs: self.study_manager.data["marks"][i]["color"] = c.name()
            self.study_manager.save_data(); self.refresh()
    def _delete_group(self, idxs):
        self.study_manager.save_state(); 
        for i in sorted(idxs, reverse=True): self.study_manager.data["marks"].pop(i)
        self.study_manager.save_data(); self.refresh()
    def _delete_symbol(self, k): self.study_manager.save_state(); self.study_manager.data["symbols"].pop(k, None); self.study_manager.save_data(); self.refresh()
    def _delete_note(self, k): self.study_manager.delete_note(k); self.refresh()
    def _delete_arrow(self, k, i): 
        self.study_manager.save_state(); self.study_manager.data["arrows"][k].pop(i)
        if not self.study_manager.data["arrows"][k]: del self.study_manager.data["arrows"][k]
        self.study_manager.save_data(); self.refresh()
    def _delete_logical_mark(self, k): self.study_manager.save_state(); self.study_manager.data.get("logical_marks", {}).pop(k, None); self.study_manager.save_data(); self.refresh()
