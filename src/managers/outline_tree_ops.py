import uuid
from typing import List, Dict, Optional, Tuple
from src.managers.outline_ref_utils import OutlineRefUtils

class OutlineTreeOps:
    """Operations for manipulating the outline tree hierarchy."""

    @staticmethod
    def get_node(nodes: List[Dict], node_id: str) -> Optional[Dict]:
        for node in nodes:
            if node["id"] == node_id:
                return node
            if "children" in node:
                found = OutlineTreeOps.get_node(node["children"], node_id)
                if found:
                    return found
        return None

    @staticmethod
    def find_parent_and_index(nodes: List[Dict], target_id: str) -> Tuple[Optional[Dict], int]:
        for node in nodes:
            children = node.get("children", [])
            for i, child in enumerate(children):
                if child["id"] == target_id:
                    return node, i
                p, idx = OutlineTreeOps.find_parent_and_index([child], target_id)
                if p: return p, idx
        return None, -1

    @staticmethod
    def delete_node_recursive(nodes: List[Dict], target_id: str) -> bool:
        for node in nodes:
            if "children" in node:
                for i, child in enumerate(node["children"]):
                    if child["id"] == target_id:
                        node["children"].pop(i)
                        return True
                    if OutlineTreeOps.delete_node_recursive(node["children"], target_id):
                        return True
        return False

    @staticmethod
    def get_node_level(nodes: List[Dict], target_id: str, current_level=0) -> int:
        for node in nodes:
            if node["id"] == target_id: return current_level
            if "children" in node:
                lvl = OutlineTreeOps.get_node_level(node["children"], target_id, current_level + 1)
                if lvl != -1: return lvl
        return -1

    @staticmethod
    def find_innermost_covering(nodes, ref1, ref2, loader):
        for node in nodes:
            if OutlineRefUtils.is_ref_in_range(ref1, node["range"], loader) and \
               OutlineRefUtils.is_ref_in_range(ref2, node["range"], loader):
                inner = OutlineTreeOps.find_innermost_covering(node.get("children", []), ref1, ref2, loader)
                return inner if inner else node
        return None

    @staticmethod
    def find_node_with_split(nodes, ref1, ref2, loader):
        for node in nodes:
            children = node.get("children", [])
            for i in range(len(children) - 1):
                if children[i]["range"]["end"] == ref1 and children[i+1]["range"]["start"] == ref2:
                    return node, i
            found_node, found_idx = OutlineTreeOps.find_node_with_split(children, ref1, ref2, loader)
            if found_node: return found_node, found_idx
        return None, -1

    @staticmethod
    def propagate_start_change(node: Dict, new_start: str):
        if "children" in node and node["children"]:
            first_child = node["children"][0]
            first_child["range"]["start"] = new_start
            OutlineTreeOps.propagate_start_change(first_child, new_start)

    @staticmethod
    def propagate_end_change(node: Dict, new_end: str):
        if "children" in node and node["children"]:
            last_child = node["children"][-1]
            last_child["range"]["end"] = new_end
            OutlineTreeOps.propagate_end_change(last_child, new_end)
