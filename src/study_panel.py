from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, 
    QLabel, QMenu, QColorDialog, QInputDialog, QMessageBox, QStyle
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QIcon
import os

class StudyPanel(QWidget):
    jumpRequested = Signal(str, str, str) # book, chap, verse
    noteOpenRequested = Signal(str, str) # note_key, ref
    dataChanged = Signal() # Signal to refresh view after edits

    def __init__(self, study_manager, symbol_manager, parent=None):
        super().__init__(parent)
        self.study_manager = study_manager
        self.symbol_manager = symbol_manager
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        title = QLabel("STUDY OVERVIEW")
        title.setStyleSheet("font-weight: bold; color: #aaa; margin-bottom: 5px;")
        layout.addWidget(title)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(15)
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
        """)
        layout.addWidget(self.tree)
        
        # Enable Drag and Drop
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDragDropMode(QTreeWidget.InternalMove)
        self.tree.setDropIndicatorShown(True)
        # We'll override the dropEvent to handle our custom logic
        self.tree.dropEvent = self._on_drop_event
        
        self.tree.itemDoubleClicked.connect(self._on_item_clicked)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_context_menu)
        
        self.refresh()

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
        
        # 1. Moving a Note
        if source_type == "note":
            note_key = source_item.data(0, Qt.UserRole + 1)
            
            if target_type == "note_folder":
                # Drop on a folder
                new_folder = target_item.data(0, Qt.UserRole + 1)
                self.study_manager.move_note(note_key, new_folder)
                self.refresh()
                event.accept()
            elif target_type == "notes_header":
                # Drop on the main header (root)
                self.study_manager.move_note(note_key, "")
                self.refresh()
                event.accept()
            else:
                event.ignore()
        
        # 2. Moving a Folder
        elif source_type == "note_folder":
            source_path = source_item.data(0, Qt.UserRole + 1)
            
            if target_type == "notes_header":
                # Move folder to root
                self.study_manager.move_folder(source_path, "")
                self.refresh()
                event.accept()
            elif target_type == "note_folder":
                # Move into another folder
                target_path = target_item.data(0, Qt.UserRole + 1)
                # Ensure we are not dropping into ourself
                if source_path != target_path and not target_path.startswith(f"{source_path}/"):
                    self.study_manager.move_folder(source_path, target_path)
                    self.refresh()
                    event.accept()
                else:
                    event.ignore()
            else:
                event.ignore()
        else:
            event.ignore()

    def _get_range_string(self, group_marks):
        if not group_marks: return ""
        m0 = group_marks[0]
        if len(group_marks) == 1:
            return f"{m0['book']} {m0['chapter']}:{m0['verse_num']}"
        
        # Sort by verse number to get start and end
        sorted_marks = sorted(group_marks, key=lambda x: int(x['verse_num']))
        start = sorted_marks[0]
        end = sorted_marks[-1]
        
        if start['book'] == end['book'] and start['chapter'] == end['chapter']:
            return f"{start['book']} {start['chapter']}:{start['verse_num']}-{end['verse_num']}"
        else:
            return f"{start['book']} {start['chapter']}:{start['verse_num']} - {end['book']} {end['chapter']}:{end['verse_num']}"

    def refresh(self):
        self.tree.clear()
        
        # 1. Marks
        marks_root = QTreeWidgetItem(self.tree, ["Marks"])
        marks_root.setExpanded(True)
        
        # Group marks by group_id
        grouped_marks = {} # {group_id: [indices]}
        ungrouped_indices = []
        
        all_marks = self.study_manager.data.get("marks", [])
        for i, m in enumerate(all_marks):
            gid = m.get("group_id")
            if gid:
                if gid not in grouped_marks:
                    grouped_marks[gid] = []
                grouped_marks[gid].append(i)
            else:
                ungrouped_indices.append(i)
        
        # Add grouped marks
        for gid, indices in grouped_marks.items():
            group_data = [all_marks[i] for i in indices]
            range_str = self._get_range_string(group_data)
            mark_type = group_data[0]['type'].title()
            
            item = QTreeWidgetItem(marks_root, [f"{range_str} ({mark_type})"])
            item.setData(0, Qt.UserRole, "mark_group")
            item.setData(0, Qt.UserRole + 1, indices)
            item.setData(0, Qt.UserRole + 2, group_data[0]) # Use first mark for jump reference
            
        # Add ungrouped marks
        for i in ungrouped_indices:
            m = all_marks[i]
            ref = f"{m['book']} {m['chapter']}:{m['verse_num']}"
            item = QTreeWidgetItem(marks_root, [f"{ref} ({m['type'].title()})"])
            item.setData(0, Qt.UserRole, "mark")
            item.setData(0, Qt.UserRole + 1, m)
            item.setData(0, Qt.UserRole + 2, i) # index
            
        # 2. Symbols
        symbols_root = QTreeWidgetItem(self.tree, ["Symbols"])
        symbols_root.setExpanded(True)
        
        symbol_groups = {} # {type_name: [(key, s_name)]}
        for key, s_name in self.study_manager.data.get("symbols", {}).items():
            clean_name = os.path.splitext(s_name)[0]
            parts = clean_name.replace('_', '-').split('-')
            type_name = parts[0].title() if len(parts) > 1 else "General"
            
            if type_name not in symbol_groups:
                symbol_groups[type_name] = []
            symbol_groups[type_name].append((key, s_name, clean_name))

        for type_name in sorted(symbol_groups.keys()):
            type_root = QTreeWidgetItem(symbols_root, [type_name])
            for key, s_name, clean_name in sorted(symbol_groups[type_name], key=lambda x: x[2]):
                parts = key.split('|')
                ref = f"{parts[0]} {parts[1]}:{parts[2]}"
                
                # Further refine display name (strip group prefix if it exists)
                display_name = clean_name
                d_parts = display_name.replace('_', '-').split('-')
                if len(d_parts) > 1:
                    display_name = " ".join(d_parts[1:])
                
                item = QTreeWidgetItem(type_root, [f"{ref} ({display_name})"])
                item.setData(0, Qt.UserRole, "symbol")
                item.setData(0, Qt.UserRole + 1, key)
                item.setData(0, Qt.UserRole + 2, s_name)
            
        # 3. Notes
        notes_root = QTreeWidgetItem(self.tree, ["Notes"])
        notes_root.setData(0, Qt.UserRole, "notes_header")
        notes_root.setExpanded(True)
        
        # Build folder structure
        folder_items = {"": notes_root} # path: QTreeWidgetItem
        
        # First add all defined folders
        for f_path in sorted(self.study_manager.data.get("note_folders", [])):
            parts = f_path.split("/")
            current_path = ""
            for i, part in enumerate(parts):
                parent_path = current_path
                current_path = "/".join(parts[:i+1])
                if current_path not in folder_items:
                    parent_item = folder_items[parent_path]
                    item = QTreeWidgetItem(parent_item, [part])
                    # Add Folder Icon indication
                    item.setIcon(0, self.style().standardIcon(QStyle.SP_DirIcon))
                    item.setData(0, Qt.UserRole, "note_folder")
                    item.setData(0, Qt.UserRole + 1, current_path)
                    folder_items[current_path] = item

        # Then add notes to their respective folders
        for key, note_data in self.study_manager.data.get("notes", {}).items():
            folder_path = ""
            if isinstance(note_data, dict):
                folder_path = note_data.get("folder", "")
            
            parent_item = folder_items.get(folder_path, notes_root)
            
            title = ""
            if isinstance(note_data, dict):
                title = note_data.get("title", "")
            
            if key.startswith("standalone_"):
                # Standalone: Just show title
                label = title if title else "Untitled Note"
            else:
                # Attached: Show Ref - Title or just Ref
                parts = key.split('|')
                ref = f"{parts[0]} {parts[1]}:{parts[2]}"
                label = f"{ref} - {title}" if title else ref
            
            item = QTreeWidgetItem(parent_item, [label])
            item.setData(0, Qt.UserRole, "note")
            item.setData(0, Qt.UserRole + 1, key)
            
        # 4. Arrows
        arrows_root = QTreeWidgetItem(self.tree, ["Arrows"])
        arrows_root.setExpanded(True)
        verse_arrow_counts = {} # {ref: count}
        # Sort keys to ensure consistent numbering
        sorted_keys = sorted(self.study_manager.data.get("arrows", {}).keys())
        for key in sorted_keys:
            arrow_list = self.study_manager.data["arrows"][key]
            parts = key.split('|')
            ref = f"{parts[0]} {parts[1]}:{parts[2]}"
            
            # Initialize or get count for this ref
            if ref not in verse_arrow_counts:
                verse_arrow_counts[ref] = 0
                
            for i, a in enumerate(arrow_list):
                verse_arrow_counts[ref] += 1
                item = QTreeWidgetItem(arrows_root, [f"{ref} Arrow {verse_arrow_counts[ref]}"])
                item.setData(0, Qt.UserRole, "arrow")
                item.setData(0, Qt.UserRole + 1, key)
                item.setData(0, Qt.UserRole + 2, i)

        # 5. Bookmarks
        bookmarks_root = QTreeWidgetItem(self.tree, ["Bookmarks"])
        bookmarks_root.setExpanded(True)
        for b in self.study_manager.data.get("bookmarks", []):
            label = f"{b['title']} ({b['ref']})" if b.get('title') else b['ref']
            item = QTreeWidgetItem(bookmarks_root, [label])
            item.setData(0, Qt.UserRole, "bookmark")
            item.setData(0, Qt.UserRole + 1, b)

    def _on_item_clicked(self, item, col):
        itype = item.data(0, Qt.UserRole)
        if itype == "mark":
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
            if key.startswith("standalone_"):
                self._open_note(key)
            else:
                parts = key.split('|')
                ref = f"{parts[0]} {parts[1]}:{parts[2]}"
                self.jumpRequested.emit(parts[0], parts[1], parts[2])
                self.noteOpenRequested.emit(key, ref)
        elif itype in ["symbol", "arrow"]:
            key = item.data(0, Qt.UserRole + 1)
            parts = key.split('|')
            self.jumpRequested.emit(parts[0], parts[1], parts[2])

    def _on_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not item: return
        
        itype = item.data(0, Qt.UserRole)
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #333; color: white; } QMenu::item:selected { background-color: #555; }")
        
        if itype == "notes_header":
            add_note_act = QAction("New Standalone Note", self)
            add_note_act.triggered.connect(self._add_standalone_note)
            menu.addAction(add_note_act)
            
            add_folder_act = QAction("New Folder", self)
            add_folder_act.triggered.connect(lambda: self._add_folder(""))
            menu.addAction(add_folder_act)

        elif itype == "note_folder":
            f_path = item.data(0, Qt.UserRole + 1)
            
            add_note_act = QAction("New Note in Folder", self)
            add_note_act.triggered.connect(lambda: self._add_standalone_note(f_path))
            menu.addAction(add_note_act)
            
            add_sub_act = QAction("New Sub-folder", self)
            add_sub_act.triggered.connect(lambda: self._add_folder(f_path))
            menu.addAction(add_sub_act)
            
            menu.addSeparator()
            del_folder_act = QAction("Delete Folder", self)
            del_folder_act.triggered.connect(lambda: self._delete_folder(f_path))
            menu.addAction(del_folder_act)

        elif itype == "mark":
            idx = item.data(0, Qt.UserRole + 2)
            color_act = QAction("Change Color", self)
            color_act.triggered.connect(lambda: self._change_mark_color(idx))
            menu.addAction(color_act)
            
            del_act = QAction("Delete Mark", self)
            del_act.triggered.connect(lambda: self._delete_mark(idx))
            menu.addAction(del_act)
            
        elif itype == "mark_group":
            indices = item.data(0, Qt.UserRole + 1)
            color_act = QAction("Change Group Color", self)
            color_act.triggered.connect(lambda: self._change_group_color(indices))
            menu.addAction(color_act)
            
            del_act = QAction("Delete Group", self)
            del_act.triggered.connect(lambda: self._delete_group(indices))
            menu.addAction(del_act)
            
        elif itype == "symbol":
            key = item.data(0, Qt.UserRole + 1)
            del_act = QAction("Delete Symbol", self)
            del_act.triggered.connect(lambda: self._delete_symbol(key))
            menu.addAction(del_act)
            
        elif itype == "note":
            key = item.data(0, Qt.UserRole + 1)
            
            if not key.startswith("standalone_"):
                parts = key.split('|')
                ref = f"{parts[0]} {parts[1]}:{parts[2]}"
                
                go_act = QAction("Go to Reference", self)
                go_act.triggered.connect(lambda: self.jumpRequested.emit(parts[0], parts[1], parts[2]))
                menu.addAction(go_act)
            
            open_act = QAction("Open Note Editor", self)
            open_act.triggered.connect(lambda: self._open_note(key))
            menu.addAction(open_act)
            
            # Move to Folder Submenu
            move_menu = QMenu("Move to Folder", self)
            move_menu.setStyleSheet("QMenu { background-color: #333; color: white; } QMenu::item:selected { background-color: #555; }")
            
            # Root option
            root_act = QAction("(Notes Root)", self)
            root_act.triggered.connect(lambda: self._move_note(key, ""))
            move_menu.addAction(root_act)
            
            for f_path in sorted(self.study_manager.data.get("note_folders", [])):
                f_act = QAction(f_path, self)
                f_act.triggered.connect(lambda checked=False, p=f_path: self._move_note(key, p))
                move_menu.addAction(f_act)
            
            menu.addMenu(move_menu)
            
            del_act = QAction("Delete Note", self)
            del_act.triggered.connect(lambda: self._delete_note(key))
            menu.addAction(del_act)
            
        elif itype == "arrow":
            key = item.data(0, Qt.UserRole + 1)
            idx = item.data(0, Qt.UserRole + 2)
            del_act = QAction("Delete Arrow", self)
            del_act.triggered.connect(lambda: self._delete_arrow(key, idx))
            menu.addAction(del_act)
            
        if menu.actions():
            menu.exec(self.tree.mapToGlobal(pos))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            item = self.tree.currentItem()
            if not item: return
            
            itype = item.data(0, Qt.UserRole)
            if itype == "mark":
                self._delete_mark(item.data(0, Qt.UserRole + 2))
            elif itype == "mark_group":
                self._delete_group(item.data(0, Qt.UserRole + 1))
            elif itype == "symbol":
                self._delete_symbol(item.data(0, Qt.UserRole + 1))
            elif itype == "note":
                self._delete_note(item.data(0, Qt.UserRole + 1))
            elif itype == "note_folder":
                self._delete_folder(item.data(0, Qt.UserRole + 1))
            elif itype == "arrow":
                self._delete_arrow(item.data(0, Qt.UserRole + 1), item.data(0, Qt.UserRole + 2))
            elif itype == "bookmark":
                self._delete_bookmark(item.data(0, Qt.UserRole + 1)['ref'])
        else:
            super().keyPressEvent(event)

    def _change_mark_color(self, idx):
        m = self.study_manager.data["marks"][idx]
        color = QColorDialog.getColor(Qt.yellow, self, "Select Mark Color")
        if color.isValid():
            self.study_manager.save_state()
            self.study_manager.data["marks"][idx]["color"] = color.name()
            self.study_manager.save_study()
            self.dataChanged.emit()
            self.refresh()

    def _delete_mark(self, idx):
        self.study_manager.save_state()
        self.study_manager.data["marks"].pop(idx)
        self.study_manager.save_study()
        self.dataChanged.emit()
        self.refresh()

    def _change_group_color(self, indices):
        color = QColorDialog.getColor(Qt.yellow, self, "Select Group Color")
        if color.isValid():
            self.study_manager.save_state()
            for idx in indices:
                self.study_manager.data["marks"][idx]["color"] = color.name()
            self.study_manager.save_study()
            self.dataChanged.emit()
            self.refresh()

    def _delete_group(self, indices):
        self.study_manager.save_state()
        # Sort indices in descending order to avoid shifting issues when popping
        for idx in sorted(indices, reverse=True):
            self.study_manager.data["marks"].pop(idx)
        self.study_manager.save_study()
        self.dataChanged.emit()
        self.refresh()

    def _delete_symbol(self, key):
        self.study_manager.save_state()
        if key in self.study_manager.data["symbols"]:
            del self.study_manager.data["symbols"][key]
            self.study_manager.save_study()
            self.dataChanged.emit()
            self.refresh()

    def _add_standalone_note(self, folder=""):
        # Just create it, the manager will handle default title if empty
        key = self.study_manager.add_standalone_note(title="", text="", folder=folder)
        self.refresh()
        self._open_note(key)

    def _add_folder(self, parent_path=""):
        name, ok = QInputDialog.getText(self, "New Folder", "Enter folder name:")
        if ok and name:
            full_path = f"{parent_path}/{name}" if parent_path else name
            self.study_manager.add_folder(full_path)
            self.refresh()

    def _move_note(self, note_key, folder_path):
        self.study_manager.move_note(note_key, folder_path)
        self.refresh()

    def _delete_folder(self, folder_path):
        # Check if folder or any sub-folder has notes
        has_content = False
        for key, note_data in self.study_manager.data["notes"].items():
            f = note_data.get("folder", "")
            if f == folder_path or f.startswith(f"{folder_path}/"):
                has_content = True
                break
        
        # Check for empty sub-folders
        if not has_content:
            for f in self.study_manager.data["note_folders"]:
                if f.startswith(f"{folder_path}/"):
                    has_content = True
                    break

        if has_content:
            res = QMessageBox.question(self, "Delete Folder", 
                                      f"The folder '{folder_path}' and its sub-folders contain notes.\n"
                                      "Are you sure you want to delete them? All notes inside will be PERMANENTLY deleted.",
                                      QMessageBox.Yes | QMessageBox.No)
            if res != QMessageBox.Yes:
                return

        self.study_manager.delete_folder(folder_path)
        self.refresh()

    def _delete_note(self, key):
        self.study_manager.delete_note(key)
        self.dataChanged.emit()
        self.refresh()

    def _delete_arrow(self, key, idx):
        self.study_manager.save_state()
        if key in self.study_manager.data["arrows"]:
            self.study_manager.data["arrows"][key].pop(idx)
            if not self.study_manager.data["arrows"][key]:
                del self.study_manager.data["arrows"][key]
            self.study_manager.save_study()
            self.dataChanged.emit()
            self.refresh()

    def _delete_bookmark(self, ref):
        self.study_manager.delete_bookmark(ref)
        self.dataChanged.emit()
        self.refresh()

    def _open_note(self, key):
        if key.startswith("standalone_"):
            # Use empty ref or custom string for standalone notes
            self.noteOpenRequested.emit(key, "General Note")
        else:
            parts = key.split('|')
            ref = f"{parts[0]} {parts[1]}:{parts[2]}"
            self.jumpRequested.emit(parts[0], parts[1], parts[2])
            self.noteOpenRequested.emit(key, ref)
