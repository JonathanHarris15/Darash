from PySide6.QtWidgets import QTreeWidgetItem, QStyle
from PySide6.QtCore import Qt

class StudyTreePopulator:
    """Helper to populate and manage items for StudyTreeWidget."""
    def __init__(self, tree):
        self.tree = tree
        self.study_manager = tree.study_manager
        self.symbol_manager = tree.symbol_manager

    def populate_all(self):
        tree = self.tree
        # 1. Outlines
        root_out = QTreeWidgetItem(tree, ["Outlines"])
        for o in self.study_manager.outline_manager.get_outlines():
            it = QTreeWidgetItem(root_out, [o["title"]])
            it.setData(0, Qt.UserRole, "outline"); it.setData(0, Qt.UserRole + 1, o["id"])

        # 2. Marks
        root_marks = QTreeWidgetItem(tree, ["Marks"])
        mark_cats = {
            "highlight": QTreeWidgetItem(root_marks, ["Highlights"]),
            "underline": QTreeWidgetItem(root_marks, ["Underlines"]),
            "box": QTreeWidgetItem(root_marks, ["Boxes"]),
            "circle": QTreeWidgetItem(root_marks, ["Circles"]),
            "arrow": QTreeWidgetItem(root_marks, ["Arrows"]),
            "verse_mark": QTreeWidgetItem(root_marks, ["Verse Marks"])
        }
        all_m = self.study_manager.data.get("marks", [])
        grouped = {}
        for i, m in enumerate(all_m):
            t = m.get("type", "highlight")
            if t not in grouped: grouped[t] = {"ungrouped": []}
            gid = m.get("group_id")
            if gid:
                if gid not in grouped[t]: grouped[t][gid] = []
                grouped[t][gid].append(i)
            else: grouped[t]["ungrouped"].append(i)
        
        for t, groups in grouped.items():
            parent = mark_cats.get(t, root_marks)
            for gid, idxs in groups.items():
                if gid == "ungrouped": continue
                group_data = [all_m[i] for i in idxs]
                it = QTreeWidgetItem(parent, [tree._get_range_string(group_data)])
                it.setData(0, Qt.UserRole, "mark_group"); it.setData(0, Qt.UserRole + 1, idxs); it.setData(0, Qt.UserRole + 2, group_data[0])
            for i in groups["ungrouped"]:
                m = all_m[i]; it = QTreeWidgetItem(parent, [f"{m['book']} {m['chapter']}:{m['verse_num']}"])
                it.setData(0, Qt.UserRole, "mark"); it.setData(0, Qt.UserRole + 1, m); it.setData(0, Qt.UserRole + 2, i)
        
        # Arrows
        arrow_p = mark_cats["arrow"]; counts = {}
        for key in sorted(self.study_manager.data.get("arrows", {}).keys()):
            p = key.split('|')
            if len(p) < 3: continue
            ref = f"{p[0]} {p[1]}:{p[2]}"
            counts[ref] = counts.get(ref, 0)
            for i, a in enumerate(self.study_manager.data["arrows"][key]):
                counts[ref] += 1
                it = QTreeWidgetItem(arrow_p, [f"{ref} Arrow {counts[ref]}"])
                it.setData(0, Qt.UserRole, "arrow"); it.setData(0, Qt.UserRole + 1, key); it.setData(0, Qt.UserRole + 2, i)

        # Verse Marks
        vm_p = mark_cats["verse_mark"]; vm_data = self.study_manager.data.get("verse_marks", {})
        vm_types = {"heart": "Hearts", "question": "Questions", "attention": "Attention (!!)", "star": "Stars"}
        vm_nodes = {}
        for r, t in sorted(vm_data.items()):
            if t not in vm_nodes:
                vm_nodes[t] = QTreeWidgetItem(vm_p, [vm_types.get(t, t.title())]); vm_nodes[t].setExpanded(True)
            it = QTreeWidgetItem(vm_nodes[t], [r]); it.setData(0, Qt.UserRole, "verse_mark"); it.setData(0, Qt.UserRole + 1, r)
        for c in list(mark_cats.values()):
            if c.childCount() == 0: root_marks.removeChild(c)

        # 3. Logical Marks
        root_log = QTreeWidgetItem(tree, ["Logical Marks"]); data_log = self.study_manager.data.get("logical_marks", {})
        if data_log:
            groups_log = {}
            for k, t in data_log.items():
                groups_log.setdefault(t, []).append(k)
            for t, ks in groups_log.items():
                g_it = QTreeWidgetItem(root_log, [t.replace("_", " ").title()])
                for k in sorted(ks, key=lambda x: (x.split('|')[0], int(x.split('|')[1]) if len(x.split('|'))>1 else 0)):
                    p = k.split('|'); it = QTreeWidgetItem(g_it, [f"{p[0]} {p[1]}:{p[2]}" if len(p)>=3 else k])
                    it.setData(0, Qt.UserRole, "logical_mark"); it.setData(0, Qt.UserRole + 1, k)
        if root_log.childCount() == 0: tree.takeTopLevelItem(tree.indexOfTopLevelItem(root_log)) if tree.indexOfTopLevelItem(root_log)!=-1 else None

        # 4. Symbols
        root_sym = QTreeWidgetItem(tree, ["Symbols"]); groups_sym = {}
        for k, f in self.study_manager.data.get("symbols", {}).items():
            n = self.symbol_manager.get_symbol_name(f); groups_sym.setdefault(n, []).append((k, f))
        for n in sorted(groups_sym.keys()):
            g_it = QTreeWidgetItem(root_sym, [n]); g_it.setData(0, Qt.UserRole, "symbol_type_group")
            for k, f in sorted(groups_sym[n], key=lambda x: (x[0].split('|')[0], int(x[0].split('|')[1]) if len(x[0].split('|'))>1 else 0)):
                p = k.split('|'); it = QTreeWidgetItem(g_it, [f"{p[0]} {p[1]}:{p[2]}" if len(p)>=3 else k])
                it.setData(0, Qt.UserRole, "symbol"); it.setData(0, Qt.UserRole + 1, k); it.setData(0, Qt.UserRole + 2, f)

        # 5. Notes
        root_notes = QTreeWidgetItem(tree, ["Notes"]); root_notes.setData(0, Qt.UserRole, "notes_header")
        folders = {"": root_notes}
        for path in sorted(self.study_manager.data.get("note_folders", [])):
            curr, prev = "", ""
            for part in path.split("/"):
                prev = curr; curr = f"{curr}/{part}" if curr else part
                if curr not in folders:
                    it = QTreeWidgetItem(folders[prev], [part]); it.setIcon(0, tree.style().standardIcon(QStyle.SP_DirIcon))
                    it.setData(0, Qt.UserRole, "note_folder"); it.setData(0, Qt.UserRole + 1, curr); folders[curr] = it
        for k, d in self.study_manager.data.get("notes", {}).items():
            f = d.get("folder", "") if isinstance(d, dict) else ""; t = d.get("title", "") if isinstance(d, dict) else d
            p = folders.get(f, root_notes); label = t if k.startswith("standalone_") else (f"{k.split('|')[0]} {k.split('|')[1]}:{k.split('|')[2]} - {t}" if len(k.split('|'))>=3 and t else (f"{k.split('|')[0]} {k.split('|')[1]}:{k.split('|')[2]}" if len(k.split('|'))>=3 else t or k))
            it = QTreeWidgetItem(p, [label]); it.setData(0, Qt.UserRole, "note"); it.setData(0, Qt.UserRole + 1, k)

        # 6. Bookmarks
        root_bms = QTreeWidgetItem(tree, ["Bookmarks"])
        for b in self.study_manager.data.get("bookmarks", []):
            it = QTreeWidgetItem(root_bms, [f"{b['title']} ({b['ref']})" if b.get('title') else b['ref']])
            it.setData(0, Qt.UserRole, "bookmark"); it.setData(0, Qt.UserRole + 1, b)
