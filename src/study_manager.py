import json
import os
from typing import Dict, List, Any, Optional

class StudyManager:
    """
    Manages study files (symbols, marks, notes).
    Saves and loads data from JSON and manages associated symbol images.
    """
    def __init__(self, base_dir: str = "studies"):
        self.base_dir = base_dir
        self.current_study_name = None
        self.data = {
            "symbols": {}, # (book, chap, verse, word_idx): symbol_id
            "marks": [],   # List of mark dicts {type, range: (start_ref, end_ref), color}
            "notes": {},    # (book, chap, verse, word_idx): markdown_text
            "bookmarks": [], # List of {ref, color, book, chapter, verse}
            "arrows": {}    # start_key: [{"end_dx": float, "end_dy": float, "color": str}]
        }
        self.undo_stack = [] # Stack of (symbols_dict, marks_list, arrows_dict) snapshots
        
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)
            
        self.load_study("default_study")

    def save_state(self):
        """Saves current marks, symbols, and arrows to undo stack."""
        import copy
        snapshot = (
            copy.deepcopy(self.data["symbols"]), 
            copy.deepcopy(self.data["marks"]),
            copy.deepcopy(self.data["arrows"])
        )
        self.undo_stack.append(snapshot)
        if len(self.undo_stack) > 50: # Limit history
            self.undo_stack.pop(0)

    def undo(self):
        """Restores the previous state of marks, symbols, and arrows."""
        if not self.undo_stack:
            return False
        symbols, marks, arrows = self.undo_stack.pop()
        self.data["symbols"] = symbols
        self.data["marks"] = marks
        self.data["arrows"] = arrows
        self.save_study()
        return True

    def load_study(self, name: str):
        self.current_study_name = name
        study_path = os.path.join(self.base_dir, name, "study.json")
        
        if os.path.exists(study_path):
            with open(study_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            if "bookmarks" not in self.data:
                self.data["bookmarks"] = []
            if "arrows" not in self.data:
                self.data["arrows"] = {}
        else:
            self.data = {"symbols": {}, "marks": [], "notes": {}, "bookmarks": [], "arrows": {}}
            self.save_study()

    def save_study(self):
        if not self.current_study_name:
            return
            
        study_dir = os.path.join(self.base_dir, self.current_study_name)
        if not os.path.exists(study_dir):
            os.makedirs(study_dir)
            os.makedirs(os.path.join(study_dir, "symbols"))

        study_path = os.path.join(study_dir, "study.json")
        with open(study_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4)

    def add_symbol(self, book: str, chap: str, verse: str, word_idx: int, symbol_id: str):
        self.save_state()
        key = f"{book}|{chap}|{verse}|{word_idx}"
        self.data["symbols"][key] = symbol_id
        self.save_study()

    def add_note(self, book: str, chap: str, verse: str, word_idx: int, note_text: str):
        key = f"{book}|{chap}|{verse}|{word_idx}"
        self.data["notes"][key] = note_text
        self.save_study()

    def delete_note(self, note_key: str):
        if note_key in self.data["notes"]:
            del self.data["notes"][note_key]
            self.save_study()

    def add_mark(self, mark_data: Dict[str, Any]):
        self.save_state()
        self.data["marks"].append(mark_data)
        self.save_study()

    def add_bookmark(self, book: str, chap: str, verse: str, color: str = "#0078D7"):
        ref = f"{book} {chap}:{verse}"
        if any(b['ref'] == ref for b in self.data["bookmarks"]):
            return
        self.data["bookmarks"].append({
            "ref": ref,
            "book": book,
            "chapter": chap,
            "verse": verse,
            "color": color,
            "title": ""
        })
        self.save_study()

    def delete_bookmark(self, ref: str):
        self.data["bookmarks"] = [b for b in self.data["bookmarks"] if b['ref'] != ref]
        self.save_study()

    def update_bookmark_color(self, ref: str, color: str):
        for b in self.data["bookmarks"]:
            if b['ref'] == ref:
                b['color'] = color
                break
        self.save_study()

    def update_bookmark_title(self, ref: str, title: str):
        for b in self.data["bookmarks"]:
            if b['ref'] == ref:
                b['title'] = title
                break
        self.save_study()

    def add_arrow(self, start_key: str, end_dx: float, end_dy: float, color: str = "#00FFFF"):
        self.save_state()
        if start_key not in self.data["arrows"]:
            self.data["arrows"][start_key] = []
        self.data["arrows"][start_key].append({
            "end_dx": end_dx,
            "end_dy": end_dy,
            "color": color
        })
        self.save_study()
