from PySide6.QtWidgets import QMenu
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QAction, QPen, QColor
from PySide6.QtWidgets import QGraphicsLineItem

class SceneOutlineManager:
    """
    Handles outline creation, splitting, and divider dragging.
    """
    def __init__(self, scene):
        self.scene = scene

    def create_outline(self, start_ref, end_ref, title, summary=""):
        """Creates a new outline and refreshes the scene."""
        result = self.scene.study_manager.outline_manager.create_outline(start_ref, end_ref, title, summary)
        if result:
            self.scene.renderer._render_outline_overlays()
            self.scene.studyDataChanged.emit()
            self.scene.outlineCreated.emit(result["id"])
            return result
        return None

    def create_outline_from_verse_selection(self):
        scene = self.scene
        if not scene.selected_refs: return
        
        sorted_refs = sorted(list(scene.selected_refs), key=lambda r: scene.loader.get_verse_index(r))
        start_ref = sorted_refs[0]
        end_ref = sorted_refs[-1]
        scene.showOutlineDialog.emit(start_ref, end_ref)

    def create_outline_from_selection(self):
        scene = self.scene
        if not scene.current_selection: return
        start, length = scene.current_selection
        
        start_ref = scene._get_ref_from_pos(start)
        end_ref = scene._get_ref_from_pos(start + length - 1)
        
        if not start_ref or not end_ref: return
        scene.showOutlineDialog.emit(start_ref, end_ref)

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
        
        # Determine draggable bounds
        scene.drag_bounds_min = 0
        scene.drag_bounds_max = len(loader.flat_verses) - 1
        scene.drag_hard_min = None
        scene.drag_hard_max = None
        
        if idx == -2: # Outer Start
            scene.drag_bounds_max = loader.get_verse_index(parent["range"]["end"]) - 1
            if "children" in parent and parent["children"]:
                curr = parent["children"][0]
                while "children" in curr and curr["children"]:
                    curr = curr["children"][0]
                scene.drag_hard_max = loader.get_verse_index(curr["range"]["end"])
        elif idx == -3: # Outer End
            scene.drag_bounds_min = loader.get_verse_index(parent["range"]["start"]) + 1
            if "children" in parent and parent["children"]:
                curr = parent["children"][-1]
                while "children" in curr and curr["children"]:
                    curr = curr["children"][-1]
                scene.drag_hard_min = loader.get_verse_index(curr["range"]["start"])
        elif idx >= 0: # Internal Split
            c1 = parent["children"][idx]
            c2 = parent["children"][idx+1]
            scene.drag_bounds_min = loader.get_verse_index(c1["range"]["start"])
            scene.drag_bounds_max = loader.get_verse_index(c2["range"]["end"])
            
            # Hard constraints to prevent sub-children from being orphaned
            if "children" in c1 and c1["children"]:
                curr = c1["children"][-1]
                while "children" in curr and curr["children"]:
                    curr = curr["children"][-1]
                scene.drag_hard_min = loader.get_verse_index(curr["range"]["start"])
            if "children" in c2 and c2["children"]:
                curr = c2["children"][0]
                while "children" in curr and curr["children"]:
                    curr = curr["children"][0]
                scene.drag_hard_max = loader.get_verse_index(curr["range"]["end"])

        pen = QPen(QColor("#005a9e"))
        pen.setWidth(2)
        scene.drag_divider_ghost = QGraphicsLineItem(scene.side_margin, pos.y(), scene.sceneRect().width() - 10, pos.y())
        scene.drag_divider_ghost.setPen(pen)
        scene.drag_divider_ghost.setZValue(100)
        scene.addItem(scene.drag_divider_ghost)
        
        scene.views()[0].setCursor(Qt.SizeVerCursor)

    def handle_mouse_move(self, event):
        scene = self.scene
        if scene.is_dragging_divider:
            scene_pos = event.scenePos()
            best_gap_y, best_dist = -1, 1000
            best_x = -1
            best_pitch = 24
            best_ref_before, best_ref_after = None, None
            is_word_drag = bool(event.modifiers() & Qt.ControlModifier)
            is_outer = scene.drag_divider_item.split_idx < 0
            
            if is_word_drag:
                for r, (y_top, y_bottom) in scene.verse_y_map.items():
                    if y_bottom < scene_pos.y() - 100 or y_top > scene_pos.y() + 100: continue
                    idx = scene.loader.get_verse_index(r)
                    if idx < scene.drag_bounds_min or (not is_outer and idx >= scene.drag_bounds_max) or (is_outer and idx > scene.drag_bounds_max): continue
                    if scene.drag_hard_min is not None and idx < scene.drag_hard_min: continue
                    if scene.drag_hard_max is not None and idx >= scene.drag_hard_max: continue
                    
                    v_data = scene.loader.get_verse_by_ref(r)
                    if not v_data: continue
                    v_start_pos = scene.verse_pos_map.get(r)
                    if v_start_pos is None: continue
                    
                    for w_idx in range(len(v_data['tokens'])):
                        w_offset = scene._get_word_offset_in_verse(v_data, w_idx)
                        rects = scene._get_text_rects(v_start_pos + w_offset, len(v_data['tokens'][w_idx][0]))
                        if not rects: continue
                        rct = rects[-1]
                        
                        gap_x = rct.right()
                        if w_idx + 1 < len(v_data['tokens']):
                            n_offset = scene._get_word_offset_in_verse(v_data, w_idx + 1)
                            n_rects = scene._get_text_rects(v_start_pos + n_offset, len(v_data['tokens'][w_idx + 1][0]))
                            if n_rects:
                                n_rct = n_rects[0]
                                if abs(n_rct.center().y() - rct.center().y()) < 5:
                                    gap_x = (rct.right() + n_rct.left()) / 2
                                else:
                                    gap_x += 4
                        else:
                            gap_x += 4
                            
                        gap_y = rct.center().y()
                        pitch = rct.height() * scene.line_spacing
                        
                        dist = ((scene_pos.x() - gap_x)**2 + (scene_pos.y() - gap_y)**2)**0.5
                        if dist < best_dist and dist < 150:
                            best_dist = dist
                            best_x = gap_x
                            best_gap_y = gap_y
                            best_pitch = pitch
                            best_ref_before = r + scene.loader.word_idx_to_letters(w_idx)
                            if w_idx < len(v_data['tokens']) - 1:
                                best_ref_after = r + scene.loader.word_idx_to_letters(w_idx + 1)
                            else:
                                next_idx = int(idx) + 1
                                best_ref_after = scene.loader.flat_verses[next_idx]['ref'] if next_idx < len(scene.loader.flat_verses) else None
            else:
                if len(scene.pos_verse_map) > 0:
                    char_pos0, r0 = scene.pos_verse_map[0]; idx0 = scene.loader.get_verse_index(r0)
                    if idx0 >= scene.drag_bounds_min and idx0 <= scene.drag_bounds_max:
                        y_top0 = scene.layout_engine.get_first_verse_y_top(r0)
                        dist0 = abs(scene_pos.y() - y_top0)
                        if dist0 < 50 and dist0 < best_dist: 
                            best_dist, best_gap_y = dist0, y_top0
                            best_ref_before, best_ref_after = None, r0
                for i in range(len(scene.pos_verse_map) - 1):
                    char_pos1, r1 = scene.pos_verse_map[i]; char_pos2, r2 = scene.pos_verse_map[i+1]; idx_before = scene.loader.get_verse_index(r1)
                    if idx_before < scene.drag_bounds_min or (not is_outer and idx_before >= scene.drag_bounds_max) or (is_outer and idx_before > scene.drag_bounds_max):
                        continue
                    if scene.drag_hard_min is not None and idx_before < scene.drag_hard_min: continue
                    if scene.drag_hard_max is not None and idx_before >= scene.drag_hard_max: continue
                    mid_y = scene.layout_engine.get_verse_y_midpoint(r1, r2)
                    dist = abs(scene_pos.y() - mid_y)
                    if dist < 50 and dist < best_dist: 
                        best_dist, best_gap_y = dist, mid_y
                        best_ref_before, best_ref_after = r1, r2

            if best_gap_y != -1: 
                scene._current_drag_refs = (best_ref_before, best_ref_after)
                if is_word_drag:
                    scene.drag_divider_ghost.setLine(best_x, best_gap_y - best_pitch / 2, best_x, best_gap_y + best_pitch / 2)
                else:
                    scene.drag_divider_ghost.setLine(scene.side_margin, best_gap_y, scene.sceneRect().width() - 10, best_gap_y)
                scene.drag_divider_ghost.show()
            else: 
                scene._current_drag_refs = (None, None)
                scene.drag_divider_ghost.hide()
            return True
            
        if scene.active_outline_id:
            scene_pos = event.scenePos(); tolerance = 25; found_gap = False
            refs = list(scene.verse_y_map.keys())
            doc = scene.main_text_item.document()
            layout = doc.documentLayout()
            
            best_dist = tolerance
            best_mid_y = None
            
            for i in range(len(refs) - 1):
                _, prev_bottom = scene.verse_y_map[refs[i]]
                next_top, _ = scene.verse_y_map[refs[i + 1]]
                if scene_pos.y() < prev_bottom - 200 or scene_pos.y() > next_top + 200:
                    continue
                    
                block2 = doc.findBlock(scene.verse_pos_map[refs[i + 1]])
                block1 = block2.previous()
                if block1.isValid() and block2.isValid():
                    mid_y = (layout.blockBoundingRect(block1).bottom() + layout.blockBoundingRect(block2).top()) / 2
                else:
                    mid_y = (prev_bottom + next_top) / 2
                
                dist = abs(scene_pos.y() - mid_y)
                if dist < best_dist:
                    best_dist = dist
                    best_mid_y = mid_y
                    
            if best_mid_y is not None:
                if not scene.ghost_line_item:
                    from PySide6.QtGui import QPen; pen = QPen(QColor("#AAAAAA"), 1.0, Qt.DotLine); color = QColor("#AAAAAA"); color.setAlpha(80); pen.setColor(color)
                    from PySide6.QtWidgets import QGraphicsLineItem; scene.ghost_line_item = QGraphicsLineItem(scene.side_margin, best_mid_y, scene.sceneRect().width() - 10, best_mid_y)
                    scene.ghost_line_item.setPen(pen); scene.addItem(scene.ghost_line_item)
                else: 
                    scene.ghost_line_item.setLine(scene.side_margin, best_mid_y, scene.sceneRect().width() - 10, best_mid_y)
                found_gap = True
                    
            if not found_gap and scene.ghost_line_item: scene.removeItem(scene.ghost_line_item); scene.ghost_line_item = None
            return found_gap
            
        return False

    def handle_mouse_release(self, event):
        scene = self.scene
        if scene.is_dragging_divider:
            scene.is_dragging_divider = False
            if scene.drag_divider_ghost: 
                if not scene.drag_divider_ghost.isVisible() or getattr(scene, '_current_drag_refs', (None, None)) == (None, None):
                    scene.removeItem(scene.drag_divider_ghost); scene.drag_divider_ghost = None; scene.drag_divider_item = None
                    scene.views()[0].setCursor(Qt.ArrowCursor); return True
                
                ref_before, ref_after = scene._current_drag_refs
                
                if ref_after: # For boundaries, ref_before can be None
                    item = scene.drag_divider_item
                    if item.split_idx == -2: 
                        if scene.study_manager.outline_manager.update_outline_boundary(item.parent_node["id"], True, ref_after, scene.loader):
                            scene.renderer._render_outline_overlays(); scene.studyDataChanged.emit()
                    elif item.split_idx == -3: 
                        if ref_before and scene.study_manager.outline_manager.update_outline_boundary(item.parent_node["id"], False, ref_before, scene.loader):
                            scene.renderer._render_outline_overlays(); scene.studyDataChanged.emit()
                    elif item.split_idx >= 0 and ref_before:
                        if scene.study_manager.outline_manager.move_split_by_id(item.parent_node["id"], item.split_idx, ref_before, ref_after, scene.loader):
                            scene.renderer._render_outline_overlays(); scene.studyDataChanged.emit()
                scene.removeItem(scene.drag_divider_ghost); scene.drag_divider_ghost = None; scene.drag_divider_item = None
                scene.views()[0].setCursor(Qt.ArrowCursor); return True
        return False

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

    def cycle_divider_at_pos(self, pos, delta):
        from src.scene.components.reader_items import OutlineDividerItem
        scene = self.scene
        view = scene.views()[0]
        item = scene.itemAt(pos, view.transform())
        
        if isinstance(item, OutlineDividerItem):
            if item.parent_node and item.split_idx != -1:
                forward = delta > 0
                if scene.study_manager.outline_manager.cycle_level_by_id(item.parent_node["id"], item.split_idx, forward):
                    scene._render_outline_overlays()
                    scene.studyDataChanged.emit()
                    return True
        return False
