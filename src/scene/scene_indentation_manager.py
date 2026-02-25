from PySide6.QtGui import QTextCursor
from src.core.verse_loader import VerseLoader

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
            
            for ref in scene.selected_refs:
                if not hasattr(scene, "_drag_start_indents"):
                    scene._drag_start_indents = {}
                
                if ref not in scene._drag_start_indents:
                    scene._drag_start_indents[ref] = verse_indents.get(ref, 0)
                
                start_indent = scene._drag_start_indents[ref]
                new_indent = max(0, start_indent + tabs_diff)
                
                scene.study_manager.data["verse_indent"][ref] = new_indent
                
                if ref in scene.verse_pos_map:
                    pos = scene.verse_pos_map[ref]
                    block = doc.findBlock(pos)
                    fmt = block.blockFormat()
                    fmt.setLeftMargin(new_indent * scene.tab_size)
                    
                    cursor = QTextCursor(block)
                    cursor.setBlockFormat(fmt)

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
                
                indent_level = verse_indents.get(ref, 0)
                it.setPos(scene.side_margin + (indent_level * scene.tab_size), rect.top())

    def on_verse_num_released(self):
        scene = self.scene
        scene.study_manager.save_study()
        
        if hasattr(scene, "_last_drag_tabs_diff"):
            del scene._last_drag_tabs_diff
        if hasattr(scene, "_drag_start_indents"):
            del scene._drag_start_indents
            
        if hasattr(scene, "_was_dragged") and scene._was_dragged:
            scene._clear_verse_selection()
            scene._was_dragged = False
            
        scene.studyDataChanged.emit()
