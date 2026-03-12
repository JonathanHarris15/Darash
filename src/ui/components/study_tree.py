from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QStyle, QColorDialog, QInputDialog, QMessageBox
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QAction, QColor
from src.utils.menu_utils import create_menu
from src.core.theme import Theme
from src.ui.components.study_tree_populator import StudyTreePopulator

class StudyTreeWidget(QTreeWidget):
    """Facade for study data tree. Delegates population to StudyTreePopulator."""
    jumpRequested = Signal(str, str, str); noteOpenRequested = Signal(str, str)
    outlineOpenRequested = Signal(str); outlineDeleted = Signal(str); dataChanged = Signal()

    def __init__(self, study_manager, symbol_manager, parent=None):
        super().__init__(parent); self.study_manager = study_manager; self.symbol_manager = symbol_manager
        self.populator = StudyTreePopulator(self); self.setHeaderHidden(True); self.setIndentation(15)
        self.setSelectionMode(QTreeWidget.ExtendedSelection); self.setDragEnabled(True); self.setAcceptDrops(True)
        self.setDragDropMode(QTreeWidget.InternalMove); self.setDropIndicatorShown(True)
        self.setStyleSheet(f"QTreeWidget {{ background-color: {Theme.BG_PRIMARY}; border: 1px solid {Theme.BORDER_DEFAULT}; color: {Theme.TEXT_SECONDARY}; }} QTreeWidget::item {{ padding: 4px; }} QTreeWidget::item:hover {{ background-color: {Theme.BG_SECONDARY}; }} QTreeWidget::item:selected {{ background-color: {Theme.BG_TERTIARY}; color: {Theme.TEXT_PRIMARY}; }}")
        self.itemDoubleClicked.connect(self._on_item_clicked); self.setContextMenuPolicy(Qt.CustomContextMenu); self.customContextMenuRequested.connect(self._on_context_menu)

    def dragEnterEvent(self, e): e.accept() if e.mimeData().hasFormat("application/x-qabstractitemmodeldatalist") else super().dragEnterEvent(e)
    def dropEvent(self, event):
        src = self.currentItem(); tgt = self.itemAt(event.pos())
        if not src or not tgt: event.ignore(); return
        st, tt, sk, tk = src.data(0, Qt.UserRole), tgt.data(0, Qt.UserRole), src.data(0, Qt.UserRole + 1), tgt.data(0, Qt.UserRole + 1)
        if st == "note":
            if tt == "note_folder": self.study_manager.move_note(sk, tk); self.refresh(); event.accept()
            elif tt == "notes_header": self.study_manager.move_note(sk, ""); self.refresh(); event.accept()
        elif st == "note_folder" and tt in ["notes_header", "note_folder"]:
            if tt == "notes_header": self.study_manager.move_folder(sk, ""); self.refresh(); event.accept()
            elif sk != tk and not tk.startswith(f"{sk}/"): self.study_manager.move_folder(sk, tk); self.refresh(); event.accept()
        else: event.ignore()

    def _get_range_string(self, marks):
        if not marks: return ""
        if len(marks) == 1: return f"{marks[0]['book']} {marks[0]['chapter']}:{marks[0]['verse_num']}"
        s = sorted(marks, key=lambda x: int(x['verse_num']))
        if s[0]['book'] == s[-1]['book'] and s[0]['chapter'] == s[-1]['chapter']: return f"{s[0]['book']} {s[0]['chapter']}:{s[0]['verse_num']}-{s[-1]['verse_num']}"
        return f"{s[0]['book']} {s[0]['chapter']}:{s[0]['verse_num']} - {s[-1]['book']} {s[-1]['chapter']}:{s[-1]['verse_num']}"

    def refresh(self):
        exp = set()
        def save(it, p=""):
            cp = f"{p}/{it.text(0)}" if p else it.text(0)
            if it.isExpanded(): exp.add(cp)
            for i in range(it.childCount()): save(it.child(i), cp)
        for i in range(self.topLevelItemCount()): save(self.topLevelItem(i))
        self.clear(); self.populator.populate_all()
        if not exp:
            for i in range(self.topLevelItemCount()): self.topLevelItem(i).setExpanded(True)
        else:
            def restore(it, p=""):
                cp = f"{p}/{it.text(0)}" if p else it.text(0); it.setExpanded(cp in exp)
                for i in range(it.childCount()): restore(it.child(i), cp)
            for i in range(self.topLevelItemCount()): restore(self.topLevelItem(i))

    def _on_item_clicked(self, it, col):
        t, d1, d2 = it.data(0, Qt.UserRole), it.data(0, Qt.UserRole + 1), it.data(0, Qt.UserRole + 2)
        if t == "outline": self.outlineOpenRequested.emit(d1)
        elif t == "mark": self.jumpRequested.emit(d1['book'], str(d1['chapter']), str(d1['verse_num']))
        elif t == "mark_group": self.jumpRequested.emit(d2['book'], str(d2['chapter']), str(d2['verse_num']))
        elif t == "bookmark": self.jumpRequested.emit(d1['book'], d1['chapter'], d1['verse'])
        elif t == "note":
            if d1.startswith("standalone_"): self.noteOpenRequested.emit(d1, "General Note")
            else: p = d1.split('|'); self.jumpRequested.emit(p[0], p[1], p[2]); self.noteOpenRequested.emit(d1, f"{p[0]} {p[1]}:{p[2]}")
        elif t in ["symbol", "arrow", "logical_mark"]:
            p = d1.split('|'); self.jumpRequested.emit(p[0], p[1], p[2]) if len(p)>=3 else None
        elif t == "verse_mark":
            import re; m = re.match(r"(.*) (\d+):(\d+)", d1)
            if m: self.jumpRequested.emit(m.group(1), m.group(2), m.group(3))

    def _on_context_menu(self, pos):
        sel = self.selectedItems()
        if not sel: return
        m = create_menu(self)
        if len(sel) > 1:
            syms = []
            for i in sel:
                if i.data(0, Qt.UserRole) == "symbol": syms.append(i)
                elif i.data(0, Qt.UserRole) == "symbol_type_group":
                    for j in range(i.childCount()): syms.append(i.child(j))
            if syms: m.addAction("Create Symbol List Note").triggered.connect(lambda: self._create_symbol_list_note(list(set(syms))))
            m.addAction(f"Delete Selected ({len(sel)})").triggered.connect(self._delete_selected_items)
            m.exec(self.mapToGlobal(pos)); return
        it = sel[0]; t, d = it.data(0, Qt.UserRole), it.data(0, Qt.UserRole + 1)
        if t == "notes_header":
            m.addAction("New Standalone Note").triggered.connect(lambda: self._add_standalone_note())
            m.addAction("New Folder").triggered.connect(lambda: self._add_folder())
        elif t == "note_folder":
            m.addAction("New Note in Folder").triggered.connect(lambda: self._add_standalone_note(d))
            m.addAction("New Sub-folder").triggered.connect(lambda: self._add_folder(d))
            m.addSeparator(); m.addAction("Delete Folder").triggered.connect(lambda: self._delete_folder(d))
        elif t == "mark":
            m.addAction("Change Color").triggered.connect(lambda: self._change_mark_color(d)); m.addAction("Delete Mark").triggered.connect(lambda: self._delete_mark(d))
        elif t == "mark_group":
            m.addAction("Change Group Color").triggered.connect(lambda: self._change_group_color(d)); m.addAction("Delete Group").triggered.connect(lambda: self._delete_group(d))
        elif t == "symbol": m.addAction("Delete Symbol").triggered.connect(lambda: self._delete_symbol(d))
        elif t == "note":
            if not d.startswith("standalone_"): p = d.split('|'); m.addAction("Go to Reference").triggered.connect(lambda: self.jumpRequested.emit(p[0], p[1], p[2]))
            m.addAction("Open Note Editor").triggered.connect(lambda: self.noteOpenRequested.emit(d, ""))
            mm = create_menu(self, "Move to Folder"); mm.addAction("(Notes Root)").triggered.connect(lambda: self.study_manager.move_note(d, ""))
            for f in sorted(self.study_manager.data.get("note_folders", [])): mm.addAction(f).triggered.connect(lambda c=False, p=f: self.study_manager.move_note(d, p))
            m.addMenu(mm); m.addAction("Delete Note").triggered.connect(lambda: self._delete_note(d))
        elif t == "arrow": m.addAction("Delete Arrow").triggered.connect(lambda: self._delete_arrow(d, it.data(0, Qt.UserRole + 2)))
        elif t == "logical_mark": m.addAction("Delete Logical Mark").triggered.connect(lambda: self._delete_logical_mark(d))
        elif t == "verse_mark": m.addAction("Delete Verse Mark").triggered.connect(lambda: self.study_manager.set_verse_mark(d, None))
        elif t == "outline": m.addAction("Delete Outline").triggered.connect(lambda: self._delete_outline(d))
        if m.actions(): m.exec(self.mapToGlobal(pos))

    def _delete_selected_items(self):
        items = self.selectedItems()
        if not items: return
        if len(items) > 5 and QMessageBox.question(self, "Confirm Bulk Deletion", f"Delete {len(items)} items?", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes: return
        self.study_manager.save_state(); to_del = {"m": [], "s": [], "n": [], "f": [], "a": [], "bm": [], "vm": [], "lm": [], "o": []}
        flat = []
        for i in items:
            if i.data(0, Qt.UserRole) == "symbol_type_group":
                for j in range(i.childCount()): flat.append(i.child(j))
            else: flat.append(i)
        for i in flat:
            t, d1 = i.data(0, Qt.UserRole), i.data(0, Qt.UserRole + 1)
            if t == "mark": to_del["m"].append(d1)
            elif t == "mark_group":
                for idx in d1: 
                    if idx < len(self.study_manager.data["marks"]): to_del["m"].append(self.study_manager.data["marks"][idx])
            elif t == "symbol": to_del["s"].append(d1)
            elif t == "note": to_del["n"].append(d1)
            elif t == "note_folder": to_del["f"].append(d1)
            elif t == "arrow": to_del["a"].append((d1, i.data(0, Qt.UserRole + 2)))
            elif t == "bookmark": to_del["bm"].append(d1['ref'])
            elif t == "verse_mark": to_del["vm"].append(d1)
            elif t == "logical_mark": to_del["lm"].append(d1)
            elif t == "outline": to_del["o"].append(d1); self.outlineDeleted.emit(d1)
        m_ids = set(id(m) for m in to_del["m"])
        self.study_manager.data["marks"] = [m for m in self.study_manager.data["marks"] if id(m) not in m_ids]
        for k in to_del["s"]: self.study_manager.data["symbols"].pop(k, None)
        for k in to_del["lm"]: self.study_manager.data.get("logical_marks", {}).pop(k, None)
        for nid in to_del["o"]: self.study_manager.outline_manager.delete_node(nid)
        for k in to_del["n"]: self.study_manager.delete_note(k)
        for p in to_del["f"]: self.study_manager.delete_folder(p)
        for k, idx in sorted(to_del["a"], key=lambda x: x[1], reverse=True):
            self.study_manager.data["arrows"][k].pop(idx)
            if not self.study_manager.data["arrows"][k]: del self.study_manager.data["arrows"][k]
        for r in to_del["bm"]: self.study_manager.delete_bookmark(r)
        for r in to_del["vm"]: self.study_manager.set_verse_mark(r, None)
        self.study_manager.save_data(); self.dataChanged.emit(); self.refresh()

    def _delete_outline(self, nid):
        if QMessageBox.question(self, "Delete Outline", "Are you sure?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.study_manager.outline_manager.delete_node(nid); self.outlineDeleted.emit(nid); self.dataChanged.emit(); self.refresh()
    def _add_standalone_note(self, f=""): key = self.study_manager.add_standalone_note("", "", f); self.refresh(); self.noteOpenRequested.emit(key, "General Note")
    def _add_folder(self, p=""):
        n, ok = QInputDialog.getText(self, "New Folder", "Name:"); 
        if ok and n: self.study_manager.add_folder(f"{p}/{n}" if p else n); self.refresh()
    def _delete_folder(self, p):
        if QMessageBox.question(self, "Delete Folder", f"Delete {p} and all contents?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes: self.study_manager.delete_folder(p); self.refresh()
    def _change_mark_color(self, m):
        c = QColorDialog.getColor(Qt.yellow, self, "Color"); 
        if c.isValid(): self.study_manager.save_state(); m["color"] = c.name(); self.study_manager.save_data(); self.refresh()
    def _delete_mark(self, d): self.study_manager.save_state(); self.study_manager.data["marks"] = [m for m in self.study_manager.data["marks"] if m is not d]; self.study_manager.save_data(); self.refresh()
    def _change_group_color(self, idxs):
        c = QColorDialog.getColor(Qt.yellow, self, "Color"); 
        if c.isValid():
            self.study_manager.save_state()
            for i in idxs: self.study_manager.data["marks"][i]["color"] = c.name()
            self.study_manager.save_data(); self.refresh()
    def _delete_group(self, idxs): self.study_manager.save_state(); [self.study_manager.data["marks"].pop(i) for i in sorted(idxs, reverse=True)]; self.study_manager.save_data(); self.refresh()
    def _delete_symbol(self, k): self.study_manager.save_state(); self.study_manager.data["symbols"].pop(k, None); self.study_manager.save_data(); self.refresh()
    def _delete_note(self, k): self.study_manager.delete_note(k); self.refresh()
    def _delete_arrow(self, k, i): 
        self.study_manager.save_state(); self.study_manager.data["arrows"][k].pop(i)
        if not self.study_manager.data["arrows"][k]: del self.study_manager.data["arrows"][k]
        self.study_manager.save_data(); self.refresh()
    def _delete_logical_mark(self, k): self.study_manager.save_state(); self.study_manager.data.get("logical_marks", {}).pop(k, None); self.study_manager.save_data(); self.refresh()
