from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem, 
    QLabel, QColorDialog, QInputDialog, QMessageBox, QStyle,
    QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QIcon, QCursor
import os
from src.utils.menu_utils import create_menu
from src.ui.components.outline_dialog import OutlineDialog

class StudyPanel(QWidget):
    jumpRequested = Signal(str, str, str) # book, chap, verse
    noteOpenRequested = Signal(str, str) # note_key, ref
    outlineOpenRequested = Signal(str) # node_id
    outlineDeleted = Signal(str) # node_id
    activeOutlineChanged = Signal(str) # Signal when entering/exiting outline mode
    dataChanged = Signal() # Signal to refresh view after edits

    def __init__(self, study_manager, symbol_manager, parent=None):
        super().__init__(parent)
        self.study_manager = study_manager
        self.symbol_manager = symbol_manager
        self.active_outline_id = None
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(15)
        self.tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        self.tree.setStyleSheet("""
            QTreeWidget {
                background-color: #222;
                border: 1px solid #444;
                color: #ccc;
            }
            QTreeWidget::item {
                padding: 4px;
            }
            QTreeWidget::item:hover {
                background-color: #333;
            }
            QTreeWidget::item:selected {
                background-color: #444;
                color: white;
            }
        """)
        layout.addWidget(self.tree)

        # --- Active Outline Status Bar ---
        self.status_bar = QFrame()
        self.status_bar.setStyleSheet("""
            QFrame {
                background-color: #005a9e;
                border-radius: 4px;
                margin-top: 5px;
            }
        """)
        self.status_layout = QHBoxLayout(self.status_bar)
        self.status_layout.setContentsMargins(8, 4, 8, 4)
        
        self.status_label = QLabel("Editing: Outline Name")
        self.status_label.setStyleSheet("color: white; font-weight: bold; font-size: 12px;")
        self.status_layout.addWidget(self.status_label)
        
        self.close_status_btn = QPushButton("✕")
        self.close_status_btn.setFixedSize(20, 20)
        self.close_status_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 40);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 80);
            }
        """)
        self.close_status_btn.clicked.connect(lambda: self.set_active_outline(None))
        self.status_layout.addWidget(self.close_status_btn)
        
        self.status_bar.hide()
        layout.addWidget(self.status_bar)
        
        # Enable Drag and Drop
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDragDropMode(QTreeWidget.InternalMove)
        self.tree.setDropIndicatorShown(True)
        self.tree.dropEvent = self._on_drop_event
        
        self.tree.itemDoubleClicked.connect(self._on_item_clicked)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_context_menu)
        
        # Bottom Action Menu
        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(0, 5, 0, 0)
        
        self.add_note_btn = QPushButton()
        self.add_note_btn.setIcon(self.style().standardIcon(QStyle.SP_FileIcon))
        self.add_note_btn.setToolTip("New Standalone Note")
        self.add_note_btn.clicked.connect(lambda: self._add_standalone_note(""))
        
        self.add_outline_btn = QPushButton()
        self.add_outline_btn.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        self.add_outline_btn.setToolTip("New Outline")
        self.add_outline_btn.clicked.connect(self._add_outline)
        
        btn_style = """
            QPushButton {
                background-color: #333;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #444;
                border-color: #555;
            }
            QPushButton:pressed {
                background-color: #222;
            }
        """
        self.add_note_btn.setStyleSheet(btn_style)
        self.add_outline_btn.setStyleSheet(btn_style)
        
        actions_layout.addWidget(self.add_note_btn)
        actions_layout.addWidget(self.add_outline_btn)
        layout.addLayout(actions_layout)
        
        # Ensure we refresh when our own dataChanged signal is emitted
        self.dataChanged.connect(self.refresh)
        
        self.refresh()

    def _add_outline(self):
        dialog = OutlineDialog(self, title="Book Outline")
        if dialog.exec():
            data = dialog.get_data()
            if data["title"]:
                node = self.study_manager.outline_manager.create_outline(
                    data["start_ref"], data["end_ref"], data["title"]
                )
                self.refresh()
                self.dataChanged.emit()
                self.set_active_outline(node["id"])
                self._open_outline_editor(node["id"])

    def _open_outline_editor(self, node_id):
        self.outlineOpenRequested.emit(node_id)

    def _on_drop_event(self, event):
        source_item = self.tree.currentItem()
        if not source_item:
            super(QTreeWidget, self.tree).dropEvent(event)
            return
            
        target_item = self.tree.itemAt(event.pos())
        if not target_item:
            event.ignore()
            return
            
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
        # 0. Capture expansion state
        expanded_paths = set()
        def save_state(item, path=""):
            current_path = f"{path}/{item.text(0)}" if path else item.text(0)
            if item.isExpanded(): expanded_paths.add(current_path)
            for i in range(item.childCount()): save_state(item.child(i), current_path)
        for i in range(self.tree.topLevelItemCount()): save_state(self.tree.topLevelItem(i))

        self.tree.clear()

        # 1. Outlines
        outlines_root = QTreeWidgetItem(self.tree, ["Outlines"])
        outlines = self.study_manager.outline_manager.get_outlines()
        for outline in outlines:
            item = QTreeWidgetItem(outlines_root, [outline["title"]])
            item.setData(0, Qt.UserRole, "outline")
            item.setData(0, Qt.UserRole + 1, outline["id"])

        # 1. Marks
        marks_root = QTreeWidgetItem(self.tree, ["Marks"])
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
                vm_type_nodes[m_type] = QTreeWidgetItem(vm_parent, [vm_types.get(m_type, m_type.title())])
                vm_type_nodes[m_type].setExpanded(True)
            item = QTreeWidgetItem(vm_type_nodes[m_type], [ref])
            item.setData(0, Qt.UserRole, "verse_mark"); item.setData(0, Qt.UserRole + 1, ref)

        for cat in list(mark_categories.values()):
            if cat.childCount() == 0: marks_root.removeChild(cat)

        # 2. Logical Marks
        logical_root = QTreeWidgetItem(self.tree, ["Logical Marks"])
        logical_marks_data = self.study_manager.data.get("logical_marks", {})
        if logical_marks_data:
            # Group by type
            type_groups = {}
            for key, m_type in logical_marks_data.items():
                if m_type not in type_groups: type_groups[m_type] = []
                type_groups[m_type].append(key)
            
            for m_type, keys in type_groups.items():
                # Get pretty name from constants if possible, or format type
                pretty_name = m_type.replace("_", " ").title()
                group_item = QTreeWidgetItem(logical_root, [pretty_name])
                
                def sort_key(k):
                    p = k.split('|')
                    if len(p) < 4: return (p[0], 0, 0, 0)
                    return (p[0], int(p[1]), int(p[2]), int(p[3]))

                for key in sorted(keys, key=sort_key):
                    parts = key.split('|')
                    if len(parts) >= 3:
                        ref = f"{parts[0]} {parts[1]}:{parts[2]}"
                        item = QTreeWidgetItem(group_item, [ref])
                        item.setData(0, Qt.UserRole, "logical_mark")
                        item.setData(0, Qt.UserRole + 1, key)

        if logical_root.childCount() == 0:
            # Remove if empty? The prompt says "should be another subgroup". 
            # If no marks, maybe don't show root.
            # self.tree.invisibleRootItem().removeChild(logical_root) # Can't remove directly easily without index
             pass # TreeWidget handles empty roots fine, but usually we hide empty sections.
             # Actually, let's hide it if empty to keep UI clean
             # But first let's see if we added it to the tree. Yes.
        if logical_root.childCount() == 0:
            index = self.tree.indexOfTopLevelItem(logical_root)
            if index != -1: self.tree.takeTopLevelItem(index)

        # 3. Symbols
        symbols_root = QTreeWidgetItem(self.tree, ["Symbols"])
        symbol_groups = {}
        for key, s_file in self.study_manager.data.get("symbols", {}).items():
            name = self.symbol_manager.get_symbol_name(s_file)
            if name not in symbol_groups: symbol_groups[name] = []
            symbol_groups[name].append((key, s_file))
        for name in sorted(symbol_groups.keys()):
            group_item = QTreeWidgetItem(symbols_root, [name])
            group_item.setData(0, Qt.UserRole, "symbol_type_group")
            def sort_key(x):
                p = x[0].split('|')
                if len(p) < 4: return (p[0], 0, 0, 0)
                return (p[0], int(p[1]), int(p[2]), int(p[3]))
            for key, s_file in sorted(symbol_groups[name], key=sort_key):
                p = key.split('|')
                label = f"{p[0]} {p[1]}:{p[2]}" if len(p) >= 3 else key
                item = QTreeWidgetItem(group_item, [label])
                item.setData(0, Qt.UserRole, "symbol"); item.setData(0, Qt.UserRole + 1, key); item.setData(0, Qt.UserRole + 2, s_file)

        # 3. Notes
        notes_root = QTreeWidgetItem(self.tree, ["Notes"])
        notes_root.setData(0, Qt.UserRole, "notes_header")
        folder_items = {"": notes_root}
        for f_path in sorted(self.study_manager.data.get("note_folders", [])):
            parts = f_path.split("/")
            curr = ""
            for part in parts:
                prev = curr; curr = f"{curr}/{part}" if curr else part
                if curr not in folder_items:
                    item = QTreeWidgetItem(folder_items[prev], [part])
                    item.setIcon(0, self.style().standardIcon(QStyle.SP_DirIcon))
                    item.setData(0, Qt.UserRole, "note_folder"); item.setData(0, Qt.UserRole + 1, curr)
                    folder_items[curr] = item

        for key, data in self.study_manager.data.get("notes", {}).items():
            folder = data.get("folder", "") if isinstance(data, dict) else ""
            parent = folder_items.get(folder, notes_root)
            title = data.get("title", "") if isinstance(data, dict) else data
            if key.startswith("standalone_"): label = title if title else "Untitled Note"
            else:
                p = key.split('|')
                if len(p) >= 3:
                    ref = f"{p[0]} {p[1]}:{p[2]}"
                    label = title if ref in title else f"{ref} - {title}" if title else ref
                else: label = title if title else key
            item = QTreeWidgetItem(parent, [label])
            item.setData(0, Qt.UserRole, "note"); item.setData(0, Qt.UserRole + 1, key)

        # 4. Bookmarks
        bookmarks_root = QTreeWidgetItem(self.tree, ["Bookmarks"])
        for b in self.study_manager.data.get("bookmarks", []):
            label = f"{b['title']} ({b['ref']})" if b.get('title') else b['ref']
            item = QTreeWidgetItem(bookmarks_root, [label])
            item.setData(0, Qt.UserRole, "bookmark"); item.setData(0, Qt.UserRole + 1, b)

        # 5. Restore expansion
        if not expanded_paths:
            for i in range(self.tree.topLevelItemCount()): self.tree.topLevelItem(i).setExpanded(True)
        else:
            def restore_state(item, path=""):
                current_path = f"{path}/{item.text(0)}" if path else item.text(0)
                item.setExpanded(current_path in expanded_paths)
                for i in range(item.childCount()): restore_state(item.child(i), current_path)
            for i in range(self.tree.topLevelItemCount()): restore_state(self.tree.topLevelItem(i))

    def set_active_outline(self, outline_id):
        self.active_outline_id = outline_id
        if outline_id:
            node = self.study_manager.outline_manager.get_node(outline_id)
            title = node["title"] if node else "Unknown"
            self.status_label.setText(f"Editing: {title}")
            self.status_bar.show()
        else:
            self.status_bar.hide()
        self.activeOutlineChanged.emit(outline_id)

    def _on_item_clicked(self, item, col):
        itype = item.data(0, Qt.UserRole)
        if itype == "outline":
            node_id = item.data(0, Qt.UserRole + 1)
            self.set_active_outline(node_id)
            self._open_outline_editor(node_id)
        elif itype == "mark":
            m = item.data(0, Qt.UserRole + 1)
            self.jumpRequested.emit(m['book'], str(m['chapter']), str(m['verse_num']))
        elif itype == "mark_group":
            m = item.data(0, Qt.UserRole + 2)
            self.jumpRequested.emit(m['book'], str(m['chapter']), str(m['verse_num']))
        elif itype == "bookmark":
            b = item.data(0, Qt.UserRole + 1)
            self.jumpRequested.emit(b['book'], b['chapter'], b['verse'])
        elif itype == "note":
            key = item.data(0, Qt.UserRole + 1)
            if key.startswith("standalone_"): self._open_note(key)
            else:
                parts = key.split('|')
                if len(parts) >= 3:
                    ref = f"{parts[0]} {parts[1]}:{parts[2]}"
                    self.jumpRequested.emit(parts[0], parts[1], parts[2])
                    self.noteOpenRequested.emit(key, ref)
        elif itype in ["symbol", "arrow", "logical_mark"]:
            key = item.data(0, Qt.UserRole + 1)
            parts = key.split('|')
            if len(parts) >= 3: self.jumpRequested.emit(parts[0], parts[1], parts[2])
        elif itype == "verse_mark":
            ref = item.data(0, Qt.UserRole + 1)
            import re
            match = re.match(r"(.*) (\d+):(\d+)", ref)
            if match:
                book, chap, verse = match.groups()
                self.jumpRequested.emit(book, chap, verse)

    def _create_symbol_list_note(self, symbol_items):
        if not symbol_items: return
        names = set(); refs = []
        for item in symbol_items:
            key = item.data(0, Qt.UserRole + 1); s_file = item.data(0, Qt.UserRole + 2)
            names.add(self.symbol_manager.get_symbol_name(s_file))
            parts = key.split('|')
            if len(parts) >= 4:
                refs.append({"book": parts[0], "chapter": int(parts[1]), "verse": int(parts[2]), "word_idx": int(parts[3]), "ref_str": f"{parts[0]} {parts[1]}:{parts[2]}"})
        if not refs: return
        sorted_refs = sorted(refs, key=lambda r: (r['book'], r['chapter'], r['verse'], r['word_idx']))
        if len(sorted_refs) == 1: range_str = sorted_refs[0]['ref_str']
        else:
            first = sorted_refs[0]; last = sorted_refs[-1]
            if first['book'] == last['book'] and first['chapter'] == last['chapter']:
                range_str = first['ref_str'] if first['verse'] == last['verse'] else f"{first['book']} {first['chapter']}:{first['verse']}-{last['verse']}"
            else: range_str = f"{first['ref_str']} - {last['ref_str']}"
        title = f"{list(names)[0]} - {range_str}" if len(names) == 1 else f"Symbol List - {range_str}"
        content = "## Symbol List\n"
        for r in sorted_refs: content += f"- {r['ref_str']} - \n"
        first = sorted_refs[0]; note_key = f"{first['book']}|{first['chapter']}|{first['verse']}|{first['word_idx']}"
        self.study_manager.add_note(first['book'], str(first['chapter']), str(first['verse']), first['word_idx'], content, title)
        self.refresh(); self._open_note(note_key)

    def _on_context_menu(self, pos):
        selected_items = self.tree.selectedItems()
        if not selected_items: return
        menu = create_menu(self)
        if len(selected_items) > 1:
            symbol_items = []
            for item in selected_items:
                itype = item.data(0, Qt.UserRole)
                if itype == "symbol": symbol_items.append(item)
                elif itype == "symbol_type_group":
                    for i in range(item.childCount()): symbol_items.append(item.child(i))
            if symbol_items and len(selected_items) > 1:
                unique_symbol_items = list(set(symbol_items))
                list_note_act = QAction("Create Symbol List Note", self)
                list_note_act.triggered.connect(lambda: self._create_symbol_list_note(unique_symbol_items))
                menu.addAction(list_note_act)
            del_act = QAction(f"Delete Selected ({len(selected_items)})", self)
            del_act.triggered.connect(self._delete_selected_items); menu.addAction(del_act)
            menu.exec(self.tree.mapToGlobal(pos)); return
        item = selected_items[0]; itype = item.data(0, Qt.UserRole)
        if itype == "notes_header":
            add_note_act = QAction("New Standalone Note", self); add_note_act.triggered.connect(self._add_standalone_note); menu.addAction(add_note_act)
            add_folder_act = QAction("New Folder", self); add_folder_act.triggered.connect(lambda: self._add_folder("")); menu.addAction(add_folder_act)
        elif itype == "note_folder":
            f_path = item.data(0, Qt.UserRole + 1)
            add_note_act = QAction("New Note in Folder", self); add_note_act.triggered.connect(lambda: self._add_standalone_note(f_path)); menu.addAction(add_note_act)
            add_sub_act = QAction("New Sub-folder", self); add_sub_act.triggered.connect(lambda: self._add_folder(f_path)); menu.addAction(add_sub_act)
            menu.addSeparator(); del_folder_act = QAction("Delete Folder", self); del_folder_act.triggered.connect(lambda: self._delete_folder(f_path)); menu.addAction(del_folder_act)
        elif itype == "mark":
            mark_data = item.data(0, Qt.UserRole + 1)
            color_act = QAction("Change Color", self); color_act.triggered.connect(lambda: self._change_mark_color_by_data(mark_data)); menu.addAction(color_act)
            del_act = QAction("Delete Mark", self); del_act.triggered.connect(lambda: self._delete_mark(mark_data)); menu.addAction(del_act)
        elif itype == "mark_group":
            indices = item.data(0, Qt.UserRole + 1)
            color_act = QAction("Change Group Color", self); color_act.triggered.connect(lambda: self._change_group_color(indices)); menu.addAction(color_act)
            del_act = QAction("Delete Group", self); del_act.triggered.connect(lambda: self._delete_group(indices)); menu.addAction(del_act)
        elif itype == "symbol":
            key = item.data(0, Qt.UserRole + 1); del_act = QAction("Delete Symbol", self); del_act.triggered.connect(lambda: self._delete_symbol(key)); menu.addAction(del_act)
        elif itype == "note":
            key = item.data(0, Qt.UserRole + 1)
            if not key.startswith("standalone_"):
                parts = key.split('|')
                if len(parts) >= 3:
                    go_act = QAction("Go to Reference", self); go_act.triggered.connect(lambda: self.jumpRequested.emit(parts[0], parts[1], parts[2])); menu.addAction(go_act)
            open_act = QAction("Open Note Editor", self); open_act.triggered.connect(lambda: self._open_note(key)); menu.addAction(open_act)
            move_menu = create_menu(self, "Move to Folder")
            root_act = QAction("(Notes Root)", self); root_act.triggered.connect(lambda: self._move_note(key, "")); move_menu.addAction(root_act)
            for f_path in sorted(self.study_manager.data.get("note_folders", [])):
                f_act = QAction(f_path, self); f_act.triggered.connect(lambda checked=False, p=f_path: self._move_note(key, p)); move_menu.addAction(f_act)
            menu.addMenu(move_menu)
            del_act = QAction("Delete Note", self); del_act.triggered.connect(lambda: self._delete_note(key)); menu.addAction(del_act)
        elif itype == "arrow":
            key = item.data(0, Qt.UserRole + 1); idx = item.data(0, Qt.UserRole + 2); del_act = QAction("Delete Arrow", self); del_act.triggered.connect(lambda: self._delete_arrow(key, idx)); menu.addAction(del_act)
        elif itype == "logical_mark":
            key = item.data(0, Qt.UserRole + 1); del_act = QAction("Delete Logical Mark", self); del_act.triggered.connect(lambda: self._delete_logical_mark(key)); menu.addAction(del_act)
        elif itype == "verse_mark":
            ref = item.data(0, Qt.UserRole + 1); del_act = QAction("Delete Verse Mark", self); del_act.triggered.connect(lambda: self._delete_verse_mark(ref)); menu.addAction(del_act)
        elif itype == "outline":
            node_id = item.data(0, Qt.UserRole + 1)
            del_act = QAction("Delete Outline", self); del_act.triggered.connect(lambda: self._delete_outline(node_id)); menu.addAction(del_act)
        if menu.actions(): menu.exec(self.tree.mapToGlobal(pos))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete: self._delete_selected_items()
        else: super().keyPressEvent(event)

    def _change_mark_color(self, idx):
        color = QColorDialog.getColor(Qt.yellow, self, "Select Mark Color")
        if color.isValid():
            self.study_manager.save_state(); self.study_manager.data["marks"][idx]["color"] = color.name(); self.study_manager.save_study(); self.dataChanged.emit(); self.refresh()

    def _change_mark_color_by_data(self, mark_data):
        color = QColorDialog.getColor(Qt.yellow, self, "Select Mark Color")
        if color.isValid():
            self.study_manager.save_state()
            mark_data["color"] = color.name()
            self.study_manager.save_study(); self.dataChanged.emit(); self.refresh()

    def _delete_mark(self, mark_data):
        """Delete a single mark by object identity, not by index (index may be stale)."""
        self.study_manager.save_state()
        marks = self.study_manager.data["marks"]
        for i, m in enumerate(marks):
            if m is mark_data:
                marks.pop(i)
                break
        self.study_manager.save_study(); self.dataChanged.emit(); self.refresh()

    def _change_group_color(self, indices):
        color = QColorDialog.getColor(Qt.yellow, self, "Select Group Color")
        if color.isValid():
            self.study_manager.save_state()
            for idx in indices: self.study_manager.data["marks"][idx]["color"] = color.name()
            self.study_manager.save_study(); self.dataChanged.emit(); self.refresh()

    def _delete_group(self, indices):
        self.study_manager.save_state()
        for idx in sorted(indices, reverse=True): self.study_manager.data["marks"].pop(idx)
        self.study_manager.save_study(); self.dataChanged.emit(); self.refresh()

    def _delete_symbol(self, key):
        self.study_manager.save_state()
        if key in self.study_manager.data["symbols"]: del self.study_manager.data["symbols"][key]; self.study_manager.save_study(); self.dataChanged.emit(); self.refresh()

    def _add_standalone_note(self, folder=""):
        key = self.study_manager.add_standalone_note(title="", text="", folder=folder); self.refresh(); self._open_note(key)

    def _add_folder(self, parent_path=""):
        name, ok = QInputDialog.getText(self, "New Folder", "Enter folder name:")
        if ok and name:
            full_path = f"{parent_path}/{name}" if parent_path else name
            self.study_manager.add_folder(full_path); self.refresh()

    def _move_note(self, note_key, folder_path): self.study_manager.move_note(note_key, folder_path); self.refresh()

    def _delete_folder(self, folder_path):
        has_content = any(n.get("folder", "") == folder_path or n.get("folder", "").startswith(f"{folder_path}/") for n in self.study_manager.data["notes"].values())
        if not has_content: has_content = any(f.startswith(f"{folder_path}/") for f in self.study_manager.data["note_folders"])
        if has_content:
            res = QMessageBox.question(self, "Delete Folder", f"The folder '{folder_path}' and its sub-folders contain notes.\nAre you sure you want to delete them?", QMessageBox.Yes | QMessageBox.No)
            if res != QMessageBox.Yes: return
        self.study_manager.delete_folder(folder_path); self.refresh()

    def _delete_note(self, key): self.study_manager.delete_note(key); self.dataChanged.emit(); self.refresh()

    def _delete_arrow(self, key, idx):
        self.study_manager.save_state()
        if key in self.study_manager.data["arrows"]:
            self.study_manager.data["arrows"][key].pop(idx)
            if not self.study_manager.data["arrows"][key]: del self.study_manager.data["arrows"][key]
            self.study_manager.save_study(); self.dataChanged.emit(); self.refresh()

    def _delete_bookmark(self, ref): self.study_manager.delete_bookmark(ref); self.dataChanged.emit(); self.refresh()

    def _delete_logical_mark(self, key):
        self.study_manager.save_state()
        if "logical_marks" in self.study_manager.data and key in self.study_manager.data["logical_marks"]:
            del self.study_manager.data["logical_marks"][key]
            self.study_manager.save_study()
            self.dataChanged.emit()
            self.refresh()

    def set_active_outline(self, outline_id, emit_signal=True):
        self.active_outline_id = outline_id
        if outline_id:
            node = self.study_manager.outline_manager.get_node(outline_id)
            title = node.get("title", "Unknown") if node else "Unknown"
            self.status_label.setText(f"Editing: {title}")
            self.status_bar.show()
        else:
            self.status_bar.hide()
            
        if emit_signal:
            self.activeOutlineChanged.emit(outline_id or "")

    def _delete_outline(self, node_id):
        res = QMessageBox.question(self, "Delete Outline", "Are you sure you want to delete this outline?", QMessageBox.Yes | QMessageBox.No)
        if res == QMessageBox.Yes:
            if self.active_outline_id == node_id:
                self.set_active_outline(None)
            self.study_manager.outline_manager.delete_node(node_id)
            self.outlineDeleted.emit(node_id)
            self.refresh()
            self.dataChanged.emit()

    def _open_note(self, key):
        if key.startswith("standalone_"): self.noteOpenRequested.emit(key, "General Note")
        else:
            p = key.split('|')
            if len(p) >= 3:
                ref = f"{p[0]} {p[1]}:{p[2]}"; self.jumpRequested.emit(p[0], p[1], p[2]); self.noteOpenRequested.emit(key, ref)

    def _delete_selected_items(self):
        selected_items = self.tree.selectedItems()
        if not selected_items: return
        if len(selected_items) > 5 or any(i.data(0, Qt.UserRole) in ["note_folder", "symbol_type_group"] for i in selected_items):
            res = QMessageBox.question(self, "Confirm Bulk Deletion", f"Are you sure you want to delete {len(selected_items)} selected items?", QMessageBox.Yes | QMessageBox.No)
            if res != QMessageBox.Yes: return
        self.study_manager.save_state()
        to_del = {"marks": [], "symbols": [], "notes": [], "note_folders": [], "arrows": [], "bookmarks": [], "verse_marks": [], "logical_marks": [], "outlines": []}
        expanded_selected = []
        for item in selected_items:
            if item.data(0, Qt.UserRole) == "symbol_type_group":
                for i in range(item.childCount()): expanded_selected.append(item.child(i))
            else: expanded_selected.append(item)
        for item in expanded_selected:
            itype = item.data(0, Qt.UserRole)
            if itype == "mark": to_del["marks"].append(item.data(0, Qt.UserRole + 1))
            elif itype == "mark_group":
                all_marks = self.study_manager.data["marks"]
                for idx in item.data(0, Qt.UserRole + 1):
                    if idx < len(all_marks): to_del["marks"].append(all_marks[idx])
            elif itype == "symbol": to_del["symbols"].append(item.data(0, Qt.UserRole + 1))
            elif itype == "note": to_del["notes"].append(item.data(0, Qt.UserRole + 1))
            elif itype == "note_folder": to_del["note_folders"].append(item.data(0, Qt.UserRole + 1))
            elif itype == "arrow": to_del["arrows"].append((item.data(0, Qt.UserRole + 1), item.data(0, Qt.UserRole + 2)))
            elif itype == "bookmark": to_del["bookmarks"].append(item.data(0, Qt.UserRole + 1)['ref'])
            elif itype == "verse_mark": to_del["verse_marks"].append(item.data(0, Qt.UserRole + 1))
            elif itype == "logical_mark": to_del["logical_marks"].append(item.data(0, Qt.UserRole + 1))
            elif itype == "outline":
                node_id = item.data(0, Qt.UserRole + 1)
                to_del["outlines"].append(node_id)
                self.outlineDeleted.emit(node_id) # Added emit line
        if any(v for v in to_del.values()): # Changed condition from `if to_del["marks"]:`
            marks_to_remove = set(id(m) for m in to_del["marks"])
            self.study_manager.data["marks"] = [m for m in self.study_manager.data["marks"] if id(m) not in marks_to_remove]
        for key in to_del["symbols"]:
            if key in self.study_manager.data["symbols"]: del self.study_manager.data["symbols"][key]
        for key in to_del["logical_marks"]:
            if "logical_marks" in self.study_manager.data and key in self.study_manager.data["logical_marks"]:
                del self.study_manager.data["logical_marks"][key]
        for node_id in to_del["outlines"]:
            if self.active_outline_id == node_id:
                self.set_active_outline(None)
            self.study_manager.outline_manager.delete_node(node_id)
        for key in to_del["notes"]: self.study_manager.delete_note(key)
        for path in to_del["note_folders"]: self.study_manager.delete_folder(path)
        arrow_map = {}
        for key, idx in to_del["arrows"]:
            if key not in arrow_map: arrow_map[key] = []
            arrow_map[key].append(idx)
        for key, indices in arrow_map.items():
            if key in self.study_manager.data["arrows"]:
                for idx in sorted(list(set(indices)), reverse=True): self.study_manager.data["arrows"][key].pop(idx)
                if not self.study_manager.data["arrows"][key]: del self.study_manager.data["arrows"][key]
        for ref in to_del["bookmarks"]: self.study_manager.delete_bookmark(ref)
        for ref in to_del["verse_marks"]: self.study_manager.set_verse_mark(ref, None)
        self.study_manager.save_study(); self.dataChanged.emit(); self.refresh()
