import uuid
import re
from typing import List, Dict, Optional, Tuple

class OutlineManager:
    """
    Manages the hierarchy of outlines.
    Each outline is a tree structure covering a range of verses.
    """
    def __init__(self, study_manager):
        self.study_manager = study_manager
        # Ensure outlines exist in study data
        if "outlines" not in self.study_manager.data:
            self.study_manager.data["outlines"] = []
            self.study_manager.save_study()

    def get_outlines(self) -> List[Dict]:
        return self.study_manager.data.get("outlines", [])

    def create_outline(self, start_ref: str, end_ref: str, title: str, summary: str = "") -> Dict:
        """Creates a new top-level outline with two initial sub-sections."""
        new_outline = {
            "id": str(uuid.uuid4()),
            "title": title,
            "summary": summary,
            "range": {"start": start_ref, "end": end_ref},
            "children": [],
            "expanded": True
        }
        
        # Automatically create initial split if possible
        split1, split2 = self._calculate_range_split(start_ref, end_ref)
        if split1 and split2:
            c1 = {
                "id": str(uuid.uuid4()),
                "title": "Section 1",
                "range": {"start": start_ref, "end": self._get_end_ref_from_split(split1)},
                "children": [],
                "expanded": True
            }
            c2 = {
                "id": str(uuid.uuid4()),
                "title": "Section 2",
                "range": {"start": self._get_start_ref_from_split(split2), "end": end_ref},
                "children": [],
                "expanded": True
            }
            new_outline["children"] = [c1, c2]
            new_outline["split_levels"] = [1]

        self.study_manager.data["outlines"].append(new_outline)
        self.study_manager.save_study()
        return new_outline

    def _calculate_range_split(self, start_ref, end_ref):
        loader = self.study_manager.loader
        if not loader: return None, None
        
        # Support optional 'a' or 'b' suffix
        m_s = re.match(r"(.*) (\d+):(\d+)([a-z])?", start_ref)
        m_e = re.match(r"(.*) (\d+):(\d+)([a-z])?", end_ref)
        
        if not m_s or not m_e: return None, None
        
        s_base = f"{m_s.group(1)} {m_s.group(2)}:{m_s.group(3)}"
        e_base = f"{m_e.group(1)} {m_e.group(2)}:{m_e.group(3)}"
        
        # If already at part level granularity (a/b), don't split further
        if m_s.group(4) or m_e.group(4): return None, None
        
        idx_s = loader.get_verse_index(s_base)
        idx_e = loader.get_verse_index(e_base)
        
        if idx_s == -1 or idx_e == -1: return None, None
        
        if idx_s == idx_e:
            return f"{s_base}a", f"{s_base}b"
        else:
            mid = int((idx_s + idx_e) // 2)
            ref_mid_end = loader.flat_verses[mid]['ref']
            ref_mid_start = loader.flat_verses[mid+1]['ref']
            return f"{s_base}-{ref_mid_end}", f"{ref_mid_start}-{e_base}"

    def _get_start_ref_from_split(self, split_str):
        return split_str.split('-')[0]

    def _get_end_ref_from_split(self, split_str):
        parts = split_str.split('-')
        return parts[1] if len(parts) > 1 else parts[0]

    def add_section(self, parent_id: str, start_ref: str, end_ref: str, title: str, summary: str = "") -> Optional[Dict]:
        """Adds a child section to a parent outline node."""
        parent = self.get_node(parent_id)
        if parent:
            new_section = {
                "id": str(uuid.uuid4()),
                "title": title,
                "summary": summary,
                "range": {"start": start_ref, "end": end_ref},
                "children": [],
                "expanded": True
            }
            parent.setdefault("children", []).append(new_section)
            
            # Determine the level of the new split
            parent_level = self._get_node_level(self.get_outlines(), parent["id"])
            new_split_level = parent_level + 1
            
            # Initialize split_levels if this is adding to an existing split
            if "split_levels" not in parent:
                parent["split_levels"] = [new_split_level] * (len(parent["children"]) - 1)
            else:
                # Add a default level for the new child. We need to find where to insert it.
                # For simplicity, append for now.
                parent["split_levels"].append(new_split_level)
            
            # Sort children by range? (Optional but helpful)
            self.study_manager.save_study()
            return new_section
        return None

    def update_node(self, node_id: str, title: str = None, summary: str = None, range_start: str = None, range_end: str = None):
        """Updates a node's properties."""
        node = self.get_node(node_id)
        if node:
            if title is not None: node["title"] = title
            if summary is not None: node["summary"] = summary
            if range_start: node["range"]["start"] = range_start
            if range_end: node["range"]["end"] = range_end
            self.study_manager.save_study()
            return True
        return False

    def delete_node(self, node_id: str):
        """Deletes a node and its children."""
        outlines = self.get_outlines()
        # Check top level
        for i, outline in enumerate(outlines):
            if outline["id"] == node_id:
                outlines.pop(i)
                self.study_manager.save_study()
                return True
        
        # Check children
        if self._delete_node_recursive(outlines, node_id):
            self.study_manager.save_study()
            return True
        return False

    def delete_node_smart(self, node_id: str):
        """
        Deletes a node and redistributes its range to its neighbors.
        If it has a previous sibling, that sibling takes its range.
        If not, but has a next sibling, that sibling takes its range.
        If it's the only child, the parent loses all children.
        
        RULE: No bullet point should ever have only one sub-point. 
        If deleting one sibling leaves only one other sibling, that remaining sibling is also removed,
        effectively merging both back into the parent.
        """
        outlines = self.get_outlines()
        
        # NEVER delete a top-level outline via "smart delete" (merging logic)
        for outline in outlines:
            if outline["id"] == node_id:
                return False
        
        parent, idx = self._find_parent_and_index(outlines, node_id)
        if parent and idx != -1:
            # Check if parent is a top-level outline (meaning node is level 1)
            is_level_1 = any(o["id"] == parent["id"] for o in outlines)
            if is_level_1 and len(parent["children"]) <= 2:
                return False # Always protect at least two primary points (1. and 2.)
                
            node = parent["children"][idx]
            
            if len(parent["children"]) == 1:
                # Only child, just clear children
                parent["children"] = []
                if "split_levels" in parent:
                    parent["split_levels"] = []
            elif len(parent["children"]) == 2:
                # If we delete one of two children, we must remove BOTH
                # to satisfy the "no single sub-point" rule.
                parent["children"] = []
                if "split_levels" in parent:
                    parent["split_levels"] = []
            else:
                # Redistribute range to neighbors
                if idx > 0:
                    # Give range to previous sibling
                    parent["children"][idx-1]["range"]["end"] = node["range"]["end"]
                    parent["children"].pop(idx)
                    if "split_levels" in parent and len(parent["split_levels"]) >= idx:
                        parent["split_levels"].pop(idx-1)
                else:
                    # Give range to next sibling
                    parent["children"][idx+1]["range"]["start"] = node["range"]["start"]
                    parent["children"].pop(idx)
                    if "split_levels" in parent and len(parent["split_levels"]) > 0:
                        parent["split_levels"].pop(0)
                        
            self.study_manager.save_study()
            return True
        return False

    def delete_divider_smart(self, parent_id: str, split_idx: int):
        """
        Specialized deletion for a division line between children.
        If there are exactly 2 children, removes BOTH children.
        Otherwise, removes the child AFTER the divider and redistributes its range to the child BEFORE.
        """
        outlines = self.get_outlines()
        parent = self.get_node(parent_id)
        if not parent or "children" not in parent or len(parent["children"]) <= split_idx + 1:
            return False

        # Protect top-level (level 0) primary points (1. and 2.)
        # Check both direct ID match and recursive level check for robustness
        is_level_0 = any(o["id"] == parent["id"] for o in outlines)
        if not is_level_0:
            is_level_0 = (self._get_node_level(outlines, parent["id"]) == 0)

        if is_level_0 and len(parent["children"]) <= 2:
            return False

        if len(parent["children"]) == 2:
            # Deleting the divider between exactly two children: Remove both
            parent["children"] = []
            if "split_levels" in parent:
                parent["split_levels"] = []
        else:
            # Multiple children: remove the child after the divider and merge its range back
            # into the child before the divider.
            node_after = parent["children"][split_idx + 1]
            parent["children"][split_idx]["range"]["end"] = node_after["range"]["end"]
            parent["children"].pop(split_idx + 1)
            if "split_levels" in parent and len(parent["split_levels"]) > split_idx:
                parent["split_levels"].pop(split_idx)
                
            # Check if we now only have one child left (shouldn't happen with 3+, 
            # but if something else removed a child simultaneously, enforce rule)
            if len(parent["children"]) == 1:
                parent["children"] = []
                if "split_levels" in parent:
                    parent["split_levels"] = []

        self.study_manager.save_study()
        return True

    def _find_parent_and_index(self, nodes, target_id):
        for node in nodes:
            children = node.get("children", [])
            for i, child in enumerate(children):
                if child["id"] == target_id:
                    return node, i
                p, idx = self._find_parent_and_index([child], target_id)
                if p: return p, idx
        return None, -1

    def _delete_node_recursive(self, nodes: List[Dict], target_id: str) -> bool:
        for node in nodes:
            if "children" in node:
                for i, child in enumerate(node["children"]):
                    if child["id"] == target_id:
                        node["children"].pop(i)
                        return True
                    if self._delete_node_recursive(node["children"], target_id):
                        return True
        return False

    def add_split(self, ref_before: str, ref_after: str, loader):
        """
        Splits the innermost outline containing both references between them.
        """
        outlines = self.get_outlines()
        innermost = self._find_innermost_covering(outlines, ref_before, ref_after, loader)
        if not innermost: return None
            
        # If it has children, check if it's already a split point
        if innermost.get("children"):
            for i in range(len(innermost["children"]) - 1):
                c1 = innermost["children"][i]
                c2 = innermost["children"][i+1]
                if self._is_ref_equal_or_after(ref_before, c1["range"]["end"], loader) and \
                   self._is_ref_equal_or_before(ref_after, c2["range"]["start"], loader):
                    return None # Already a split point
            return None
            
        # Split the leaf node
        # Check if we can split in-place within the parent (preferred for Level 1 splits)
        parent, idx = self._find_parent_and_index(outlines, innermost["id"])
        
        c1 = {
            "id": str(uuid.uuid4()),
            "title": innermost.get("title", "Section") + " A",
            "range": {"start": innermost["range"]["start"], "end": ref_before},
            "children": [],
            "expanded": True
        }
        c2 = {
            "id": str(uuid.uuid4()),
            "title": innermost.get("title", "Section") + " B",
            "range": {"start": ref_after, "end": innermost["range"]["end"]},
            "children": [],
            "expanded": True
        }
        
        if parent:
            # Insert c1, c2 into parent at idx, replacing innermost
            parent["children"].pop(idx)
            parent["children"].insert(idx, c2)
            parent["children"].insert(idx, c1)
            
            # Update split_levels
            # We need to insert a level for the new split between c1 and c2.
            # Use the existing level if available, or determine from context.
            if "split_levels" not in parent:
                parent["split_levels"] = []
                
            # If parent has split_levels, try to match neighbors or default to 1
            new_level = 1
            if parent["split_levels"]:
                if idx < len(parent["split_levels"]): new_level = parent["split_levels"][idx]
                elif idx > 0: new_level = parent["split_levels"][idx-1]
            
            # The split between c1 and c2 is at index 'idx' now (since c1 is at idx, c2 is at idx+1)
            # wait. children was [... A ...] -> [... c1, c2 ...]
            # split at idx was between A and Next. Now it's between c2 and Next.
            # We need to INSERT a split at idx (between c1 and c2).
            # The existing split at idx (if any) moves to idx+1.
            
            # Wait, if we replace A with c1, c2.
            # Old splits: [s0, s1 (after A), s2]
            # New children: [..., c1, c2, ...]
            # New splits: [s0, NEW_SPLIT, s1, s2]
            
            # If idx was 0 (first child).
            # Children: [A, B] -> [c1, c2, B]
            # Splits: [s_AB] -> [s_c1c2, s_c2B]
            
            parent["split_levels"].insert(idx, new_level)
            
            self.study_manager.save_study()
            return parent # Return parent to trigger refresh
            
        else:
            # Root node or no parent found - Nesting (Standard behavior for root)
            innermost["children"] = [c1, c2]
            
            # Determine the level of the new split relative to its parent
            parent_level = self._get_node_level(self.get_outlines(), innermost["id"])
            new_split_level = parent_level + 1
            innermost["split_levels"] = [new_split_level]
            
            self.study_manager.save_study()
            return innermost

    def cycle_level(self, ref_before: str, ref_after: str, forward: bool, loader):
        """Cycles the level of the divider between ref_before and ref_after."""
        outlines = self.get_outlines()
        node, split_idx = self._find_node_with_split(outlines, ref_before, ref_after, loader)
        
        if node and split_idx != -1:
            if "split_levels" not in node:
                # Initialize split_levels if missing
                node["split_levels"] = [1] * (len(node["children"]) - 1)
            
            current_level = node["split_levels"][split_idx]
            if forward:
                new_level = (current_level + 1) % 10 # Cycle up to 9
            else:
                new_level = max(0, current_level - 1)
            
            node["split_levels"][split_idx] = new_level
            self.study_manager.save_study()
            return True
        return False

    def cycle_level_by_id(self, parent_id: str, split_idx: int, forward: bool):
        """
        Cycles the level of a specific divider by restructuring the tree.
        Forward (Increase level/Tab): Demotes siblings into a new parent group.
        Backward (Decrease level/Shift+Tab): Promotes children to the parent's level.
        """
        outlines = self.get_outlines()
        parent = self.get_node(parent_id)
        if not parent or "children" not in parent or len(parent["children"]) <= split_idx + 1:
            return False
            
        parent_level = self._get_node_level(outlines, parent["id"])

        if forward:
            # DEMOTE (Tab): Group S1 and S2 into a new parent
            # Constraint 1: Cannot demote if parent has only 2 children (would leave parent with 1 child)
            if len(parent["children"]) <= 2:
                return False
            
            # Constraint 2: Cannot demote if it would create a level jump > 1
            # (Implicitly handled by restructuring: new group is always parent_level + 1)
                
            s1 = parent["children"][split_idx]
            s2 = parent["children"][split_idx + 1]
            
            new_node = {
                "id": str(uuid.uuid4()),
                "title": f"Group: {s1['title']} & {s2['title']}" if s1['title'] and s2['title'] else "New Group",
                "summary": "",
                "range": {
                    "start": s1["range"]["start"],
                    "end": s2["range"]["end"]
                },
                "children": [s1, s2],
                "expanded": True,
                # New split levels will be recalculated or defaulted.
                # The split INSIDE the new group (between s1 and s2) will be parent_level + 2
                "split_levels": [parent_level + 2] 
            }
            
            # Replace s1 and s2 with new_node
            parent["children"].pop(split_idx + 1)
            parent["children"][split_idx] = new_node
            
            # Update parent's split_levels: remove the split that was consumed
            if "split_levels" in parent and len(parent["split_levels"]) > split_idx:
                parent["split_levels"].pop(split_idx)
            
        else:
            # PROMOTE (Shift+Tab): Dissolve the parent if it's not a top-level outline
            
            # Constraint: Cannot promote to Level 0 (Double Line) unless merging top-level nodes (not supported)
            # Level 0 = Top-level Outline
            if parent_level == 0:
                return False

            grand_parent, p_idx = self._find_parent_and_index(outlines, parent["id"])
            if grand_parent:
                # Move all children of parent into grand_parent
                children = parent["children"]
                grand_parent["children"].pop(p_idx)
                
                # Insert children at the old position of parent
                for i, child in enumerate(children):
                    grand_parent["children"].insert(p_idx + i, child)
                
                # Update grand_parent's split_levels
                # We need to insert len(children)-1 split levels at p_idx
                # These new splits should be at parent_level (since they were children of parent)
                
                if "split_levels" not in grand_parent: 
                    grand_parent["split_levels"] = [parent_level - 1] * (len(grand_parent["children"]) - 1)
                else:
                    # Remove the split that was after parent (now gone) - Wait, split levels are gaps.
                    # If we had [A, Parent, B], split at p_idx was between Parent and B.
                    # We removed Parent. Now we insert [C1...Cn].
                    # Splits become: [s_AC1, s_C1C2...s_CnB]
                    # We need to insert len(children)-1 splits for the internal gaps.
                    # And maybe update the surrounding splits?
                    # Simpler: just insert default level splits.
                    
                    # Correct logic:
                    # The split at `p_idx` in `grand_parent["split_levels"]` corresponded to the gap AFTER `parent`.
                    # Now `parent` is replaced by `children[0]...children[-1]`.
                    # The gap after `children[-1]` corresponds to the old split at `p_idx`.
                    # We need to insert new splits for the gaps between the new siblings.
                    
                    # We need `len(children) - 1` new entries.
                    # Their level should be `parent_level`.
                    for _ in range(len(children) - 1):
                        grand_parent["split_levels"].insert(p_idx, parent_level)
            else:
                return False

        self.study_manager.save_study()
        return True

    def move_split_by_id(self, parent_id: str, split_idx: int, new_ref_before: str, new_ref_after: str, loader):
        """Moves a split point by targeting a specific parent node and split index."""
        node = self.get_node(parent_id)
        if node and "children" in node and len(node["children"]) > split_idx + 1:
            c1 = node["children"][split_idx]
            c2 = node["children"][split_idx+1]
            
            idx_c1_start = loader.get_verse_index(c1["range"]["start"])
            idx_new_before = loader.get_verse_index(new_ref_before)
            idx_new_after = loader.get_verse_index(new_ref_after)
            idx_c2_end = loader.get_verse_index(c2["range"]["end"])
            
            # Constraints: Each section must have at least one verse, and splits cannot cross or overlap.
            if idx_c1_start <= idx_new_before and idx_new_after <= idx_c2_end and idx_new_before < idx_new_after:
                # Update the nodes directly involved
                c1["range"]["end"] = new_ref_before
                c2["range"]["start"] = new_ref_after
                
                # Propagate changes to the children that share these boundaries
                self._propagate_end_change(c1, new_ref_before)
                self._propagate_start_change(c2, new_ref_after)
                
                self.study_manager.save_study()
                return True
        return False

    def update_outline_boundary(self, outline_id: str, is_top: bool, new_ref: str, loader):
        """Updates the outer start or end boundary of an outline and propagates to children."""
        node = self.get_node(outline_id)
        if not node: return False
        
        if is_top:
            node["range"]["start"] = new_ref
            # Propagate to first child recursively
            self._propagate_start_change(node, new_ref)
        else:
            node["range"]["end"] = new_ref
            # Propagate to last child recursively
            self._propagate_end_change(node, new_ref)
            
        self.study_manager.save_study()
        return True

    def _propagate_start_change(self, node: Dict, new_start: str):
        """Recursively updates the start reference of the first child."""
        if "children" in node and node["children"]:
            first_child = node["children"][0]
            first_child["range"]["start"] = new_start
            self._propagate_start_change(first_child, new_start)

    def _propagate_end_change(self, node: Dict, new_end: str):
        """Recursively updates the end reference of the last child."""
        if "children" in node and node["children"]:
            last_child = node["children"][-1]
            last_child["range"]["end"] = new_end
            self._propagate_end_change(last_child, new_end)

    def _find_node_with_split(self, nodes, ref1, ref2, loader):
        for node in nodes:
            children = node.get("children", [])
            for i in range(len(children) - 1):
                if children[i]["range"]["end"] == ref1 and children[i+1]["range"]["start"] == ref2:
                    return node, i
            
            # Check recursively in children
            found_node, found_idx = self._find_node_with_split(children, ref1, ref2, loader)
            if found_node: return found_node, found_idx
            
        return None, -1

    def _find_innermost_covering(self, nodes, ref1, ref2, loader):
        for node in nodes:
            if self._is_ref_in_range(ref1, node["range"], loader) and \
               self._is_ref_in_range(ref2, node["range"], loader):
                # Found a covering node, check children
                inner = self._find_innermost_covering(node.get("children", []), ref1, ref2, loader)
                return inner if inner else node
        return None

    def _is_ref_in_range(self, ref, r, loader):
        return self._is_ref_equal_or_after(ref, r["start"], loader) and \
               self._is_ref_equal_or_before(ref, r["end"], loader)

    def _is_ref_equal_or_after(self, ref, target, loader):
        idx1 = loader.get_verse_index(ref)
        idx2 = loader.get_verse_index(target)
        return idx1 >= idx2 if idx1 != -1 and idx2 != -1 else False

    def _is_ref_equal_or_before(self, ref, target, loader):
        idx1 = loader.get_verse_index(ref)
        idx2 = loader.get_verse_index(target)
        return idx1 <= idx2 if idx1 != -1 and idx2 != -1 else False

    def _get_node_level(self, nodes, target_id, current_level=0):
        for node in nodes:
            if node["id"] == target_id: return current_level
            if "children" in node:
                lvl = self._get_node_level(node["children"], target_id, current_level + 1)
                if lvl != -1: return lvl
        return -1 # Return -1 if not found in this branch

    def get_node(self, node_id: str) -> Optional[Dict]:
        """Returns the node with the given ID."""
        return self._find_node_recursive(self.get_outlines(), node_id)

    def _find_node_recursive(self, nodes: List[Dict], target_id: str) -> Optional[Dict]:
        for node in nodes:
            if node["id"] == target_id:
                return node
            if "children" in node:
                found = self._find_node_recursive(node["children"], target_id)
                if found:
                    return found
        return None

    def get_all_split_indices(self, exclude_split_idx: Optional[float] = None) -> List[float]:
        """Returns a sorted list of all indices where a split exists across all outlines,
        optionally excluding a specific split index."""
        all_splits = set() # Use a set to avoid duplicates
        loader = self.study_manager.loader
        
        for outline in self.get_outlines():
            # End boundary of an outline: divider is after the end verse
            all_splits.add(loader.get_verse_index(outline["range"]["end"]))
            
            # Start boundary of an outline: divider is before the start verse
            start_idx = loader.get_verse_index(outline["range"]["start"])
            if start_idx >= 0.1: # If not at very start of Bible
                # A split 'at' index X means between X and X+1 (or X+0.1)
                # If start is index 10.0, the divider is at 9.0 (between 9 and 10)
                # Support sub-verse granularity: if start is 10.1, divider is at 10.0
                if int(start_idx) == start_idx:
                    all_splits.add(start_idx - 1.0)
                else:
                    all_splits.add(start_idx - 0.1)
            
            self._collect_split_indices_recursive(outline, all_splits)
        
        sorted_splits = sorted(list(all_splits))
        if exclude_split_idx is not None:
            return [s for s in sorted_splits if s != exclude_split_idx]
        return sorted_splits

    def _collect_split_indices_recursive(self, node: Dict, all_splits: set):
        if "children" in node and node["children"]:
            for i in range(len(node["children"]) - 1):
                # The split is between node["children"][i]["range"]["end"] and node["children"][i+1]["range"]["start"]
                # We'll use the index of the verse *before* the split (end of the first child)
                split_ref = node["children"][i]["range"]["end"]
                split_idx = self.study_manager.loader.get_verse_index(split_ref)
                if split_idx != -1.0:
                    all_splits.add(split_idx)
            for child in node["children"]:
                self._collect_split_indices_recursive(child, all_splits)

    def get_nearest_split_indices(self, current_split_idx: float) -> Tuple[Optional[float], Optional[float]]:
        """
        Returns the closest split index strictly less than current_split_idx (preceding)
        and the closest split index strictly greater than current_split_idx (succeeding).
        These represent the hard boundaries imposed by other divisions.
        """
        all_splits = self.get_all_split_indices(exclude_split_idx=current_split_idx)
        
        preceding = None
        succeeding = None
        
        for s_idx in all_splits:
            # Check for float precision with a small epsilon
            if s_idx < current_split_idx - 0.01:
                preceding = max(preceding, s_idx) if preceding is not None else s_idx
            elif s_idx > current_split_idx + 0.01:
                succeeding = min(succeeding, s_idx) if succeeding is not None else s_idx
        
        return preceding, succeeding

    def get_visible_dividers(self, visible_refs: set) -> List[Dict]:
        """
        Returns a list of divider lines to draw based on visible verses.
        Each divider: { "ref_after": str, "level": int, "type": "start"|"end"|"split" }
        This is a simplification; precise positioning requires more logic in ReaderScene.
        """
        dividers = []
        # TODO: Traversal logic to identify split points
        return dividers
