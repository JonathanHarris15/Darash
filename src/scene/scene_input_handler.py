from PySide6.QtCore import Qt, QPointF, QObject, QTimer
from PySide6.QtGui import QColor, QCursor, QTextCursor, QGuiApplication
from src.scene.components.reader_items import ArrowItem, OutlineDividerItem

class SceneInputHandler(QObject):
    """
    Handles keyboard and mouse events for ReaderScene, 
    including complex state machines like arrow drawing and Strongs lookups.
    """
    def __init__(self, scene):
        super().__init__()
        self.scene = scene
        self._was_dragged = False
        self._last_drag_tabs_diff = 0
        self._drag_start_indents = {}
        self.d_key_pressed = False
        self._last_hovered_word_key = None

        # Strongs Hover State
        self.strongs_hover_timer = QTimer(self)
        self.strongs_hover_timer.setSingleShot(True)
        self.strongs_hover_timer.setInterval(500)
        self.strongs_hover_timer.timeout.connect(self.on_strongs_hover_timeout)
        self.last_strongs_pos = QPointF()

    def handle_key_press(self, event):
        key = event.key()
        modifiers = event.modifiers()
        scene = self.scene

        if key == Qt.Key_C and (modifiers & Qt.ControlModifier):
            self._handle_copy()
            return True

        if key == Qt.Key_Z and modifiers & Qt.ControlModifier:
            if scene.study_manager.undo():
                scene._render_study_overlays()
                scene.studyDataChanged.emit()
            return True

        if key in (Qt.Key_Delete, Qt.Key_Backspace):
            self._handle_delete_key()
            return True

        if key == Qt.Key_A and not scene.is_drawing_arrow and not event.isAutoRepeat():
            self._start_arrow_drawing()
            return True

        if key == Qt.Key_Q:
            self._handle_strongs_lookup()
            return True

        if key == Qt.Key_D:
            self.d_key_pressed = True
            return False # Allow bubble for scrolling if not using wheel

        if Qt.Key_1 <= key <= Qt.Key_9:
            scene._apply_symbol_at_mouse(str(key - Qt.Key_0))
            return True
        elif event.text().isdigit() and event.text() != '0':
            scene._apply_symbol_at_mouse(event.text())
            return True
            
        return False

    def handle_key_release(self, event):
        scene = self.scene
        if event.key() == Qt.Key_A and scene.is_drawing_arrow and not event.isAutoRepeat():
            self._finish_arrow_drawing()
            return True
        if event.key() == Qt.Key_D and not event.isAutoRepeat():
            self.d_key_pressed = False
            return False
        return False

    def _handle_copy(self):
        scene = self.scene
        cursor = scene.main_text_item.textCursor()
        if not cursor.hasSelection():
            return
            
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        
        parts = []
        current_pos = start
        doc = scene.main_text_item.document()
        
        import bisect
        s_idx = bisect.bisect_right(scene.pos_verse_map, (start, "zzzzzz"))
        e_idx = bisect.bisect_left(scene.pos_verse_map, (end, ""))
        
        for i in range(s_idx, e_idx):
            v_pos, v_ref = scene.pos_verse_map[i]
            segment_cursor = QTextCursor(doc)
            segment_cursor.setPosition(current_pos)
            segment_cursor.setPosition(v_pos, QTextCursor.KeepAnchor)
            parts.append(segment_cursor.selectedText())
            try:
                v_num = v_ref.split(':')[-1]
                parts.append(f" [{v_num}] ")
            except Exception:
                pass
            current_pos = v_pos
        
        segment_cursor = QTextCursor(doc)
        segment_cursor.setPosition(current_pos)
        segment_cursor.setPosition(end, QTextCursor.KeepAnchor)
        parts.append(segment_cursor.selectedText())
        
        final_text = "".join(parts).replace("\u2029", "\n")
        if not final_text.strip():
            final_text = cursor.selectedText().replace("\u2029", "\n")
        
        if final_text:
            QGuiApplication.clipboard().setText(final_text)

    def handle_wheel(self, event):
        scene = self.scene
        if self.d_key_pressed:
            # Cycle division levels
            scene_pos = event.scenePos()
            delta = event.delta()
            if scene.outline_manager.cycle_divider_at_pos(scene_pos, delta):
                return True
            return True # Still block scrolling even if no divider found
        
        modifiers = event.modifiers()
        delta = event.delta()
        if delta == 0:
            return False

        if modifiers & (Qt.ControlModifier | Qt.AltModifier):
            scene._zoom_accumulator += delta
            while abs(scene._zoom_accumulator) >= 120:
                step = 120 if scene._zoom_accumulator > 0 else -120
                if modifiers & Qt.ControlModifier:
                    scene.target_font_size = max(8, min(72, scene.target_font_size + (2 if step > 0 else -2)))
                elif modifiers & Qt.AltModifier:
                    scene.target_line_spacing = max(1.0, min(3.0, scene.target_line_spacing + (0.1 if step > 0 else -0.1)))
                scene._zoom_accumulator -= step
            scene.settingsPreview.emit(scene.target_font_size, scene.target_line_spacing)
            scene.layout_timer.start()
            return True

        scene._wheel_accumulator += delta
        while abs(scene._wheel_accumulator) >= 30:
            step = 30 if scene._wheel_accumulator > 0 else -30
            move = -(step / 120.0) * (scene.scroll_sens / 100.0)
            scene.target_virtual_scroll_y = max(0, min(len(scene.loader.flat_verses) - 1, scene.target_virtual_scroll_y + move))
            scene._wheel_accumulator -= step
        
        if not scene.scroll_timer.isActive():
            scene.scroll_timer.start()
        return True

    def handle_mouse_move(self, event):
        scene = self.scene
        scene.last_mouse_scene_pos = event.scenePos()
        if scene.outline_manager.handle_mouse_move(event):
            return True
            
        if scene.is_drawing_arrow:
            self._draw_temp_arrow(event.scenePos())
            
        key_at_pos = scene._get_word_key_at_pos(event.scenePos())
        if key_at_pos != self._last_hovered_word_key:
            self._last_hovered_word_key = key_at_pos
            if key_at_pos:
                scene.overlay_manager.on_word_hover(key_at_pos)
            else:
                scene.overlay_manager.on_word_hover_leave()
        
        if scene.strongs_enabled:
            sn_str, _ = scene._get_strongs_at_pos(event.scenePos())
            if sn_str:
                # If we moved significantly or to a different word, reset timer
                diff = event.scenePos() - self.last_strongs_pos
                dist = abs(diff.x()) + abs(diff.y())
                if dist > 10:
                    self.strongs_hover_timer.stop()
                    scene.showStrongsTooltip.emit(event.scenePos(), None) # Hide current
                    self.last_strongs_pos = event.scenePos()
                    self.strongs_hover_timer.start()
            else:
                if self.strongs_hover_timer.isActive():
                    self.strongs_hover_timer.stop()
                scene.showStrongsTooltip.emit(event.scenePos(), None) # Hide current
        return False

    def handle_mouse_press(self, event):
        scene = self.scene
        item = scene.itemAt(event.scenePos(), scene.views()[0].transform())
        from src.scene.components.reader_items import VerseNumberItem, SentenceHandleItem
        if not isinstance(item, VerseNumberItem) and not isinstance(item, SentenceHandleItem):
            scene._clear_verse_selection()
        return False

    def handle_mouse_release(self, event):
        scene = self.scene
        if scene.outline_manager.handle_mouse_release(event):
            return True
        if event.button() != Qt.LeftButton:
            return False
            
        cursor = scene.main_text_item.textCursor()
        if cursor.hasSelection():
            scene.current_selection = (cursor.selectionStart(), cursor.selectionEnd() - cursor.selectionStart())
            view = scene.views()[0]
            screen_pos = view.viewport().mapToGlobal(view.mapFromScene(event.scenePos()))
            scene.showMarkPopup.emit(screen_pos, scene._get_ref_from_pos(cursor.selectionStart()))
        else:
            scene.current_selection = None
        scene.render_verses()
        return False

    def handle_mouse_double_click(self, event):
        return self.scene.outline_manager.handle_double_click(event)

    def handle_context_menu(self, event):
        scene = self.scene
        view = scene.views()[0]
        global_pos = event.screenPos()
        h_data = scene.interaction_manager.get_heading_at_pos(event.scenePos())
        from PySide6.QtGui import QAction
        from src.utils.menu_utils import create_menu
        if h_data:
            menu = create_menu(view)
            suggest_act = QAction("Get suggested symbols", menu)
            suggest_act.triggered.connect(lambda: scene.interaction_manager.show_suggested_symbols_dialog(h_data))
            menu.addAction(suggest_act)
            menu.exec(global_pos)
            return True
            
        from src.scene.components.reader_items import VerseNumberItem
        item = scene.itemAt(event.scenePos(), view.transform())
        if isinstance(item, VerseNumberItem):
            item.contextMenuRequested.emit(QPointF(global_pos))
            return True
            
        cursor = scene.main_text_item.textCursor()
        if not cursor.hasSelection():
            pos = scene.main_text_item.document().documentLayout().hitTest(
                scene.main_text_item.mapFromScene(event.scenePos()), Qt.FuzzyHit
            )
            if pos != -1:
                cursor.setPosition(pos)
                cursor.select(QTextCursor.WordUnderCursor)
                scene.main_text_item.setTextCursor(cursor)
                
        if cursor.hasSelection():
            scene.current_selection = (cursor.selectionStart(), cursor.selectionEnd() - cursor.selectionStart())
            scene.showMarkPopup.emit(global_pos, scene._get_ref_from_pos(cursor.selectionStart()))
            scene.render_verses()
            return True
        return False

    def _handle_strongs_lookup(self):
        scene = self.scene
        mouse_pos = scene.last_mouse_scene_pos
        sn_str, _ = scene._get_strongs_at_pos(mouse_pos)
        if sn_str:
            scene.showStrongsTooltip.emit(mouse_pos, None) # Hide
            sn = sn_str.split()[0]
            entry = scene.strongs_manager.get_entry(sn)
            if entry:
                usages = scene.strongs_manager.get_usages(sn)
                scene.showStrongsVerboseDialog.emit(sn, entry, usages)

    def _handle_delete_key(self):
        scene = self.scene
        view = scene.views()[0]
        mouse_pos = scene.last_mouse_scene_pos
        
        # 1. Check for OutlineDividerItem (Division lines)
        item = scene.itemAt(mouse_pos, view.transform())
        if isinstance(item, OutlineDividerItem):
            if item.parent_node and item.split_idx != -1:
                # Use specialized deletion that handles merging sub-elements
                if scene.study_manager.outline_manager.delete_divider_smart(item.parent_node["id"], item.split_idx):
                    scene._render_outline_overlays()
                    scene.studyDataChanged.emit()
                return # Stop here even if delete was blocked (protected line)

        # 2. Check for other items at pos
        key_str = scene._get_word_key_at_pos(mouse_pos)
        if not key_str: return
        
        modified = False
        scene.study_manager.save_state()
        if key_str in scene.study_manager.data["symbols"]:
            del scene.study_manager.data["symbols"][key_str]
            modified = True

        # Arrow deletion: handle both start-key and end-key (ghost arrows)
        arrows = scene.study_manager.data.get("arrows", {})
        if key_str in arrows:
            del arrows[key_str]
            modified = True
        else:
            # Search for ghost arrows where this word is the end_key
            start_keys_to_remove = []
            for s_key, arrow_list in arrows.items():
                new_list = [
                    a for a in arrow_list
                    if not (a.get('end_key') == key_str and a.get('type') == 'ghost')
                ]
                if len(new_list) < len(arrow_list):
                    modified = True
                    if new_list:
                        arrows[s_key] = new_list
                    else:
                        start_keys_to_remove.append(s_key)
            for sk in start_keys_to_remove:
                del arrows[sk]

        if "logical_marks" in scene.study_manager.data and key_str in scene.study_manager.data["logical_marks"]:
            del scene.study_manager.data["logical_marks"][key_str]
            modified = True
            
        if modified:
            scene.study_manager.save_data()
            scene._render_study_overlays()
            scene.studyDataChanged.emit()

    def _start_arrow_drawing(self):
        scene = self.scene
        mouse_pos = scene.last_mouse_scene_pos
        key_at_pos = scene._get_word_key_at_pos(mouse_pos)
        if key_at_pos:
            scene.arrow_start_key = key_at_pos
            scene.arrow_start_center = scene._get_word_center(key_at_pos)
            if scene.arrow_start_center:
                scene.is_drawing_arrow = True
                self._draw_temp_arrow(mouse_pos)

    def _finish_arrow_drawing(self):
        scene = self.scene
        mouse_pos = scene.last_mouse_scene_pos
        end_key = scene._get_word_key_at_pos(mouse_pos)
        start_key = scene.arrow_start_key

        if not end_key or end_key == start_key:
            scene.is_drawing_arrow = False
            scene.arrow_start_key = None
            scene.arrow_start_center = None
            self._clear_temp_arrow()
            scene._render_study_overlays()
            scene.studyDataChanged.emit()
            return

        # Show type-selection menu at the current cursor position
        view = scene.views()[0]
        screen_pos = view.viewport().mapToGlobal(
            view.mapFromScene(mouse_pos)
        )
        
        from src.utils.menu_utils import create_menu
        menu = create_menu(view, "Arrow Type")
        act_standard = menu.addAction("Standard")
        act_snake    = menu.addAction("Snake")
        act_ghost    = menu.addAction("Ghost")

        chosen = menu.exec(screen_pos)

        # Now clean up drawing state
        scene.is_drawing_arrow = False
        scene.arrow_start_key = None
        scene.arrow_start_center = None
        self._clear_temp_arrow()

        if chosen is None:
            # User dismissed — no arrow created
            scene._render_study_overlays()
            scene.studyDataChanged.emit()
            return

        color = QColor("white")
        color.setAlphaF(0.6)

        if chosen == act_standard:
            arrow_type = "straight"
        elif chosen == act_snake:
            arrow_type = "snake"
        else:
            arrow_type = "ghost"

        scene.study_manager.add_arrow(
            start_key, end_key,
            color.name(QColor.HexArgb),
            arrow_type=arrow_type
        )
        scene._render_study_overlays()
        scene.studyDataChanged.emit()

    def _draw_temp_arrow(self, end_pos):
        scene = self.scene
        self._clear_temp_arrow()
        if not scene.arrow_start_center: return
        color = QColor("white")
        color.setAlphaF(0.5)
        scene.temp_arrow_item = ArrowItem(scene.arrow_start_center, end_pos, color)
        scene.addItem(scene.temp_arrow_item)

    def _clear_temp_arrow(self):
        scene = self.scene
        if scene.temp_arrow_item:
            scene.removeItem(scene.temp_arrow_item)
            scene.temp_arrow_item = None

    def on_strongs_hover_timeout(self):
        scene = self.scene
        if not scene.strongs_enabled: return
        sn_str, _ = scene._get_strongs_at_pos(self.last_strongs_pos)
        if sn_str:
            sn = sn_str.split()[0]
            entry = scene.strongs_manager.get_entry(sn)
            if entry:
                view = scene.views()[0]
                screen_pos = view.viewport().mapToGlobal(view.mapFromScene(self.last_strongs_pos))
                # Emit signal with Strong's data and global position
                scene.showStrongsTooltip.emit(screen_pos, f"{sn}: {entry.get('gloss', '')}")
