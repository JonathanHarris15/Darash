import json
import os
from typing import Dict, List, Any, Optional
from src.utils.path_utils import get_user_data_path

class StudyManager:
    """
    Manages study files (symbols, marks, notes).
    Saves and loads data from JSON and manages associated symbol images.
    """
    def _get_default_data(self):
        return {
            "symbols": {}, # (book, chap, verse, word_idx): symbol_id
            "marks": [],   # List of mark dicts {type, range: (start_ref, end_ref), color}
            "notes": {},    # key: {"title": title, "text": markdown_text, "folder": "path"}
            "note_folders": [], # List of folder paths
            "bookmarks": [], # List of {ref, color, book, chapter, verse}
            "arrows": {},    # start_key: [{"end_dx": float, "end_dy": float, "color": str}]
            "verse_indent": {}, # ref: indent_level
            "verse_marks": {},  # ref: mark_type
            "logical_marks": {}, # key (book|chap|verse|word_idx): mark_type (e.g. "arrow_right")
            "settings": {
                "sentence_break_enabled": False,
                "primary_translation": "ESV",
                "enabled_interlinear": []
            },   # Persistent appearance settings
            "outlines": []  # List of outline trees {id, title, range, children}
        }

    def __init__(self, loader=None, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = get_user_data_path("study_data")
        self.base_dir = base_dir
        self.loader = loader
        self.data = self._get_default_data()
        self.undo_stack = [] # Stack of (symbols_dict, marks_list, arrows_dict) snapshots
        self.study_file_path = os.path.join(self.base_dir, "study.json")
        self.symbols_dir = os.path.join(self.base_dir, "symbols")
        
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)
        if not os.path.exists(self.symbols_dir):
            os.makedirs(self.symbols_dir)
            
        self.load_data()
        
        # Initialize managers
        from src.managers.outline_manager import OutlineManager
        self.outline_manager = OutlineManager(self)

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
        self.save_data()
        return True

    def load_data(self):
        default_data = self._get_default_data()
        
        if os.path.exists(self.study_file_path):
            try:
                with open(self.study_file_path, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                
                # Merge loaded data into default data to ensure all keys exist
                self.data = default_data
                self.data.update(loaded_data)
                
                # Ensure nested keys are also initialized if they were somehow missing
                for key, default_val in default_data.items():
                    if key not in self.data:
                        self.data[key] = default_val
                        
            except Exception as e:
                print(f"Error loading study data: {e}")
                self.data = default_data
        else:
            self.data = default_data
            self.save_data()

    def save_data(self):
        with open(self.study_file_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4)

    def add_symbol(self, book: str, chap: str, verse: str, word_idx: int, symbol_id: str):
        self.save_state()
        key = f"{book}|{chap}|{verse}|{word_idx}"
        self.data["symbols"][key] = symbol_id
        self.save_data()

    def add_note(self, book: str, chap: str, verse: str, word_idx: int, note_text: str, title: str = ""):
        key = f"{book}|{chap}|{verse}|{word_idx}"
        # Preserve existing folder if updating
        existing_folder = self.data["notes"].get(key, {}).get("folder", "")
        self.data["notes"][key] = {"title": title, "text": note_text, "folder": existing_folder}
        self.save_data()

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
        self.save_data()
        return key

    def delete_note(self, note_key: str):
        if note_key in self.data["notes"]:
            del self.data["notes"][note_key]
            self.save_data()

    def add_folder(self, path: str):
        if path not in self.data["note_folders"]:
            self.data["note_folders"].append(path)
            self.save_data()

    def move_note(self, note_key: str, folder_path: str):
        if note_key in self.data["notes"]:
            self.data["notes"][note_key]["folder"] = folder_path
            self.save_data()
            
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
                
        self.save_data()
            
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
                
        self.save_data()

    def add_mark(self, mark_data: Dict[str, Any]):
        self.save_state()
        self.data["marks"].append(mark_data)
        self.save_data()

    def set_verse_indent(self, ref: str, indent_level: int):
        self.data["verse_indent"][ref] = indent_level
        self.save_data()

    def set_verse_mark(self, ref: str, mark_type: str):
        if mark_type:
            self.data["verse_marks"][ref] = mark_type
        elif ref in self.data["verse_marks"]:
            del self.data["verse_marks"][ref]
        self.save_data()

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
        self.save_data()

    def delete_bookmark(self, ref: str):
        self.data["bookmarks"] = [b for b in self.data["bookmarks"] if b['ref'] != ref]
        self.save_data()

    def update_bookmark_color(self, ref: str, color: str):
        for b in self.data["bookmarks"]:
            if b['ref'] == ref:
                b['color'] = color
                break
        self.save_data()

    def update_bookmark_title(self, ref: str, title: str):
        for b in self.data["bookmarks"]:
            if b['ref'] == ref:
                b['title'] = title
                break
        self.save_data()

    def add_arrow(self, start_key: str, end_key: str, color: str = "#00FFFF", arrow_type: str = "straight"):
        if not start_key or start_key == "null":
            return
        self.save_state()
        if start_key not in self.data["arrows"]:
            self.data["arrows"][start_key] = []
        self.data["arrows"][start_key].append({
            "end_key": end_key,
            "color": color,
            "type": arrow_type
        })
        self.save_data()

    def add_logical_mark(self, key: str, mark_type: str):
        self.save_state()
        self.data["logical_marks"][key] = mark_type
        self.save_data()
