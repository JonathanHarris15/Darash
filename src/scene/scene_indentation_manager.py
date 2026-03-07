from PySide6.QtGui import QTextCursor
from src.core.verse_loader import VerseLoader
from src.core.constants import VERSE_NUMBER_RESERVED_WIDTH

class SceneIndentationManager:
    """
    Handles verse indentation dragging and updates.
    """
    def __init__(self, scene):
        self.scene = scene

    def on_verse_num_dragged(self, item, dx):
        scene = self.scene
        if item.ref not in scene.selected_refs:
            scene._on_verse_num_clicked(item, False)
            
        scene._was_dragged = True 
        tabs_diff = round(dx / scene.tab_size)
        
        if not hasattr(scene, "_last_drag_tabs_diff") or scene._last_drag_tabs_diff != tabs_diff:
            scene._last_drag_tabs_diff = tabs_diff
            
            doc = scene.main_text_item.document()
            verse_indents = scene.study_manager.data.get("verse_indent", {})
            
            # Determine target_ref from item
            if hasattr(item, "s_ref") and item.s_ref:
                target_ref = item.s_ref
            elif scene.sentence_break_enabled:
                target_ref = f"{item.ref}|0"
            else:
                target_ref = item.ref
                
            # If multiple verses are selected and we're NOT in sentence-break mode, 
            # we apply to all selected verses.
            if not scene.sentence_break_enabled and len(scene.selected_refs) > 1:
                target_refs = list(scene.selected_refs)
            else:
                target_refs = [target_ref]

            for ref in target_refs:
                if not hasattr(scene, "_drag_start_indents"):
                    scene._drag_start_indents = {}
                
                if ref not in scene._drag_start_indents:
                    scene._drag_start_indents[ref] = verse_indents.get(ref, 0)
                
                start_indent = scene._drag_start_indents[ref]
                new_indent = max(0, start_indent + tabs_diff)
                
                scene.study_manager.data["verse_indent"][ref] = new_indent
                
                # Update visual block format
                if ref in scene.verse_pos_map:
                    # We need to update the indentation for ALL blocks belonging to this verse/sentence.
                    # This includes secondary translation blocks that follow the primary.
                    pos = scene.verse_pos_map[ref]
                    block = doc.findBlock(pos)
                    
                    while block.isValid():
                        fmt = block.blockFormat()
                        fmt.setLeftMargin(new_indent * scene.tab_size + VERSE_NUMBER_RESERVED_WIDTH)
                        
                        cursor = QTextCursor(block)
                        cursor.setBlockFormat(fmt)
                        
                        # Move to next block. 
                        # Stop if we hit a block that belongs to the NEXT verse or sentence.
                        block = block.next()
                        if not block.isValid(): break
                        
                        # If the next block has its OWN mapping in verse_pos_map, 
                        # it's a separate entity (next sentence or next verse), so stop.
                        next_pos = block.position()
                        is_mapped = any(p == next_pos for p in scene.verse_pos_map.values())
                        if is_mapped: break

            # Targeted update: only update positions of items actually moved
            # Instead of updating EVERYTHING, we update the target items
            self.update_all_verse_number_positions()
            scene._render_study_overlays()
            if scene.strongs_enabled:
                scene.renderer._render_strongs_overlays()

    def update_all_verse_number_positions(self):
        scene = self.scene
        doc = scene.main_text_item.document()
        layout = doc.documentLayout()
        verse_indents = scene.study_manager.data.get("verse_indent", {})
        
        for ref, it in scene.verse_number_items.items():
            if ref in scene.verse_pos_map:
                pos = scene.verse_pos_map[ref]
                block = doc.findBlock(pos)
                rect = layout.blockBoundingRect(block)
                
                # If sentences are enabled, the indent for the first sentence (|0) 
                # defines the position of the verse number.
                s_ref = f"{ref}|0" if scene.sentence_break_enabled else ref
                indent_level = verse_indents.get(s_ref, verse_indents.get(ref, 0))
                it.setPos(scene.side_margin + (indent_level * scene.tab_size), rect.top())

    def on_verse_num_released(self):
        scene = self.scene
        scene.study_manager.save_data()
        
        if hasattr(scene, "_last_drag_tabs_diff"):
            del scene._last_drag_tabs_diff
        if hasattr(scene, "_drag_start_indents"):
            del scene._drag_start_indents
            
        if hasattr(scene, "_was_dragged") and scene._was_dragged:
            scene._clear_verse_selection()
            scene._was_dragged = False
            
        scene.studyDataChanged.emit()
