import bisect
from PySide6.QtGui import QPen, QColor, QBrush
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsLineItem
from src.scene.components.reader_items import VerseNumberItem, OutlineDividerItem

class OverlayRenderer:
    def __init__(self, scene):
        self.scene = scene

    def render_verses(self):
        scene = self.scene
        doc = scene.main_text_item.document()
        layout = doc.documentLayout()
        
        pos = layout.hitTest(QPointF(scene.side_margin + 10, scene.scroll_y + 100), Qt.FuzzyHit)
        if pos != -1:
            ref = scene._get_ref_from_pos(pos)
            if ref and ref != scene.last_emitted_ref:
                scene.last_emitted_ref = ref
                scene.currentReferenceChanged.emit(ref)
        
        self._render_visible_verse_numbers()
        
        if scene.strongs_enabled:
            self._render_strongs_overlays()
            
        if scene.outlines_enabled or scene.active_outline_id:
            self._render_outline_overlays()

    def _render_visible_verse_numbers(self):
        scene = self.scene
        doc = scene.main_text_item.document()
        layout = doc.documentLayout()
        
        buffer = 200
        start_pos = layout.hitTest(QPointF(scene.side_margin + 10, max(0, scene.scroll_y - buffer)), Qt.FuzzyHit)
        end_pos = layout.hitTest(QPointF(scene.side_margin + 10, scene.scroll_y + scene.view_height + buffer), Qt.FuzzyHit)
        
        if start_pos == -1: start_pos = 0
        if end_pos == -1: end_pos = doc.characterCount()
        
        visible_refs = set()
        start_idx = bisect.bisect_left(scene.pos_verse_map, (start_pos, ""))
        end_idx = bisect.bisect_right(scene.pos_verse_map, (end_pos, "zzzzzz"))
        
        start_idx = max(0, start_idx - 1)
        end_idx = min(len(scene.pos_verse_map), end_idx + 1)
        
        verse_indents = scene.study_manager.data.get("verse_indent", {})
        verse_marks = scene.study_manager.data.get("verse_marks", {})
        
        for i in range(start_idx, end_idx):
            char_pos, ref = scene.pos_verse_map[i]
            visible_refs.add(ref)
            
            mark_type = verse_marks.get(ref)
            is_selected = hasattr(scene, "selected_refs") and ref in scene.selected_refs

            if ref not in scene.verse_number_items:
                verse_data = scene.loader.get_verse_by_ref(ref)
                if not verse_data: continue
                
                block = doc.findBlock(char_pos)
                rect = layout.blockBoundingRect(block)
                indent_level = verse_indents.get(ref, 0)
                
                v_item = VerseNumberItem(verse_data['verse_num'], ref, scene.verse_num_font, scene.ref_color, mark_font=scene.verse_mark_font)
                v_item.setPos(scene.side_margin + (indent_level * scene.tab_size), rect.top())
                v_item.setZValue(10)
                v_item.mark_type = mark_type
                v_item.is_selected = is_selected
                
                v_item.clicked.connect(lambda shift, v=v_item: scene._on_verse_num_clicked(v, shift))
                v_item.doubleClicked.connect(scene._clear_verse_selection)
                v_item.contextMenuRequested.connect(lambda pos, v=v_item: scene._on_verse_num_context_menu(v, pos))
                v_item.dragged.connect(lambda dx, v=v_item: scene.indentation_manager.on_verse_num_dragged(v, dx))
                v_item.released.connect(scene.indentation_manager.on_verse_num_released)
                
                scene.addItem(v_item)
                scene.verse_number_items[ref] = v_item
            else:
                it = scene.verse_number_items[ref]
                if it.mark_type != mark_type or it.is_selected != is_selected:
                    it.mark_type = mark_type
                    it.is_selected = is_selected
                    it.update()

        to_remove = []
        for ref, it in scene.verse_number_items.items():
            if ref not in visible_refs and not it.is_selected:
                to_remove.append(ref)
        
        for ref in to_remove:
            it = scene.verse_number_items.pop(ref)
            scene.removeItem(it)

    def _render_outline_overlays(self):
        scene = self.scene
        scene._clear_outline_overlays()
        if not scene.outlines_enabled and not scene.active_outline_id: return
        
        outlines = scene.study_manager.outline_manager.get_outlines()
        if not scene.outlines_enabled and scene.active_outline_id:
            outlines = [o for o in outlines if o["id"] == scene.active_outline_id]
            
        doc = scene.main_text_item.document()
        layout = doc.documentLayout()
        
        def get_verse_y_range(ref):
            if ref in scene.verse_pos_map:
                pos = scene.verse_pos_map[ref]
                block = doc.findBlock(pos)
                rect = layout.blockBoundingRect(block)
                # Use the actual text block boundaries
                return rect.top(), rect.bottom()
            return None, None

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
            
            s_top, s_bottom = get_verse_y_range(start_ref)
            e_top, e_bottom = get_verse_y_range(end_ref)
            
            if s_top is None or e_bottom is None: return

            # Top boundary should be just above the verse text (below headers)
            y_start = s_top - 2
            # Bottom boundary should be just below the verse text (above next headers)
            y_end = e_bottom + 2

            def draw_h_line(y, h_level, summary_node=None, split_parent=None, split_idx=-1):
                pen, is_double, text_level = get_line_style(h_level)
                x_end = scene.sceneRect().width() - 10
                
                item = OutlineDividerItem(split_parent, split_idx, y, scene.side_margin, x_end, pen, is_double, text_level=text_level)
                item.setVisible(scene._is_rect_visible(item.boundingRect()))
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
                draw_h_line(y_start, 0, node, split_parent=node, split_idx=-2)
                draw_h_line(y_end, 0, node, split_parent=node, split_idx=-3)
            
            if "children" in node:
                children = node["children"]
                child_divider_level = level + 1
                
                for i in range(len(children) - 1):
                    # Child dividers also go between verses
                    _, child_bottom = get_verse_y_range(children[i]["range"]["end"])
                    next_child_top, _ = get_verse_y_range(children[i+1]["range"]["start"])
                    
                    if child_bottom is not None and next_child_top is not None:
                        # Center child dividers in the gap (usually includes headers)
                        # Or should they also be below headers? Let's center for now 
                        # as child splits usually don't happen across major book breaks.
                        mid_y = (child_bottom + next_child_top) / 2
                        draw_h_line(mid_y, child_divider_level, node, split_parent=node, split_idx=i)
            
                for child in children:
                    render_node(child, level + 1, node_is_active)
                    
        for outline in outlines:
            render_node(outline)

    def _render_strongs_overlays(self):
        scene = self.scene
        scene._clear_strongs_overlays()
        
        doc = scene.main_text_item.document()
        layout = doc.documentLayout()
        
        buffer = 100
        start_pos = layout.hitTest(QPointF(scene.side_margin + 10, max(0, scene.scroll_y - buffer)), Qt.FuzzyHit)
        end_pos = layout.hitTest(QPointF(scene.side_margin + 10, scene.scroll_y + scene.view_height + buffer), Qt.FuzzyHit)
        
        if start_pos == -1: start_pos = 0
        if end_pos == -1: end_pos = doc.characterCount()
        
        start_idx = bisect.bisect_left(scene.pos_verse_map, (start_pos, ""))
        end_idx = bisect.bisect_right(scene.pos_verse_map, (end_pos, "zzzzzz"))
        
        start_idx = max(0, start_idx - 1)
        end_idx = min(len(scene.pos_verse_map), end_idx + 1)
        
        pen = QPen(QColor(120, 120, 120, 120), 1.5) 
        
        for i in range(start_idx, end_idx):
            char_pos, ref = scene.pos_verse_map[i]
            
            verse = scene.loader.get_verse_by_ref(ref)
            if not verse: continue
            
            v_start = scene.verse_pos_map[ref]
            
            for word_idx, token in enumerate(verse['tokens']):
                if len(token) > 1:
                    start_pos_in_v = scene._get_word_offset_in_verse(verse, word_idx)
                    rects = scene._get_text_rects(v_start + start_pos_in_v, len(token[0]))
                    for r in rects:
                        line = QGraphicsLineItem(r.left(), r.bottom() + 1, r.right(), r.bottom() + 1)
                        line.setPen(pen)
                        line.setZValue(-1)
                        line.setAcceptedMouseButtons(Qt.NoButton)
                        scene.addItem(line)
                        scene.strongs_overlay_items.append(line)

    def _render_search_overlays(self):
        scene = self.scene
        from src.core.constants import SEARCH_HIGHLIGHT_COLOR
        for it in scene.search_overlay_items: scene.removeItem(it)
        scene.search_overlay_items.clear()

        for start, length in scene.search_results:
            rects = scene._get_text_rects(start, length)
            for r in rects:
                hl = QGraphicsRectItem(r)
                hl.setBrush(QBrush(SEARCH_HIGHLIGHT_COLOR))
                hl.setPen(Qt.NoPen); hl.setZValue(-1)
                hl.setAcceptedMouseButtons(Qt.NoButton)
                hl.setVisible(scene._is_rect_visible(r))
                scene.addItem(hl); scene.search_overlay_items.append(hl)
