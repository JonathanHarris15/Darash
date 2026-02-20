import re
import os
import time
from typing import Dict, List, Optional

class StrongsManager:
    """
    Manages Strong's Concordance data: parsing the dictionary and indexing usages.
    """
    def __init__(self, xhtml_path: str = "strongs-dictionary.xhtml"):
        self.dictionary: Dict[str, Dict[str, str]] = {} # "H123": {word, translit, definition, lang}
        self.usages: Dict[str, List[str]] = {} # "H123": ["Genesis 1:1", ...]
        self._load_dictionary(xhtml_path)

    def _load_dictionary(self, path: str):
        if not os.path.exists(path):
            print(f"Warning: {path} not found.")
            return
        
        start_t = time.time()
        print(f"Parsing Strong's dictionary from {path}...")
        
        # Optimization: Use line-by-line parsing with regex for speed on large file
        # Pattern matches: <li value="430" id="ot:430"><i title="{aw-lo-heem'}" xml:lang="hbo">אֱלֹהִים</i> ...
        li_pattern = re.compile(r'<li value="(\d+)" id="(ot|nt):\d+">')
        i_pattern = re.compile(r'<i title="\{([^}]*)\}" xml:lang="([^"]*)">([^<]*)</i>')
        kjv_pattern = re.compile(r'<span class="kjv_def">([^<]*)</span>')
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    li_match = li_pattern.search(line)
                    if not li_match:
                        continue
                        
                    num_val = li_match.group(1)
                    test_type = li_match.group(2)
                    prefix = "H" if test_type == "ot" else "G"
                    key = f"{prefix}{num_val}"
                    
                    i_match = i_pattern.search(line)
                    if i_match:
                        translit, lang, word = i_match.groups()
                    else:
                        translit, lang, word = "", "", ""
                        
                    kjv_match = kjv_pattern.search(line)
                    kjv_def = kjv_match.group(1) if kjv_match else ""
                    
                    # Extract the full text description (everything between </i> and </li>, stripping the kjv_def span)
                    # We look for the start of the description after the </i> tag
                    parts = line.split('</i>')
                    if len(parts) > 1:
                        desc_part = parts[-1].split('</li>')[0]
                        # Remove the kjv_def span if it exists
                        if '<span' in desc_part:
                            desc_part = desc_part.split('<span')[0]
                        
                        # Clean up HTML tags (like <a href...>) using regex
                        desc_part = re.sub(r'<[^>]+>', '', desc_part)
                        
                        # Clean up leading punctuation and whitespace
                        desc_part = desc_part.strip().lstrip(';').lstrip(':').strip()
                    else:
                        desc_part = ""
                    
                    self.dictionary[key] = {
                        "word": word,
                        "translit": translit,
                        "lang": lang,
                        "description": desc_part.strip().lstrip(':').strip(),
                        "kjv_def": kjv_def
                    }
            print(f"Parsed {len(self.dictionary)} Strong's entries in {time.time() - start_t:.2f}s")
        except Exception as e:
            print(f"Error parsing Strong's dictionary: {e}")

    def index_usages(self, loader):
        """Indexes usages of Strongs numbers across all verses."""
        start_t = time.time()
        print("Indexing Strong's usages...")
        self.usages = {}
        for verse in loader.flat_verses:
            ref = verse['ref']
            for token in verse['tokens']:
                if len(token) > 1:
                    strongs_str = token[1]
                    # Strongs can be space-separated "H123 H456"
                    s_nums = strongs_str.split()
                    for sn in s_nums:
                        if sn not in self.usages:
                            self.usages[sn] = []
                        # Avoid duplicates in same verse if multiple words map to same sn
                        if not self.usages[sn] or self.usages[sn][-1] != ref:
                            self.usages[sn].append(ref)
        print(f"Indexed Strong's usages in {time.time() - start_t:.2f}s")

    def get_entry(self, sn: str) -> Optional[Dict[str, str]]:
        return self.dictionary.get(sn)

    def get_usages(self, sn: str) -> List[str]:
        return self.usages.get(sn, [])
