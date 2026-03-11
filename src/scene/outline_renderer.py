import re
from PySide6.QtGui import QColor, QPen
from PySide6.QtCore import Qt
from src.scene.components.reader_items import OutlineDividerItem

class OutlineRenderer:
    def __init__(self, scene):
        self.scene = scene

    def render(self):
        scene = self.scene
        scene._clear_outline_overlays()
        if not scene.outlines_enabled and not scene.active_outline_id: return
        
        outlines = scene.study_manager.outline_manager.get_outlines()
        if not scene.outlines_enabled and scene.active_outline_id:
            outlines = [o for o in outlines if o["id"] == scene.active_outline_id]
            
        doc = scene.main_text_item.document()
        layout = doc.documentLayout()
        
        def get_verse_y_range(ref, is_end=False):
            m = re.match(r"(.* \d+:\d+)([a-zA-Z]+)?$", ref)
            if not m: return None, None, None, None
            base_ref = m.group(1)
            letters = m.group(2)

            if base_ref in scene.verse_y_map:
                y_top, y_bottom = scene.verse_y_map[base_ref]
                
                if not letters:
                    visual_top = scene.layout_engine.get_first_verse_y_top(base_ref) if not is_end else y_top
                    return visual_top, y_bottom, None, None
                
                word_idx = scene.loader.letters_to_word_idx(letters)
                v_data = scene.loader.get_verse_by_ref(base_ref)
                if not v_data or word_idx >= len(v_data['tokens']): return y_top, y_bottom, None, None
                
                def get_inline_metrics(v_data, w_index):
                    pos = scene.verse_pos_map[base_ref]
                    w_offset = scene._get_word_offset_in_verse(v_data, w_index)
                    rects = scene._get_text_rects(pos + w_offset, len(v_data['tokens'][w_index][0]))
                    if not rects: return None
                    
                    rct = rects[-1]
                    gap_x = rct.right()
                    
                    if w_index + 1 < len(v_data['tokens']):
                        n_offset = scene._get_word_offset_in_verse(v_data, w_index + 1)
                        if n_offset >= 0:
                            n_rects = scene._get_text_rects(pos + n_offset, len(v_data['tokens'][w_index + 1][0]))
                            if n_rects:
                                n_rct = n_rects[0]
                                if abs(n_rct.center().y() - rct.center().y()) < 5:
                                    gap_x = (rct.right() + n_rct.left()) / 2
                                else:
                                    gap_x += 4
                    else:
                        gap_x += 4
                    
                    pitch = rct.height() * scene.line_spacing
                    top_y = rct.center().y() - pitch / 2
                    bot_y = rct.center().y() + pitch / 2
                    
                    return (gap_x, top_y, bot_y)

                if not is_end:
                    if word_idx > 0:
                        metrics = get_inline_metrics(v_data, word_idx - 1)
                        if metrics:
                            return y_top, y_bottom, metrics, metrics
                else:
                    metrics = get_inline_metrics(v_data, word_idx)
                    if metrics:
                        return y_top, y_bottom, metrics, metrics
                
                return y_top, y_bottom, None, None
            return None, None, None, None

        def get_line_style(level):
            color = QColor("#AAAAAA")
            if level == 0:
                pen = QPen(color, 2)
                return pen, True, None
            elif level == 1:
                pen = QPen(color, 2, Qt.SolidLine)
                return pen, False, None
            elif level == 2:
                pen = QPen(color, 1.5, Qt.CustomDashLine)
                pen.setDashPattern([4, 4])
                return pen, False, None
            elif level == 3:
                pen = QPen(color, 1.5, Qt.CustomDashLine)
                pen.setDashPattern([4, 10, 1, 10])
                return pen, False, None
            elif level == 4:
                pen = QPen(color, 1.5, Qt.CustomDashLine)
                pen.setDashPattern([1, 14])
                return pen, False, level
            else:
                pen = QPen(color, 1, Qt.SolidLine)
                return pen, False, level

        def render_node(node, level=0, is_active=False):
            start_ref = node["range"]["start"]
            end_ref = node["range"]["end"]
            
            node_is_active = is_active or (scene.active_outline_id and node.get("id") == scene.active_outline_id)
            
            s_top, s_bottom, s_inline_top, s_inline_bottom = get_verse_y_range(start_ref, is_end=False)
            e_top, e_bottom, e_inline_top, e_inline_bottom = get_verse_y_range(end_ref, is_end=True)
            
            if s_top is None or e_bottom is None: return

            def draw_divider(y, h_level, summary_node=None, split_parent=None, split_idx=-1, inline_pos=None):
                pen, is_double, text_level = get_line_style(h_level)
                x_end = scene.sceneRect().width() - 10
                
                item = OutlineDividerItem(split_parent, split_idx, y, scene.side_margin, x_end, pen, is_double, text_level=text_level)
                if inline_pos:
                    item.is_inline = True
                    item.inline_x = inline_pos[0]
                    item.inline_y_top = inline_pos[1]
                    item.inline_y_bot = inline_pos[2]
                
                item.setVisible(self._is_rect_visible(item.boundingRect()))
                if summary_node:
                    tip = f"[{summary_node['title']}]\\n{summary_node.get('summary', '')}"
                    item.setToolTip(tip)
                
                if node_is_active and split_idx != -1:
                    item.dragStarted.connect(scene._start_divider_drag)
                else:
                    item.setCursor(Qt.ArrowCursor)
                
                scene.addItem(item)
                scene.outline_overlay_items.append(item)

            if level == 0:
                draw_divider(s_top, 0, node, split_parent=node, split_idx=-2, inline_pos=s_inline_top)
                draw_divider(e_bottom, 0, node, split_parent=node, split_idx=-3, inline_pos=e_inline_bottom)
            
            if "children" in node:
                children = node["children"]
                child_divider_level = level + 1
                
                for i in range(len(children) - 1):
                    _, child_bottom, _, c_inline_bottom = get_verse_y_range(children[i]["range"]["end"], is_end=True)
                    next_child_top, _, nc_inline_top, _ = get_verse_y_range(children[i+1]["range"]["start"], is_end=False)
                    
                    if child_bottom is not None and next_child_top is not None:
                        inline_pos = c_inline_bottom if c_inline_bottom else nc_inline_top
                        if inline_pos:
                            draw_divider(inline_pos[1], child_divider_level, node, split_parent=node, split_idx=i, inline_pos=inline_pos)
                        else:
                            draw_divider(next_child_top, child_divider_level, node, split_parent=node, split_idx=i)
            
                for child in children:
                    render_node(child, level + 1, node_is_active)
                    
        for outline in outlines:
            render_node(outline)

    def _is_rect_visible(self, r):
        scene = self.scene
        buffer = 800 
        return not (r.bottom() < scene.scroll_y - buffer or r.top() > scene.scroll_y + scene.view_height + buffer)
