import bisect
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QTextCursor

def get_ref_from_pos(pos, pos_verse_map):
    """Finds the verse reference corresponding to a document position."""
    if not pos_verse_map: return None
    idx = bisect.bisect_right(pos_verse_map, (pos, "zzzzzz")) - 1
    return pos_verse_map[idx][1] if idx >= 0 else None

def get_word_idx_from_pos(verse_data, pos):
    """Finds the word index within a verse for a given document position."""
    if verse_data is None: return -1
    
    if pos < 0: return -1
    
    text = verse_data['text']
    search_pos = 0
    for i, token in enumerate(verse_data['tokens']):
        token_text = token[0]
        # Use find with search_pos to handle multiple occurrences of the same word
        start = text.find(token_text, search_pos)
        if start != -1:
            end = start + len(token_text)
            if start <= pos <= end:
                return i
            search_pos = end
    return -1

def get_text_rects(text_item, start, length):
    """Calculates the bounding rectangles for a range of text in the scene."""
    doc = text_item.document()
    rects = []
    block = doc.findBlock(start)
    while block.isValid() and block.position() < start + length:
        block_pos = block.position()
        rel_start = max(0, start - block_pos)
        rel_end = min(block.length(), start + length - block_pos)
        if rel_start < rel_end:
            layout = block.layout()
            for i in range(layout.lineCount()):
                line = layout.lineAt(i)
                l_start, l_end = line.textStart(), line.textStart() + line.textLength()
                i_start, i_end = max(rel_start, l_start), min(rel_end, l_end)
                if i_start < i_end:
                    x1, _ = line.cursorToX(i_start)
                    x2, _ = line.cursorToX(i_end)
                    line_rect = line.rect()
                    rect = QRectF(min(x1, x2) + layout.position().x(), 
                                  line_rect.top() + layout.position().y(), 
                                  abs(x2 - x1), line_rect.height())
                    rect.translate(text_item.pos())
                    # Adjust slightly to fit highlighting/underlining better
                    rects.append(rect.adjusted(0, 2, 0, -2))
        block = block.next()
    return rects

def get_word_offset_in_verse(verse_data, word_idx):
    """Calculates the character offset of a word within a verse block."""
    text = verse_data['text']
    pos = 0
    for i in range(word_idx):
        token_text = verse_data['tokens'][i][0]
        found_pos = text.find(token_text, pos)
        if found_pos != -1:
            pos = found_pos + len(token_text)
    
    target_token = verse_data['tokens'][word_idx][0]
    actual_start = text.find(target_token, pos)
    if actual_start == -1: return pos
    return actual_start
