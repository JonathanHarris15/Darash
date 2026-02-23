import json
import os
from typing import Dict, List, Any, Optional
# Delayed import to avoid circular dependency if OutlineManager imports StudyManager for typing
# from src.outline_manager import OutlineManager

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
            "settings": {},   # Persistent appearance settings
            "outlines": []  # List of outline trees {id, title, range, children}
        }

    def __init__(self, loader=None, base_dir: str = "studies"):
        self.base_dir = base_dir
        self.loader = loader
        self.config_path = os.path.join(self.base_dir, "config.json")
        self.current_study_name = None
        self.data = self._get_default_data()
        self.undo_stack = [] # Stack of (symbols_dict, marks_list, arrows_dict) snapshots
        
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)
            
        last_study = self._load_last_study_name()
        self.load_study(last_study)
        
        # Initialize managers
        from src.outline_manager import OutlineManager
        self.outline_manager = OutlineManager(self)

    def _load_last_study_name(self) -> str:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get("last_study", "default_study")
            except:
                pass
        return "default_study"

    def _save_last_study_name(self, name: str):
        config = {"last_study": name}
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

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
        self._save_last_study_name(name)
        study_path = os.path.join(self.base_dir, name, "study.json")
        
        default_data = self._get_default_data()
        
        if os.path.exists(study_path):
            try:
                with open(study_path, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                
                # Merge loaded data into default data to ensure all keys exist
                self.data = default_data
                self.data.update(loaded_data)
                
                # Ensure nested keys are also initialized if they were somehow missing
                for key, default_val in default_data.items():
                    if key not in self.data:
                        self.data[key] = default_val
                        
                print(f"Loaded study: {name}")
            except Exception as e:
                print(f"Error loading study {name}: {e}")
                self.data = default_data
        else:
            self.data = default_data
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

    def set_verse_indent(self, ref: str, indent_level: int):
        self.data["verse_indent"][ref] = indent_level
        self.save_study()

    def set_verse_mark(self, ref: str, mark_type: str):
        if mark_type:
            self.data["verse_marks"][ref] = mark_type
        elif ref in self.data["verse_marks"]:
            del self.data["verse_marks"][ref]
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
        self.save_study()

    def add_logical_mark(self, key: str, mark_type: str):
        self.save_state()
        self.data["logical_marks"][key] = mark_type
        self.save_study()
