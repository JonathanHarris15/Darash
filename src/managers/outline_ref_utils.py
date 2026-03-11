import re

class OutlineRefUtils:
    """Utilities for handling Bible references and indices in outlines."""
    
    @staticmethod
    def calculate_range_split(start_ref, end_ref, loader):
        if not loader: return None, None
        
        m_s = re.match(r"(.* \d+:\d+)([a-zA-Z]+)?", start_ref)
        m_e = re.match(r"(.* \d+:\d+)([a-zA-Z]+)?", end_ref)
        
        if not m_s or not m_e: return None, None
        
        s_base = m_s.group(1)
        e_base = m_e.group(1)
        
        if m_s.group(2) or m_e.group(2): return None, None
        
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

    @staticmethod
    def shift_ref_by_verses(ref, delta, loader):
        if delta == 0 or not ref: return ref
        m = re.match(r"(.* \d+:\d+)([a-zA-Z]+)?$", ref)
        if not m: return ref
        base_ref = m.group(1)
        
        idx = loader.get_verse_index(base_ref)
        if idx == -1.0: return ref
        
        new_idx = int(idx) + delta
        new_idx = max(0, min(new_idx, len(loader.flat_verses) - 1))
        
        return loader.flat_verses[new_idx]['ref']

    @staticmethod
    def shift_ref_by_words(ref, delta, loader):
        if delta == 0 or not ref: return ref
        m = re.match(r"(.* \d+:\d+)([a-zA-Z]+)?$", ref)
        if not m: return ref
        base_ref = m.group(1)
        letters = m.group(2)
        
        idx = loader.get_verse_index(base_ref)
        if idx == -1.0: return ref
        v_idx = int(idx)
        
        word_idx = loader.letters_to_word_idx(letters) if letters else 0
        
        while delta != 0:
            v_data = loader.flat_verses[v_idx]
            max_words = len(v_data['tokens'])
            if delta > 0:
                if word_idx + delta < max_words:
                    word_idx += delta
                    delta = 0
                else:
                    delta -= (max_words - word_idx)
                    if v_idx < len(loader.flat_verses) - 1:
                        v_idx += 1
                        word_idx = 0
                    else:
                        word_idx = max_words - 1
                        delta = 0
            else:
                if word_idx + delta >= 0:
                    word_idx += delta
                    delta = 0
                else:
                    delta += (word_idx + 1)
                    if v_idx > 0:
                        v_idx -= 1
                        word_idx = len(loader.flat_verses[v_idx]['tokens']) - 1
                    else:
                        word_idx = 0
                        delta = 0
        return loader.flat_verses[v_idx]['ref'] + loader.word_idx_to_letters(word_idx)

    @staticmethod
    def is_ref_in_range(ref, r, loader):
        idx1 = loader.get_verse_index(ref)
        idx_s = loader.get_verse_index(r["start"])
        idx_e = loader.get_verse_index(r["end"])
        return idx1 >= idx_s and idx1 <= idx_e if idx1 != -1 and idx_s != -1 and idx_e != -1 else False

    @staticmethod
    def is_ref_equal_or_after(ref, target, loader):
        idx1 = loader.get_verse_index(ref)
        idx2 = loader.get_verse_index(target)
        return idx1 >= idx2 if idx1 != -1 and idx2 != -1 else False

    @staticmethod
    def is_ref_equal_or_before(ref, target, loader):
        idx1 = loader.get_verse_index(ref)
        idx2 = loader.get_verse_index(target)
        return idx1 <= idx2 if idx1 != -1 and idx2 != -1 else False
