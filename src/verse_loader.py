import json
import os
from typing import Dict, List, Optional, Tuple, Any
from src.constants import OT_BOOKS, NT_BOOKS

class VerseLoader:
    """
    Handles loading and parsing of Bible data from JSON files.
    Provides methods for structured and flat access to verses.
    """
    def __init__(self, json_path: Optional[str] = None):
        if json_path is None:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            json_path = os.path.join(base_path, "mdbible-main", "mdbible-main", "json", "ESV.json")
        
        self.data: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self.flat_verses: List[Dict[str, Any]] = []
        self.ref_map: Dict[str, Dict[str, Any]] = {}
        self._load_data(json_path)

    def _load_data(self, path: str) -> None:
        try:
            print(f"Loading Bible data from {path}...")
            import time
            start_t = time.time()
            with open(path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            print(f"Parsing JSON data...")
            books_data = raw_data.get('books', {})
            
            for book_name, chapters in books_data.items():
                self.data[book_name] = {}
                for chap_idx, verses in enumerate(chapters):
                    chap_num = str(chap_idx + 1)
                    self.data[book_name][chap_num] = {}
                    for v_idx, raw_tokens in enumerate(verses):
                        v_num = str(v_idx + 1)
                        
                        # Split multi-word tokens (e.g., ["In the"] -> ["In"], ["the"])
                        # to ensure precise word-level indexing and centering.
                        tokens = []
                        for rt in raw_tokens:
                            words = rt[0].split()
                            if not words: # Handle edge case of empty strings
                                tokens.append(rt)
                                continue
                            if len(words) > 1:
                                for w in words:
                                    # Copy extra data (Strongs, etc) to each split word
                                    tokens.append([w] + rt[1:])
                            else:
                                tokens.append(rt)
                        
                        verse_text = " ".join(token[0] for token in tokens)
                        for char in [",", ".", ";", ":", "?", "!"]:
                            verse_text = verse_text.replace(f" {char}", char)
                        
                        verse_entry = {
                            'ref': f"{book_name} {chap_num}:{v_num}",
                            'book': book_name,
                            'chapter': chap_num,
                            'verse_num': v_num,
                            'text': verse_text,
                            'tokens': tokens 
                        }
                        
                        self.data[book_name][chap_num][v_num] = verse_entry
                        self.flat_verses.append(verse_entry)
                        self.ref_map[verse_entry['ref']] = verse_entry
            print(f"Loaded {len(self.flat_verses)} verses in {time.time() - start_t:.2f}s")
        except Exception as e:
            print(f"Error loading Bible data: {e}")

    def get_verse_by_ref(self, ref: str) -> Optional[Dict[str, Any]]:
        return self.ref_map.get(ref)

    def get_verse(self, book: str, chapter: int, verse: int) -> Optional[Dict[str, Any]]:
        try:
            return self.data[book][str(chapter)][str(verse)]
        except KeyError:
            return None

    def get_structure(self) -> Dict[str, Dict[str, List[int]]]:
        structure = {"Old Testament": {}, "New Testament": {}}
        for book_name in self.data.keys():
            testament = "Old Testament" if book_name in OT_BOOKS else "New Testament"
            chapters = sorted([int(c) for c in self.data[book_name].keys()])
            structure[testament][book_name] = chapters
        return structure
