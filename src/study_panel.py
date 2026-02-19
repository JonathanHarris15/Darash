from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, 
    QLabel, QMenu, QColorDialog, QInputDialog, QMessageBox
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
        
        self.tree.itemDoubleClicked.connect(self._on_item_clicked)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_context_menu)
        
        self.refresh()

    def refresh(self):
        self.tree.clear()
        
        # 1. Marks
        marks_root = QTreeWidgetItem(self.tree, ["Marks"])
        marks_root.setExpanded(True)
        for i, m in enumerate(self.study_manager.data.get("marks", [])):
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
        notes_root.setExpanded(True)
        for key, text in self.study_manager.data.get("notes", {}).items():
            parts = key.split('|')
            ref = f"{parts[0]} {parts[1]}:{parts[2]}"
            snippet = text[:30] + "..." if len(text) > 30 else text
            item = QTreeWidgetItem(notes_root, [f"{ref}: {snippet}"])
            item.setData(0, Qt.UserRole, "note")
            item.setData(0, Qt.UserRole + 1, key)
            
        # 4. Arrows
        arrows_root = QTreeWidgetItem(self.tree, ["Arrows"])
        arrows_root.setExpanded(True)
        for key, arrow_list in self.study_manager.data.get("arrows", {}).items():
            parts = key.split('|')
            ref = f"{parts[0]} {parts[1]}:{parts[2]}"
            for i, a in enumerate(arrow_list):
                item = QTreeWidgetItem(arrows_root, [f"{ref} Arrow {i+1}"])
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
        elif itype == "bookmark":
            b = item.data(0, Qt.UserRole + 1)
            self.jumpRequested.emit(b['book'], b['chapter'], b['verse'])
        elif itype in ["symbol", "note", "arrow"]:
            key = item.data(0, Qt.UserRole + 1)
            parts = key.split('|')
            self.jumpRequested.emit(parts[0], parts[1], parts[2])

    def _on_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not item: return
        
        itype = item.data(0, Qt.UserRole)
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #333; color: white; } QMenu::item:selected { background-color: #555; }")
        
        if itype == "mark":
            idx = item.data(0, Qt.UserRole + 2)
            color_act = QAction("Change Color", self)
            color_act.triggered.connect(lambda: self._change_mark_color(idx))
            menu.addAction(color_act)
            
            del_act = QAction("Delete Mark", self)
            del_act.triggered.connect(lambda: self._delete_mark(idx))
            menu.addAction(del_act)
            
        elif itype == "symbol":
            key = item.data(0, Qt.UserRole + 1)
            del_act = QAction("Delete Symbol", self)
            del_act.triggered.connect(lambda: self._delete_symbol(key))
            menu.addAction(del_act)
            
        elif itype == "note":
            key = item.data(0, Qt.UserRole + 1)
            open_act = QAction("Open Note Editor", self)
            open_act.triggered.connect(lambda: self._open_note(key))
            menu.addAction(open_act)
            
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
            elif itype == "symbol":
                self._delete_symbol(item.data(0, Qt.UserRole + 1))
            elif itype == "note":
                self._delete_note(item.data(0, Qt.UserRole + 1))
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

    def _delete_symbol(self, key):
        self.study_manager.save_state()
        if key in self.study_manager.data["symbols"]:
            del self.study_manager.data["symbols"][key]
            self.study_manager.save_study()
            self.dataChanged.emit()
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
        parts = key.split('|')
        ref = f"{parts[0]} {parts[1]}:{parts[2]}"
        self.jumpRequested.emit(parts[0], parts[1], parts[2])
        self.noteOpenRequested.emit(key, ref)
