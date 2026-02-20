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
            "notes": {},    # key: {"title": title, "text": markdown_text, "folder": "path"}
            "note_folders": [], # List of folder paths
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
            try:
                with open(study_path, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                if "bookmarks" not in self.data:
                    self.data["bookmarks"] = []
                if "arrows" not in self.data:
                    self.data["arrows"] = {}
                if "note_folders" not in self.data:
                    self.data["note_folders"] = []
                print(f"Loaded study: {name}")
            except Exception as e:
                print(f"Error loading study {name}: {e}")
                self.data = {"symbols": {}, "marks": [], "notes": {}, "note_folders": [], "bookmarks": [], "arrows": {}}
        else:
            self.data = {"symbols": {}, "marks": [], "notes": {}, "note_folders": [], "bookmarks": [], "arrows": {}}
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

    def add_note(self, book: str, chap: str, verse: str, word_idx: int, note_text: str, title: str = ""):
        key = f"{book}|{chap}|{verse}|{word_idx}"
        # Preserve existing folder if updating
        existing_folder = self.data["notes"].get(key, {}).get("folder", "")
        self.data["notes"][key] = {"title": title, "text": note_text, "folder": existing_folder}
        self.save_study()

    def add_standalone_note(self, title: str = "", text: str = "", folder: str = ""):
        import time
        key = f"standalone_{int(time.time() * 1000)}"
        
        if not title:
            # Count existing standalone notes to find the next number
            count = 1
            for k, v in self.data["notes"].items():
                if k.startswith("standalone_"):
                    # Check if it has a title like "New Note 5"
                    t = v.get("title", "")
                    if t.startswith("New Note "):
                        try:
                            num = int(t.replace("New Note ", ""))
                            if num >= count: count = num + 1
                        except: pass
            title = f"New Note {count}"
            
        self.data["notes"][key] = {"title": title, "text": text, "folder": folder}
        self.save_study()
        return key

    def delete_note(self, note_key: str):
        if note_key in self.data["notes"]:
            del self.data["notes"][note_key]
            self.save_study()

    def add_folder(self, path: str):
        if path not in self.data["note_folders"]:
            self.data["note_folders"].append(path)
            self.save_study()

    def move_note(self, note_key: str, folder_path: str):
        if note_key in self.data["notes"]:
            self.data["notes"][note_key]["folder"] = folder_path
            self.save_study()
            
    def move_folder(self, source_path: str, target_parent_path: str):
        if source_path == target_parent_path or target_parent_path.startswith(f"{source_path}/"):
            return # Cannot move into self or sub-folder
            
        source_name = source_path.split("/")[-1]
        new_path = f"{target_parent_path}/{source_name}" if target_parent_path else source_name
        
        if new_path == source_path: return
        
        # 1. Update the folder itself and all sub-folders
        new_folders = []
        for f in self.data["note_folders"]:
            if f == source_path:
                new_folders.append(new_path)
            elif f.startswith(f"{source_path}/"):
                new_folders.append(f.replace(source_path, new_path, 1))
            else:
                new_folders.append(f)
        self.data["note_folders"] = new_folders
        
        # 2. Update all notes in these folders
        for key, note_data in self.data["notes"].items():
            f = note_data.get("folder", "")
            if f == source_path:
                note_data["folder"] = new_path
            elif f.startswith(f"{source_path}/"):
                note_data["folder"] = f.replace(source_path, new_path, 1)
                
        self.save_study()
            
    def delete_folder(self, folder_path: str):
        # 1. Collect all folder paths to be removed (this folder and all sub-folders)
        paths_to_remove = [folder_path]
        for f in self.data["note_folders"]:
            if f.startswith(f"{folder_path}/"):
                paths_to_remove.append(f)
        
        # 2. Remove the folders from the list
        self.data["note_folders"] = [f for f in self.data["note_folders"] if f not in paths_to_remove]
            
        # 3. Delete all notes that were in any of these folders
        keys_to_delete = []
        for key, note_data in self.data["notes"].items():
            f = note_data.get("folder", "")
            if f in paths_to_remove:
                keys_to_delete.append(key)
        
        for k in keys_to_delete:
            del self.data["notes"][k]
                
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

    def add_arrow(self, start_key: str, end_key: str, color: str = "#00FFFF"):
        self.save_state()
        if start_key not in self.data["arrows"]:
            self.data["arrows"][start_key] = []
        self.data["arrows"][start_key].append({
            "end_key": end_key,
            "color": color
        })
        self.save_study()
