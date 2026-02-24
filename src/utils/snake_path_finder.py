from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QTextCursor, QTextDocument, QTextLine
import math

class SnakePathFinder:
    """
    Calculates the snaking path between two word keys through punctuation gates and margins.
    """
    GATES_CHARS = [",", ";", ":", ".", "?", "!"]

    def __init__(self, scene):
        self.scene = scene
        self._path_cache = {} # Cache for (start_key, end_key) -> path
        self._cache_layout_version = -1 # Invalidate cache if layout changes

    def calculate_path(self, start_key, end_key):
        # Invalidate cache if layout has changed
        if self._cache_layout_version != self.scene.layout_version:
            self._path_cache.clear()
            self._cache_layout_version = self.scene.layout_version

        cache_key = (start_key, end_key)
        if cache_key in self._path_cache:
            return self._path_cache[cache_key]

        start_center = self.scene._get_word_center(start_key)
        end_center = self.scene._get_word_center(end_key)
        if not start_center or not end_center:
            return None

        # Get line info for start and end
        start_line_rect, _ = self._get_line_info(start_key)
        
        # SAME LINE LOGIC
        if abs(start_center.y() - end_center.y()) < 10:
            path = self._calculate_same_line_path(start_key, end_key, start_center, end_center, start_line_rect)
        # DIFFERENT LINE LOGIC
        else:
            path = self._calculate_multi_line_path(start_center, end_center)

        self._path_cache[cache_key] = path
        return path

    def _get_line_info(self, key):
        """Returns (line_rect, global_line_index) for a word key."""
        if not key or not isinstance(key, str): return None, -1
        ref_parts = key.split('|')
        if len(ref_parts) < 4: return None, -1 # Ensure we have Book|Chap|Verse|WordIdx
        
        ref = f"{ref_parts[0]} {ref_parts[1]}:{ref_parts[2]}"
        word_idx = int(ref_parts[3])
        
        if ref not in self.scene.verse_pos_map:
            return None, -1
            
        v_start = self.scene.verse_pos_map[ref]
        verse_data = self.scene.loader.get_verse_by_ref(ref)
        if not verse_data:
            return None, -1
            
        word_pos_in_v = self.scene._get_word_offset_in_verse(verse_data, word_idx)
        abs_pos = v_start + word_pos_in_v
        
        doc = self.scene.main_text_item.document()
        layout = doc.documentLayout()
        block = doc.findBlock(abs_pos)
        line = block.layout().lineForTextPosition(abs_pos - block.position())
        
        line_rect = line.rect()
        line_rect.translate(layout.blockBoundingRect(block).topLeft())
        
        return line_rect, int(line_rect.center().y())

    def _get_gates_on_y(self, y):
        """Finds all gate X-coordinates on the line at visual position Y."""
        doc = self.scene.main_text_item.document()
        layout = doc.documentLayout()
        
        pos = layout.hitTest(QPointF(self.scene.side_margin + 50, y), Qt.FuzzyHit)
        if pos == -1: return [self.scene.side_margin, self.scene.last_width - self.scene.side_margin]
        
        block = doc.findBlock(pos)
        if not block.isValid(): return [self.scene.side_margin, self.scene.last_width - self.scene.side_margin]

        block_pos = block.position()
        text = block.text()
        
        # Find which line within the block we are on
        rel_pos = pos - block_pos
        line = block.layout().lineForTextPosition(rel_pos)
        line_start = line.textStart()
        line_len = line.textLength()
        line_text = text[line_start : line_start + line_len]
        
        gates = [self.scene.side_margin, self.scene.last_width - self.scene.side_margin]
        
        # Find punctuation gates
        for i, char in enumerate(line_text):
            if char in self.GATES_CHARS:
                # Calculate visual X of this character
                char_rel_pos = line_start + i
                x_off = line.cursorToX(char_rel_pos)[0]
                # Adjust for block position and margin
                gates.append(x_off + layout.blockBoundingRect(block).left())
                
        return sorted(list(set(gates)))

    def _get_all_lines_between(self, start_y, end_y):
        """Returns a list of line rectangles and their gates between two Y coordinates."""
        doc = self.scene.main_text_item.document()
        layout = doc.documentLayout()
        
        lines_data = []
        curr_y_scan = min(start_y, end_y)
        limit_y_scan = max(start_y, end_y)
        
        step = 10.0 # Vertical scan step
        processed_blocks = set()
        
        y_scan = curr_y_scan
        while y_scan <= limit_y_scan:
            pos = layout.hitTest(QPointF(self.scene.side_margin + 50, y_scan), Qt.FuzzyHit)
            if pos != -1:
                block = doc.findBlock(pos)
                if block.isValid() and block.blockNumber() not in processed_blocks:
                    processed_blocks.add(block.blockNumber())
                    block_rect = layout.blockBoundingRect(block)
                    
                    for i in range(block.layout().lineCount()):
                        line = block.layout().lineAt(i)
                        line_rect = line.rect()
                        line_rect.translate(block_rect.topLeft())
                        
                        # Only include lines that are actually between our start and end
                        if line_rect.bottom() < min(start_y, end_y) - 5: continue
                        if line_rect.top() > max(start_y, end_y) + 5: continue
                        
                        gates = [self.scene.side_margin, self.scene.last_width - self.scene.side_margin]
                        text = block.text()
                        l_start = line.textStart()
                        l_text = text[l_start : l_start + line.textLength()]
                        
                        for char_idx, char in enumerate(l_text):
                            if char in self.GATES_CHARS:
                                x_off = line.cursorToX(l_start + char_idx)[0]
                                gates.append(x_off + block_rect.left())
                        
                        lines_data.append({
                            "rect": line_rect,
                            "gates": sorted(list(set(gates))),
                            "line_object": line
                        })
            y_scan += step
            
        lines_data.sort(key=lambda x: x["rect"].center().y())
        if end_y < start_y:
            lines_data.reverse()
        return lines_data

    def _calculate_same_line_path(self, start_key, end_key, start, end, line_rect):
        """Logic for start/end on the same line (Rectangle loop)."""
        offset = 15.0
        
        above_count = 0
        below_count = 0
        
        # Iterate over all arrows in the study data
        # To avoid recursion, we assume the gutter position based on start/end word Y
        for skey_in_data, arrow_list in self.scene.study_manager.data.get("arrows", {}).items():
            for arrow_data in arrow_list:
                if arrow_data.get('type') == 'snake':
                    # Do not count the arrow we are currently drawing
                    if (skey_in_data, arrow_data['end_key']) == (start_key, end_key):
                        continue

                    other_start_center = self.scene._get_word_center(skey_in_data)
                    other_end_center = self.scene._get_word_center(arrow_data['end_key'])
                    
                    # Check if this existing arrow is relevant (same line)
                    if other_start_center and other_end_center:
                        if abs(other_start_center.y() - other_end_center.y()) < 10: # It's a same-line arrow
                            other_start_line_rect, _ = self._get_line_info(skey_in_data)
                            if abs(other_start_line_rect.center().y() - line_rect.center().y()) < 10: # On the same actual line
                                # Heuristic: If its start word's Y is less than the line center Y, assume it goes above.
                                # This is a reasonable estimation without full path recalculation.
                                if other_start_center.y() < other_start_line_rect.center().y():
                                    above_count += 1
                                else:
                                    below_count += 1

        if above_count <= below_count: # Prefer above or if counts are equal
            gutter_y = line_rect.top() - offset
        else: # More arrows above, go below
            gutter_y = line_rect.bottom() + offset
        
        return [start, QPointF(start.x(), gutter_y), QPointF(end.x(), gutter_y), end]

    def _calculate_multi_line_path(self, start, end):
        """Shortest path through punctuation gates between different lines."""
        lines = self._get_all_lines_between(start.y(), end.y())
        if len(lines) < 2:
            return [start, end]
            
        path = [start]
        curr_x = start.x()
        direction = 1 if end.y() > start.y() else -1
        
        gulley_offset = 8.0 * direction # Small offset to place arrow in the gulley
        
        # 1. Move from start to the first gulley
        start_line = lines[0]["rect"]
        curr_y = (start_line.bottom() if direction == 1 else start_line.top()) + gulley_offset
        path.append(QPointF(curr_x, curr_y))
        
        # 2. Iterate through in-between lines (those that must be passed through a gate)
        # Skip the very first and very last line in the 'lines' list for gate calculation
        # as per new requirements.
        for i in range(1, len(lines) - 1): # Exclude first (start) and last (end) line
            line = lines[i]
            l_rect = line["rect"]
            gates = line["gates"]
            
            # Find closest gate on this line
            # NEW RULE: If the line doesn't fill the whole width and curr_x is past the text, just pass through.
            line_text_end_x = l_rect.left() + lines[i]["line_object"].naturalTextWidth()
            if curr_x > line_text_end_x + 5: # 5px buffer
                # No need to snap to a gate, just move vertically
                pass
            else:
                best_gate_x = min(gates, key=lambda x: abs(x - curr_x))
                # Move horizontally in gulley to the gate
                if abs(best_gate_x - curr_x) > 1:
                    curr_x = best_gate_x
                    path.append(QPointF(curr_x, curr_y))
            
            # Move vertically through the line to the next gulley
            curr_y = (l_rect.bottom() if direction == 1 else l_rect.top()) + gulley_offset
            path.append(QPointF(curr_x, curr_y))
            
        # 3. Final horizontal move in the gulley adjacent to the end word
        path.append(QPointF(end.x(), curr_y))
        
        # 4. Final vertical move to the end word
        path.append(end)
        
        return path
