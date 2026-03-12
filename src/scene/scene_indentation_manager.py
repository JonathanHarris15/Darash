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

            # Pre-build a set of all mapped positions for O(1) lookups inside the loop
            mapped_positions = set(scene.verse_pos_map.values())
            
            # Batch all block updates in a single edit block to prevent multiple re-layouts
            from PySide6.QtGui import QTextCursor
            cursor = QTextCursor(doc)
            cursor.beginEditBlock()
            
            try:
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
                        pos = scene.verse_pos_map[ref]
                        block = doc.findBlock(pos)
                        
                        while block.isValid():
                            fmt = block.blockFormat()
                            fmt.setLeftMargin(new_indent * scene.tab_size + VERSE_NUMBER_RESERVED_WIDTH)
                            
                            cursor.setPosition(block.position())
                            cursor.setBlockFormat(fmt)
                            
                            block = block.next()
                            if not block.isValid(): break
                            if block.position() in mapped_positions: break
            finally:
                cursor.endEditBlock()

            # Targeted update for verse item positions
            self.update_all_verse_number_positions()
            
            # SUPPRESS expensive overlays like Strong's during active drag.
            # Only render essential study overlays (like marks) if specifically requested.
            # scene._render_study_overlays() 


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
            # Trigger full rerender on release
            scene.renderer.render_verses()
            if scene.strongs_enabled:
                scene.renderer._render_strongs_overlays()
            
        # Remove studyDataChanged.emit() as the Study Panel does not show indentation
        # and rebuilding the entire tree is extremely slow for these rapid changes.
