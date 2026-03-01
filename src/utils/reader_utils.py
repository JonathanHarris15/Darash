import bisect
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QTextCursor

def get_word_idx_from_pos(verse_data, pos):
    """Finds the word index within a verse for a given document position."""
    if verse_data is None: return -1
    
    if pos < 0: return -1
    
    text = verse_data['text']
    current_char_offset = 0

    for i, token in enumerate(verse_data['tokens']):
        token_text = token[0]
        
        # Advance current_char_offset to the precise start of this token in the full text string
        start_idx = text.find(token_text, current_char_offset)
        
        # If the word isn't found, keep going from current position
        if start_idx == -1:
            start_idx = current_char_offset
            
        end_idx = start_idx + len(token_text)
        
        # Check if the document hit-test position falls cleanly within this token's bounds.
        # We also want to include the whitespace/formatting preceding the token as belonging to it
        if current_char_offset <= pos <= end_idx:
            return i
            
        current_char_offset = end_idx
        
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
    """Calculates the exact character offset of a word within a verse block."""
    text = verse_data['text']
    current_char_offset = 0
    
    for i in range(min(word_idx + 1, len(verse_data['tokens']))):
        token_text = verse_data['tokens'][i][0]
        
        # Advance current_char_offset to the precise start of this token
        start_idx = text.find(token_text, current_char_offset)
        
        # If the word isn't found, keep going from current position
        if start_idx == -1:
            start_idx = current_char_offset
            
        if i == word_idx:
            return start_idx
            
        current_char_offset = start_idx + len(token_text)
        
    return current_char_offset
