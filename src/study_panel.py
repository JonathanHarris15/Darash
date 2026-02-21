from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem, 
    QLabel, QMenu, QColorDialog, QInputDialog, QMessageBox, QStyle,
    QPushButton
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
        
        # Bottom Action Menu
        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(0, 5, 0, 0)
        
        self.add_note_btn = QPushButton()
        self.add_note_btn.setIcon(self.style().standardIcon(QStyle.SP_FileIcon))
        self.add_note_btn.setToolTip("New Standalone Note")
        self.add_note_btn.clicked.connect(lambda: self._add_standalone_note(""))
        
        self.add_outline_btn = QPushButton()
        self.add_outline_btn.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        self.add_outline_btn.setToolTip("New Outline (Coming Soon)")
        # Placeholder for future outline logic
        self.add_outline_btn.clicked.connect(lambda: QMessageBox.information(self, "Coming Soon", "The Outline feature is currently under development."))
        
        # Style the buttons
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
        
        # 1. Marks (includes Highlights, Underlines, Boxes, Circles, and Arrows)
        marks_root = QTreeWidgetItem(self.tree, ["Marks"])
        marks_root.setExpanded(True)
        
        # Sub-categories for marks
        mark_categories = {
            "highlight": QTreeWidgetItem(marks_root, ["Highlights"]),
            "underline": QTreeWidgetItem(marks_root, ["Underlines"]),
            "box": QTreeWidgetItem(marks_root, ["Boxes"]),
            "circle": QTreeWidgetItem(marks_root, ["Circles"]),
            "arrow": QTreeWidgetItem(marks_root, ["Arrows"]),
            "verse_mark": QTreeWidgetItem(marks_root, ["Verse Marks"])
        }
        
        # Marks grouping logic
        all_marks = self.study_manager.data.get("marks", [])
        # Group marks by type first, then by group_id
        type_grouped_marks = {} # {type: {group_id: [indices], "ungrouped": [indices]}}
        
        for i, m in enumerate(all_marks):
            m_type = m.get("type", "highlight")
            if m_type not in type_grouped_marks:
                type_grouped_marks[m_type] = {"ungrouped": []}
            
            gid = m.get("group_id")
            if gid:
                if gid not in type_grouped_marks[m_type]:
                    type_grouped_marks[m_type][gid] = []
                type_grouped_marks[m_type][gid].append(i)
            else:
                type_grouped_marks[m_type]["ungrouped"].append(i)

        # Add marks to their respective categories
        for m_type, groups in type_grouped_marks.items():
            parent = mark_categories.get(m_type, marks_root)
            
            # Add grouped marks
            for gid, indices in groups.items():
                if gid == "ungrouped": continue
                group_data = [all_marks[i] for i in indices]
                range_str = self._get_range_string(group_data)
                
                item = QTreeWidgetItem(parent, [range_str])
                item.setData(0, Qt.UserRole, "mark_group")
                item.setData(0, Qt.UserRole + 1, indices)
                item.setData(0, Qt.UserRole + 2, group_data[0])
            
            # Add ungrouped marks
            for i in groups["ungrouped"]:
                m = all_marks[i]
                ref = f"{m['book']} {m['chapter']}:{m['verse_num']}"
                item = QTreeWidgetItem(parent, [ref])
                item.setData(0, Qt.UserRole, "mark")
                item.setData(0, Qt.UserRole + 1, m)
                item.setData(0, Qt.UserRole + 2, i)

        # Add Arrows to the Arrow sub-category
        arrow_parent = mark_categories["arrow"]
        verse_arrow_counts = {}
        sorted_keys = sorted(self.study_manager.data.get("arrows", {}).keys())
        for key in sorted_keys:
            arrow_list = self.study_manager.data["arrows"][key]
            parts = key.split('|')
            ref = f"{parts[0]} {parts[1]}:{parts[2]}"
            if ref not in verse_arrow_counts: verse_arrow_counts[ref] = 0
            for i, a in enumerate(arrow_list):
                verse_arrow_counts[ref] += 1
                item = QTreeWidgetItem(arrow_parent, [f"{ref} Arrow {verse_arrow_counts[ref]}"])
                item.setData(0, Qt.UserRole, "arrow")
                item.setData(0, Qt.UserRole + 1, key)
                item.setData(0, Qt.UserRole + 2, i)

        # Add Verse Marks
        vm_parent = mark_categories["verse_mark"]
        verse_marks_data = self.study_manager.data.get("verse_marks", {})
        
        # Group by mark type for display
        vm_types = {
            "heart": "Hearts",
            "question": "Questions",
            "attention": "Attention (!!)",
            "star": "Stars"
        }
        
        vm_type_nodes = {}
        for ref, m_type in sorted(verse_marks_data.items()):
            if m_type not in vm_type_nodes:
                type_label = vm_types.get(m_type, m_type.title())
                vm_type_nodes[m_type] = QTreeWidgetItem(vm_parent, [type_label])
                vm_type_nodes[m_type].setExpanded(True)
            
            item = QTreeWidgetItem(vm_type_nodes[m_type], [ref])
            item.setData(0, Qt.UserRole, "verse_mark")
            item.setData(0, Qt.UserRole + 1, ref)

        # Hide empty mark categories
        for cat in mark_categories.values():
            if cat.childCount() == 0:
                marks_root.removeChild(cat)

        # 2. Symbols
        symbols_root = QTreeWidgetItem(self.tree, ["Symbols"])
        symbols_root.setExpanded(True)
        
        symbol_groups = {} # {display_name: [(key, s_file)]}
        for key, s_file in self.study_manager.data.get("symbols", {}).items():
            display_name = self.symbol_manager.get_symbol_name(s_file)
            if display_name not in symbol_groups:
                symbol_groups[display_name] = []
            symbol_groups[display_name].append((key, s_file))
            
        for display_name in sorted(symbol_groups.keys()):
            group_item = QTreeWidgetItem(symbols_root, [display_name])
            group_item.setData(0, Qt.UserRole, "symbol_type_group")
            group_item.setExpanded(True)
            
            # Sort by verse reference
            def sort_ref(item_tuple):
                k = item_tuple[0].split('|')
                # book, chap, verse, word
                return (k[0], int(k[1]), int(k[2]), int(k[3]))
                
            for key, s_file in sorted(symbol_groups[display_name], key=sort_ref):
                parts = key.split('|')
                ref = f"{parts[0]} {parts[1]}:{parts[2]}"
                
                item = QTreeWidgetItem(group_item, [ref])
                item.setData(0, Qt.UserRole, "symbol")
                item.setData(0, Qt.UserRole + 1, key)
                item.setData(0, Qt.UserRole + 2, s_file)
            
        # 3. Notes (Always visible)
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
                
                if title:
                    # Clean up redundant prefixes
                    if ref in title:
                        label = title
                    else:
                        label = f"{ref} - {title}"
                else:
                    label = ref
            
            item = QTreeWidgetItem(parent_item, [label])
            item.setData(0, Qt.UserRole, "note")
            item.setData(0, Qt.UserRole + 1, key)

        # 4. Bookmarks
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
        elif itype == "verse_mark":
            ref = item.data(0, Qt.UserRole + 1)
            # Parse ref "Book Chap:Verse"
            import re
            match = re.match(r"(.*) (\d+):(\d+)", ref)
            if match:
                book, chap, verse = match.groups()
                self.jumpRequested.emit(book, chap, verse)

    def _create_symbol_list_note(self, symbol_items):
        if not symbol_items: return
        
        # Collect symbol names and references
        names = set()
        refs = [] # List of (book, chap, verse)
        
        for item in symbol_items:
            key = item.data(0, Qt.UserRole + 1)
            s_file = item.data(0, Qt.UserRole + 2)
            names.add(self.symbol_manager.get_symbol_name(s_file))
            
            parts = key.split('|')
            refs.append({
                "book": parts[0],
                "chapter": int(parts[1]),
                "verse": int(parts[2]),
                "word_idx": int(parts[3]),
                "ref_str": f"{parts[0]} {parts[1]}:{parts[2]}"
            })
            
        # Sort references
        def sort_key(r):
            # We don't have book order here easily, so we just group by book
            return (r['book'], r['chapter'], r['verse'], r['word_idx'])
        
        sorted_refs = sorted(refs, key=sort_key)
        
        # Calculate Range String
        if len(sorted_refs) == 1:
            range_str = sorted_refs[0]['ref_str']
        else:
            first = sorted_refs[0]
            last = sorted_refs[-1]
            if first['book'] == last['book'] and first['chapter'] == last['chapter']:
                if first['verse'] == last['verse']:
                    range_str = first['ref_str'] # Genesis 1:1 instead of 1:1-1
                else:
                    range_str = f"{first['book']} {first['chapter']}:{first['verse']}-{last['verse']}"
            else:
                range_str = f"{first['ref_str']} - {last['ref_str']}"

        # Determine Title
        if len(names) == 1:
            title = f"{list(names)[0]} - {range_str}"
        else:
            title = f"Symbol List - {range_str}"
            
        # Create Markdown Content
        # No title in content as it's redundant with the title metadata
        content = "## Symbol List\n"
        for r in sorted_refs:
            content += f"- {r['ref_str']} - \n"
            
        # Create the note attached to the first symbol's word position
        # This makes it jumpable from the Study Overview and Reader
        first = sorted_refs[0]
        note_key = f"{first['book']}|{first['chapter']}|{first['verse']}|{first['word_idx']}"
        self.study_manager.add_note(first['book'], str(first['chapter']), str(first['verse']), first['word_idx'], 
                                   content, title)
        
        self.refresh()
        self._open_note(note_key)

    def _on_context_menu(self, pos):
        selected_items = self.tree.selectedItems()
        if not selected_items: return
        
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #333; color: white; } QMenu::item:selected { background-color: #555; }")

        # Handle Multiple Selection Context Menu
        if len(selected_items) > 1:
            # Check for symbol list note possibility
            symbol_items = []
            for item in selected_items:
                itype = item.data(0, Qt.UserRole)
                if itype == "symbol":
                    symbol_items.append(item)
                elif itype == "symbol_type_group":
                    for i in range(item.childCount()):
                        symbol_items.append(item.child(i))
            
            # If everything selected (directly or via group root) is a symbol
            # and we have at least one symbol...
            if symbol_items and len(selected_items) > 1:
                # We need to be careful: if the user selected a group root AND its children, 
                # we don't want to duplicate symbols in the list.
                unique_symbol_items = list(set(symbol_items))
                
                list_note_act = QAction("Create Symbol List Note", self)
                list_note_act.triggered.connect(lambda: self._create_symbol_list_note(unique_symbol_items))
                menu.addAction(list_note_act)
            
            # Bulk Delete Action
            del_act = QAction(f"Delete Selected ({len(selected_items)})", self)
            del_act.triggered.connect(self._delete_selected_items)
            menu.addAction(del_act)
            
            menu.exec(self.tree.mapToGlobal(pos))
            return

        # Handle Single Selection (Existing Logic)
        item = selected_items[0]
        itype = item.data(0, Qt.UserRole)
        
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
            
        elif itype == "verse_mark":
            ref = item.data(0, Qt.UserRole + 1)
            del_act = QAction("Delete Verse Mark", self)
            del_act.triggered.connect(lambda: self._delete_verse_mark(ref))
            menu.addAction(del_act)
            
        if menu.actions():
            menu.exec(self.tree.mapToGlobal(pos))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            self._delete_selected_items()
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

    def _delete_verse_mark(self, ref):
        self.study_manager.set_verse_mark(ref, None)
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

    def _delete_selected_items(self):
        selected_items = self.tree.selectedItems()
        if not selected_items: return
        
        # Confirmation for multiple items or folders
        if len(selected_items) > 5 or any(i.data(0, Qt.UserRole) in ["note_folder", "symbol_type_group"] for i in selected_items):
            res = QMessageBox.question(self, "Confirm Bulk Deletion", 
                                      f"Are you sure you want to delete {len(selected_items)} selected items?",
                                      QMessageBox.Yes | QMessageBox.No)
            if res != QMessageBox.Yes:
                return

        self.study_manager.save_state()
        
        # Categorize items for bulk deletion
        to_del = {
            "marks": [], # indices
            "symbols": [], # keys
            "notes": [], # keys
            "note_folders": [], # paths
            "arrows": [], # (key, idx)
            "bookmarks": [], # refs
            "verse_marks": [] # refs
        }
        
        # Expand any groups to their children
        expanded_selected = []
        for item in selected_items:
            itype = item.data(0, Qt.UserRole)
            if itype == "symbol_type_group":
                for i in range(item.childCount()):
                    expanded_selected.append(item.child(i))
            else:
                expanded_selected.append(item)

        for item in expanded_selected:
            itype = item.data(0, Qt.UserRole)
            if itype == "mark":
                to_del["marks"].append(item.data(0, Qt.UserRole + 2))
            elif itype == "mark_group":
                to_del["marks"].extend(item.data(0, Qt.UserRole + 1))
            elif itype == "symbol":
                to_del["symbols"].append(item.data(0, Qt.UserRole + 1))
            elif itype == "note":
                to_del["notes"].append(item.data(0, Qt.UserRole + 1))
            elif itype == "note_folder":
                to_del["note_folders"].append(item.data(0, Qt.UserRole + 1))
            elif itype == "arrow":
                to_del["arrows"].append((item.data(0, Qt.UserRole + 1), item.data(0, Qt.UserRole + 2)))
            elif itype == "bookmark":
                to_del["bookmarks"].append(item.data(0, Qt.UserRole + 1)['ref'])
            elif itype == "verse_mark":
                to_del["verse_marks"].append(item.data(0, Qt.UserRole + 1))
        
        # Execute Deletions
        # Marks (reverse sort indices to pop correctly)
        if to_del["marks"]:
            for idx in sorted(list(set(to_del["marks"])), reverse=True):
                self.study_manager.data["marks"].pop(idx)
        
        # Symbols
        for key in to_del["symbols"]:
            if key in self.study_manager.data["symbols"]:
                del self.study_manager.data["symbols"][key]
        
        # Notes
        for key in to_del["notes"]:
            self.study_manager.delete_note(key)
        
        # Folders
        for path in to_del["note_folders"]:
            self.study_manager.delete_folder(path)
        
        # Arrows
        arrow_map = {}
        for key, idx in to_del["arrows"]:
            if key not in arrow_map: arrow_map[key] = []
            arrow_map[key].append(idx)
        for key, indices in arrow_map.items():
            if key in self.study_manager.data["arrows"]:
                for idx in sorted(list(set(indices)), reverse=True):
                    self.study_manager.data["arrows"][key].pop(idx)
                if not self.study_manager.data["arrows"][key]:
                    del self.study_manager.data["arrows"][key]
        
        # Bookmarks
        for ref in to_del["bookmarks"]:
            self.study_manager.delete_bookmark(ref)
            
        # Verse Marks
        for ref in to_del["verse_marks"]:
            self.study_manager.set_verse_mark(ref, None)
            
        self.study_manager.save_study()
        self.dataChanged.emit()
        self.refresh()
