from PySide6.QtWidgets import QMenu
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QAction, QPen, QColor
from PySide6.QtWidgets import QGraphicsLineItem
from src.ui.components.outline_dialog import OutlineDialog

class SceneOutlineManager:
    """
    Handles outline creation, splitting, and divider dragging.
    """
    def __init__(self, scene):
        self.scene = scene

    def create_outline_from_verse_selection(self):
        scene = self.scene
        if not scene.selected_refs: return
        
        sorted_refs = sorted(list(scene.selected_refs), key=lambda r: scene.loader.get_verse_index(r))
        start_ref = sorted_refs[0]
        end_ref = sorted_refs[-1]
        
        dialog = OutlineDialog(None, title="Book Outline", start_ref=start_ref, end_ref=end_ref)
        if dialog.exec():
            data = dialog.get_data()
            if data["title"]:
                node = scene.study_manager.outline_manager.create_outline(
                    data["start_ref"], data["end_ref"], data["title"]
                )
                scene.studyDataChanged.emit()
                scene._render_outline_overlays()
                scene.outlineCreated.emit(node["id"])
                scene.set_active_outline(node["id"])

    def create_outline_from_selection(self):
        scene = self.scene
        if not scene.current_selection: return
        start, length = scene.current_selection
        
        start_ref = scene._get_ref_from_pos(start)
        end_ref = scene._get_ref_from_pos(start + length - 1)
        
        if not start_ref or not end_ref: return
        
        dialog = OutlineDialog(None, title="New Outline", start_ref=start_ref, end_ref=end_ref)
        if dialog.exec():
            data = dialog.get_data()
            if data["title"]:
                scene.study_manager.outline_manager.create_outline(
                    data["start_ref"], data["end_ref"], data["title"]
                )
                scene.studyDataChanged.emit() 
                scene._render_outline_overlays()

    def start_divider_drag(self, pos):
        from src.scene.components.reader_items import OutlineDividerItem
        scene = self.scene
        item = scene.sender()
        if not isinstance(item, OutlineDividerItem): return
        
        scene.is_dragging_divider = True
        scene.drag_divider_item = item
        
        parent = item.parent_node
        idx = item.split_idx
        loader = scene.loader
        
        # (Draggable boundary logic from ReaderScene goes here)
        # This part requires access to many scene properties, so it needs careful mapping.
        
        pen = QPen(QColor("#005a9e"))
        pen.setWidth(2)
        scene.drag_divider_ghost = QGraphicsLineItem(scene.side_margin, pos.y(), scene.sceneRect().width() - 10, pos.y())
        scene.drag_divider_ghost.setPen(pen)
        scene.drag_divider_ghost.setZValue(100)
        scene.addItem(scene.drag_divider_ghost)
        
        scene.views()[0].setCursor(Qt.SizeVerCursor)

    def handle_double_click(self, event):
        scene = self.scene
        if scene.active_outline_id and event.button() == Qt.LeftButton:
            scene_pos = event.scenePos()
            doc = scene.main_text_item.document()
            layout = doc.documentLayout()
            tolerance = 10 
            
            for i in range(len(scene.pos_verse_map) - 1):
                char_pos1, ref1 = scene.pos_verse_map[i]
                char_pos2, ref2 = scene.pos_verse_map[i+1]
                
                rect1 = layout.blockBoundingRect(doc.findBlock(char_pos1))
                rect2 = layout.blockBoundingRect(doc.findBlock(char_pos2))
                
                bottom1 = rect1.bottom()
                top2 = rect2.top()
                
                if bottom1 - tolerance <= scene_pos.y() <= top2 + tolerance:
                    if scene.study_manager.outline_manager.add_split(ref1, ref2, scene.loader):
                        scene._render_outline_overlays()
                        scene.studyDataChanged.emit()
                    
                    if scene.ghost_line_item:
                        scene.removeItem(scene.ghost_line_item)
                        scene.ghost_line_item = None
                    event.accept()
                    return True
        return False
