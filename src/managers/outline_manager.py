import uuid
from typing import List, Dict, Optional, Tuple
from src.managers.outline_ref_utils import OutlineRefUtils
from src.managers.outline_tree_ops import OutlineTreeOps

class OutlineManager:
    """Manages the hierarchy of outlines. Delegation to specialized helpers for tree/ref logic."""
    def __init__(self, study_manager):
        self.study_manager = study_manager
        if "outlines" not in self.study_manager.data:
            self.study_manager.data["outlines"] = []
            self.study_manager.save_data()

    def get_outlines(self) -> List[Dict]:
        return self.study_manager.data.get("outlines", [])

    def create_outline(self, start_ref: str, end_ref: str, title: str, summary: str = "") -> Dict:
        new_outline = {
            "id": str(uuid.uuid4()), "title": title, "summary": summary,
            "range": {"start": start_ref, "end": end_ref}, "children": [], "expanded": True
        }
        split1, split2 = OutlineRefUtils.calculate_range_split(start_ref, end_ref, self.study_manager.loader)
        if split1 and split2:
            c1 = {"id": str(uuid.uuid4()), "title": "Section 1", "expanded": True,
                  "range": {"start": start_ref, "end": split1.split('-')[1] if '-' in split1 else split1}, "children": []}
            c2 = {"id": str(uuid.uuid4()), "title": "Section 2", "expanded": True,
                  "range": {"start": split2.split('-')[0], "end": end_ref}, "children": []}
            new_outline["children"] = [c1, c2]; new_outline["split_levels"] = [1]
        self.study_manager.data["outlines"].append(new_outline); self.study_manager.save_data()
        return new_outline

    def add_section(self, parent_id: str, start_ref: str, end_ref: str, title: str, summary: str = "") -> Optional[Dict]:
        parent = self.get_node(parent_id)
        if parent:
            new_section = {"id": str(uuid.uuid4()), "title": title, "summary": summary,
                           "range": {"start": start_ref, "end": end_ref}, "children": [], "expanded": True}
            parent.setdefault("children", []).append(new_section)
            lvl = OutlineTreeOps.get_node_level(self.get_outlines(), parent["id"])
            if "split_levels" not in parent: parent["split_levels"] = [lvl + 1] * (len(parent["children"]) - 1)
            else: parent["split_levels"].append(lvl + 1)
            self.study_manager.save_data(); return new_section
        return None

    def update_node(self, node_id: str, title=None, summary=None, range_start=None, range_end=None):
        node = self.get_node(node_id)
        if node:
            if title is not None: node["title"] = title
            if summary is not None: node["summary"] = summary
            if range_start: node["range"]["start"] = range_start
            if range_end: node["range"]["end"] = range_end
            self.study_manager.save_data(); return True
        return False

    def delete_node(self, node_id: str):
        outlines = self.get_outlines()
        for i, outline in enumerate(outlines):
            if outline["id"] == node_id:
                outlines.pop(i); self.study_manager.save_data(); return True
        if OutlineTreeOps.delete_node_recursive(outlines, node_id):
            self.study_manager.save_data(); return True
        return False

    def delete_node_smart(self, node_id: str):
        outlines = self.get_outlines()
        if any(o["id"] == node_id for o in outlines): return False
        parent, idx = OutlineTreeOps.find_parent_and_index(outlines, node_id)
        if parent and idx != -1:
            if any(o["id"] == parent["id"] for o in outlines) and len(parent["children"]) <= 2: return False
            node = parent["children"][idx]
            if len(parent["children"]) <= 2:
                parent["children"] = []; parent["split_levels"] = []
            else:
                if idx > 0:
                    parent["children"][idx-1]["range"]["end"] = node["range"]["end"]
                    parent["children"].pop(idx); parent["split_levels"].pop(idx-1)
                else:
                    parent["children"][idx+1]["range"]["start"] = node["range"]["start"]
                    parent["children"].pop(idx); parent["split_levels"].pop(0)
            self.study_manager.save_data(); return True
        return False

    def delete_divider_smart(self, parent_id: str, split_idx: int):
        outlines = self.get_outlines()
        parent = self.get_node(parent_id)
        if not parent or "children" not in parent or len(parent["children"]) <= split_idx + 1: return False
        if OutlineTreeOps.get_node_level(outlines, parent["id"]) == 0 and len(parent["children"]) <= 2: return False
        if len(parent["children"]) == 2:
            parent["children"] = []; parent["split_levels"] = []
        else:
            node_after = parent["children"][split_idx + 1]
            parent["children"][split_idx]["range"]["end"] = node_after["range"]["end"]
            parent["children"].pop(split_idx + 1); parent["split_levels"].pop(split_idx)
            if len(parent["children"]) == 1: parent["children"] = []; parent["split_levels"] = []
        self.study_manager.save_data(); return True

    def add_split(self, ref_before: str, ref_after: str, loader):
        outlines = self.get_outlines()
        innermost = OutlineTreeOps.find_innermost_covering(outlines, ref_before, ref_after, loader)
        if not innermost or innermost.get("children"): return None
        parent, idx = OutlineTreeOps.find_parent_and_index(outlines, innermost["id"])
        c1 = {"id": str(uuid.uuid4()), "title": innermost.get("title", "Section") + " A", "expanded": True,
              "range": {"start": innermost["range"]["start"], "end": ref_before}, "children": []}
        c2 = {"id": str(uuid.uuid4()), "title": innermost.get("title", "Section") + " B", "expanded": True,
              "range": {"start": ref_after, "end": innermost["range"]["end"]}, "children": []}
        if parent:
            parent["children"].pop(idx); parent["children"].insert(idx, c2); parent["children"].insert(idx, c1)
            new_level = parent["split_levels"][idx] if parent.get("split_levels") and idx < len(parent["split_levels"]) else 1
            parent.setdefault("split_levels", []).insert(idx, new_level)
            self.study_manager.save_data(); return parent
        else:
            innermost["children"] = [c1, c2]
            innermost["split_levels"] = [OutlineTreeOps.get_node_level(outlines, innermost["id"]) + 1]
            self.study_manager.save_data(); return innermost

    def cycle_level_by_id(self, parent_id: str, split_idx: int, forward: bool):
        outlines = self.get_outlines()
        parent = self.get_node(parent_id)
        if not parent or "children" not in parent or len(parent["children"]) <= split_idx + 1: return False
        parent_level = OutlineTreeOps.get_node_level(outlines, parent["id"])
        if forward:
            if len(parent["children"]) <= 2: return False
            s1, s2 = parent["children"][split_idx], parent["children"][split_idx + 1]
            new_node = {"id": str(uuid.uuid4()), "title": f"Group: {s1['title']} & {s2['title']}" if s1['title'] and s2['title'] else "New Group",
                        "summary": "", "range": {"start": s1["range"]["start"], "end": s2["range"]["end"]},
                        "children": [s1, s2], "expanded": True, "split_levels": [parent_level + 2]}
            parent["children"].pop(split_idx + 1); parent["children"][split_idx] = new_node
            if "split_levels" in parent: parent["split_levels"].pop(split_idx)
        else:
            if parent_level == 0: return False
            grand_parent, p_idx = OutlineTreeOps.find_parent_and_index(outlines, parent["id"])
            if grand_parent:
                children = parent["children"]; grand_parent["children"].pop(p_idx)
                for i, child in enumerate(children): grand_parent["children"].insert(p_idx + i, child)
                if "split_levels" not in grand_parent: grand_parent["split_levels"] = [parent_level - 1] * (len(grand_parent["children"]) - 1)
                else:
                    for _ in range(len(children) - 1): grand_parent["split_levels"].insert(p_idx, parent_level)
            else: return False
        self.study_manager.save_data(); return True

    def move_split_by_id(self, parent_id: str, split_idx: int, new_ref_before: str, new_ref_after: str, loader):
        node = self.get_node(parent_id)
        if node and "children" in node and len(node["children"]) > split_idx + 1:
            c1, c2 = node["children"][split_idx], node["children"][split_idx+1]
            if loader.get_verse_index(c1["range"]["start"]) <= loader.get_verse_index(new_ref_before) < loader.get_verse_index(new_ref_after) <= loader.get_verse_index(c2["range"]["end"]):
                c1["range"]["end"], c2["range"]["start"] = new_ref_before, new_ref_after
                OutlineTreeOps.propagate_end_change(c1, new_ref_before); OutlineTreeOps.propagate_start_change(c2, new_ref_after)
                self.study_manager.save_data(); return True
        return False

    def adjust_node_boundary(self, root_id, node_id, is_start, delta, loader, is_word_drag=False):
        if delta == 0: return False
        root = self.get_node(root_id)
        if not root: return False
        node = OutlineTreeOps.get_node([root], node_id)
        if not node: return False

        shift_fn = OutlineRefUtils.shift_ref_by_words if is_word_drag else OutlineRefUtils.shift_ref_by_verses
        if is_start:
            curr_right = node['range']['start']
            curr_left = shift_fn(curr_right, -1, loader)
        else:
            curr_left = node['range']['end']
            curr_right = shift_fn(curr_left, 1, loader)

        max_left_idx = float('-inf'); max_left_ref = None
        min_right_idx = float('inf'); min_right_ref = None

        def find_limits(n):
            nonlocal max_left_idx, min_right_idx, max_left_ref, min_right_ref
            if curr_left and n['range']['end'] == curr_left:
                s_idx = loader.get_verse_index(n['range']['start'])
                if s_idx > max_left_idx: max_left_idx = s_idx; max_left_ref = n['range']['start']
            if curr_right and n['range']['start'] == curr_right:
                e_idx = loader.get_verse_index(n['range']['end'])
                if e_idx < min_right_idx: min_right_idx = e_idx; min_right_ref = n['range']['end']
            for c in n.get('children', []): find_limits(c)

        find_limits(root)
        new_left_ref = shift_fn(curr_left, delta, loader) if curr_left else None
        new_right_ref = shift_fn(curr_right, delta, loader) if curr_right else None
        new_left_idx = loader.get_verse_index(new_left_ref) if new_left_ref else -1.0
        new_right_idx = loader.get_verse_index(new_right_ref) if new_right_ref else float('inf')

        clamped = False
        if curr_left and max_left_idx != float('-inf'):
            if new_left_idx <= max_left_idx:
                new_left_ref = max_left_ref
                new_right_ref = shift_fn(max_left_ref, 1, loader)
                clamped = True
        if curr_right and min_right_idx != float('inf') and not clamped:
            if new_right_idx >= min_right_idx:
                new_right_ref = min_right_ref
                new_left_ref = shift_fn(min_right_ref, -1, loader)

        changed = False
        def apply_shift(n):
            nonlocal changed
            if curr_left and n['range']['end'] == curr_left: n['range']['end'] = new_left_ref; changed = True
            if curr_right and n['range']['start'] == curr_right: n['range']['start'] = new_right_ref; changed = True
            for c in n.get('children', []): apply_shift(c)
        apply_shift(root)
        if changed: self.study_manager.save_data(); return True
        return False

    def update_outline_boundary(self, outline_id, is_top, new_ref, loader):
        node = self.get_node(outline_id)
        if not node: return False
        if is_top: node["range"]["start"] = new_ref; OutlineTreeOps.propagate_start_change(node, new_ref)
        else: node["range"]["end"] = new_ref; OutlineTreeOps.propagate_end_change(node, new_ref)
        self.study_manager.save_data(); return True

    def get_node(self, node_id: str) -> Optional[Dict]:
        return OutlineTreeOps.get_node(self.get_outlines(), node_id)

    def get_all_split_indices(self, exclude_split_idx=None) -> List[float]:
        all_splits = set(); loader = self.study_manager.loader
        for outline in self.get_outlines():
            all_splits.add(loader.get_verse_index(outline["range"]["end"]))
            start_idx = loader.get_verse_index(outline["range"]["start"])
            if start_idx >= 0.1: all_splits.add(start_idx - 1.0 if int(start_idx) == start_idx else start_idx - 0.1)
            self._collect_split_indices_recursive(outline, all_splits)
        sorted_splits = sorted(list(all_splits))
        return [s for s in sorted_splits if s != exclude_split_idx] if exclude_split_idx is not None else sorted_splits

    def _collect_split_indices_recursive(self, node, all_splits):
        if "children" in node and node["children"]:
            for i in range(len(node["children"]) - 1):
                idx = self.study_manager.loader.get_verse_index(node["children"][i]["range"]["end"])
                if idx != -1.0: all_splits.add(idx)
            for child in node["children"]: self._collect_split_indices_recursive(child, all_splits)

    def get_nearest_split_indices(self, current_split_idx) -> Tuple[Optional[float], Optional[float]]:
        all_splits = self.get_all_split_indices(exclude_split_idx=current_split_idx)
        prec = max((s for s in all_splits if s < current_split_idx - 0.01), default=None)
        succ = min((s for s in all_splits if s > current_split_idx + 0.01), default=None)
        return prec, succ
