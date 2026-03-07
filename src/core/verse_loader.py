import json
import os
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple, Any
from src.core.constants import OT_BOOKS, NT_BOOKS

class VerseLoader:
    """
    Handles loading and parsing of Bible data from JSON and XML files.
    Provides methods for structured, flat, and multi-translation access to verses.
    """
    def __init__(self, json_path: Optional[str] = None):
        # Base path for relative data lookups
        self.base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        if json_path is None:
            json_path = os.path.join(self.base_path, "data", "mdbible-main", "mdbible-main", "json", "ESV.json")
        
        self.primary_translation = "ESV" # Default
        self.data: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self.flat_verses: List[Dict[str, Any]] = []
        self.ref_map: Dict[str, Dict[str, Any]] = {}
        self.ref_to_idx: Dict[str, int] = {}
        
        # Cache for other translations loaded on demand: {translation_id: {book: {chapter: {verse: data}}}}
        self.translation_cache: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]] = {}
        
        self._load_data(json_path)

    def _load_data(self, path: str) -> None:
        try:
            print(f"Loading Primary Bible data from {path}...")
            import time
            start_t = time.time()
            with open(path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            self.primary_translation = raw_data.get('version', 'ESV')
            print(f"Parsing {self.primary_translation} JSON data...")
            books_data = raw_data.get('books', {})
            
            for book_name, chapters in books_data.items():
                self.data[book_name] = {}
                for chap_idx, verses in enumerate(chapters):
                    chap_num = str(chap_idx + 1)
                    self.data[book_name][chap_num] = {}
                    for v_idx, raw_tokens in enumerate(verses):
                        v_num = str(v_idx + 1)
                        
                        tokens = self._tokenize_raw(raw_tokens)
                        verse_text = self._tokens_to_text(tokens)
                        
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
                        self.ref_to_idx[verse_entry['ref']] = len(self.flat_verses) - 1
            
            # Store primary in cache too for uniform access
            self.translation_cache[self.primary_translation] = self.data
            
            print(f"Loaded {len(self.flat_verses)} verses in {time.time() - start_t:.2f}s")
        except Exception as e:
            print(f"Error loading Bible data: {e}")

    def _tokenize_raw(self, raw_tokens: List[Any]) -> List[List[str]]:
        """Split multi-word tokens (e.g., ["In the"] -> ["In"], ["the"]) for precise indexing."""
        tokens = []
        for rt in raw_tokens:
            if not isinstance(rt, list) or not rt:
                continue
            words = rt[0].split()
            if not words:
                tokens.append(rt)
                continue
            if len(words) > 1:
                for w in words:
                    tokens.append([w] + rt[1:])
            else:
                tokens.append(rt)
        return tokens

    def _tokens_to_text(self, tokens: List[List[str]]) -> str:
        text = " ".join(token[0] for token in tokens)
        for char in [",", ".", ";", ":", "?", "!"]:
            text = text.replace(f" {char}", char)
        return text

    def load_translation(self, translation_id: str) -> bool:
        """Loads a translation into the cache if not already present."""
        if translation_id in self.translation_cache:
            return True
        
        # 1. Check for XML in data/BibleTranslations
        xml_path = os.path.join(self.base_path, "data", "BibleTranslations", "bible-master", "bible-master", "bible", "translations", f"{translation_id}.xml")
        if os.path.exists(xml_path):
            return self._load_xml_translation(translation_id, xml_path)
            
        # 2. Check for JSON in the same dir as ESV (if it's not ESV)
        # (Assuming other translations might be JSON as well)
        json_path = os.path.join(self.base_path, "data", "mdbible-main", "mdbible-main", "json", f"{translation_id}.json")
        if os.path.exists(json_path):
            # We don't want to overwrite self.data (primary index), just load into cache
            return self._load_json_to_cache(translation_id, json_path)
            
        return False

    def _load_xml_translation(self, trans_id: str, path: str) -> bool:
        try:
            print(f"Loading XML Translation: {trans_id} from {path}")
            tree = ET.parse(path)
            root = tree.getroot()
            
            trans_data = {}
            for book_elem in root.findall('b'):
                book_name = book_elem.get('n')
                trans_data[book_name] = {}
                for chap_elem in book_elem.findall('c'):
                    chap_num = chap_elem.get('n')
                    trans_data[book_name][chap_num] = {}
                    for v_elem in chap_elem.findall('v'):
                        v_num = v_elem.get('n')
                        text = v_elem.text if v_elem.text else ""
                        # XML is usually just plain text, so we mock tokens
                        tokens = [[w] for w in text.split()]
                        trans_data[book_name][chap_num][v_num] = {
                            'ref': f"{book_name} {chap_num}:{v_num}",
                            'book': book_name,
                            'chapter': chap_num,
                            'verse_num': v_num,
                            'text': text,
                            'tokens': tokens
                        }
            
            self.translation_cache[trans_id] = trans_data
            return True
        except Exception as e:
            print(f"Error loading XML {trans_id}: {e}")
            return False

    def _load_json_to_cache(self, trans_id: str, path: str) -> bool:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            trans_data = {}
            books_data = raw_data.get('books', {})
            for book_name, chapters in books_data.items():
                trans_data[book_name] = {}
                for chap_idx, verses in enumerate(chapters):
                    chap_num = str(chap_idx + 1)
                    trans_data[book_name][chap_num] = {}
                    for v_idx, raw_tokens in enumerate(verses):
                        v_num = str(v_idx + 1)
                        tokens = self._tokenize_raw(raw_tokens)
                        text = self._tokens_to_text(tokens)
                        trans_data[book_name][chap_num][v_num] = {
                            'ref': f"{book_name} {chap_num}:{v_num}",
                            'book': book_name,
                            'chapter': chap_num,
                            'verse_num': v_num,
                            'text': text,
                            'tokens': tokens
                        }
            self.translation_cache[trans_id] = trans_data
            return True
        except Exception as e:
            print(f"Error loading JSON cache {trans_id}: {e}")
            return False

    def load_chapter_multi(self, book: str, chapter: int, translations: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Returns a map of {verse_num: {translation_id: verse_data}} for a specific chapter.
        Ensures all requested translations are loaded into cache first.
        """
        chap_str = str(chapter)
        results = {}
        
        # 1. Ensure all translations are available
        available_trans = []
        for tid in translations:
            if self.load_translation(tid):
                available_trans.append(tid)
        
        if not available_trans:
            return {}
            
        # 2. Aggregate by verse number
        # We use the first requested translation to define which verses exist in the result set
        primary_req = available_trans[0]
        
        book_data = self.translation_cache[primary_req].get(book, {})
        chap_data = book_data.get(chap_str, {})
        
        for v_num in chap_data.keys():
            results[v_num] = {}
            for tid in available_trans:
                try:
                    results[v_num][tid] = self.translation_cache[tid][book][chap_str][v_num]
                except KeyError:
                    # Verse might be missing in this translation
                    results[v_num][tid] = None
                    
        return results

    def get_available_translations(self) -> List[str]:
        """Scans filesystem for available XML and JSON translations."""
        found = set()
        if self.primary_translation:
            found.add(self.primary_translation)
            
        # 1. XML translations
        xml_dir = os.path.join(self.base_path, "data", "BibleTranslations", "bible-master", "bible-master", "bible", "translations")
        if os.path.exists(xml_dir):
            for f in os.listdir(xml_dir):
                if f.endswith(".xml"):
                    found.add(f[:-4])
                    
        # 2. JSON translations
        json_dir = os.path.join(self.base_path, "data", "mdbible-main", "mdbible-main", "json")
        if os.path.exists(json_dir):
            for f in os.listdir(json_dir):
                if f.endswith(".json"):
                    found.add(f[:-5])
                    
        return sorted(list(found))

    def get_verse_by_ref(self, ref: str) -> Optional[Dict[str, Any]]:
        return self.ref_map.get(ref)

    @staticmethod
    def word_idx_to_letters(idx: int) -> str:
        """Converts a 0-based word index to a base-26 letter string (0->a, 25->z, 26->aa)."""
        idx += 1
        letters = ""
        while idx > 0:
            idx, rem = divmod(idx - 1, 26)
            letters = chr(ord('a') + rem) + letters
        return letters

    @staticmethod
    def letters_to_word_idx(letters: str) -> int:
        """Converts a base-26 letter string to a 0-based word index ('a'->0, 'z'->25, 'aa'->26)."""
        val = 0
        for char in letters.lower():
            val = val * 26 + (ord(char) - ord('a') + 1)
        return val - 1

    def get_verse_index(self, ref: str) -> float:
        if not ref: return -1.0
        
        import re
        base_ref = ref
        suffix_val = 0.0
        
        # Support suffixes like 'a', 'b', 'c', 'aa', etc. (mid-verse word divisions)
        m = re.match(r"(.* \d+:\d+)([a-zA-Z]+)?$", ref)
        if m:
            base_ref = m.group(1)
            if m.group(2):
                word_idx = self.letters_to_word_idx(m.group(2))
                suffix_val = (word_idx + 1) / 1000.0
            
        idx = self.ref_to_idx.get(base_ref, -1)
        if idx == -1: return -1.0
        return float(idx) + suffix_val

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
