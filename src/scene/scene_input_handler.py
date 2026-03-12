from PySide6.QtCore import Qt, QPointF, QObject, QTimer
from PySide6.QtGui import QColor, QCursor, QTextCursor, QGuiApplication
from src.scene.scene_study_input_handler import SceneStudyInputHandler

class SceneInputHandler(QObject):
    """Primary input coordinator for ReaderScene. Delegates study specifics."""
    def __init__(self, scene):
        super().__init__(); self.scene = scene; self.d_key_pressed = False
        self.study_handler = SceneStudyInputHandler(scene, self)
        self.strongs_hover_timer = QTimer(self); self.strongs_hover_timer.setSingleShot(True)
        self.strongs_hover_timer.setInterval(500); self.strongs_hover_timer.timeout.connect(self.on_strongs_hover_timeout)
        self.last_strongs_pos, self._last_hovered_word_key = QPointF(), None

    def handle_key_press(self, event):
        key, mods, s = event.key(), event.modifiers(), self.scene
        if key == Qt.Key_C and (mods & Qt.ControlModifier): self._handle_copy(); return True
        if key == Qt.Key_Z and (mods & Qt.ControlModifier):
            if s.study_manager.undo(): s._render_study_overlays(); s.studyDataChanged.emit()
            return True
        if key in (Qt.Key_Delete, Qt.Key_Backspace): self.study_handler.handle_delete_key(); return True
        if key == Qt.Key_A and not s.is_drawing_arrow and not event.isAutoRepeat(): self.study_handler.start_arrow_drawing(); return True
        if key == Qt.Key_Q: self.study_handler.handle_strongs_lookup(); return True
        if key == Qt.Key_D: self.d_key_pressed = True; return False
        if Qt.Key_1 <= key <= Qt.Key_9: s._apply_symbol_at_mouse(str(key - Qt.Key_0)); return True
        return False

    def handle_key_release(self, event):
        if event.key() == Qt.Key_A and self.scene.is_drawing_arrow and not event.isAutoRepeat():
            self.study_handler.finish_arrow_drawing(); return True
        if event.key() == Qt.Key_D and not event.isAutoRepeat(): self.d_key_pressed = False; return False
        return False

    def handle_wheel(self, event):
        s = self.scene; d = event.delta()
        if self.d_key_pressed: return s.outline_manager.cycle_divider_at_pos(event.scenePos(), d) or True
        if not (event.modifiers() & (Qt.ControlModifier | Qt.AltModifier)):
            s._wheel_accumulator += d
            while abs(s._wheel_accumulator) >= 30:
                step = 30 if s._wheel_accumulator > 0 else -30
                move = -(step / 120.0) * (s.scroll_sens / 100.0)
                s.target_virtual_scroll_y = max(0, min(len(s.loader.flat_verses)-1, s.target_virtual_scroll_y + move))
                s._wheel_accumulator -= step
            if not s.state_manager.scroll_timer.isActive():
                s.state_manager.scroll_timer.start()
            return True
        s._zoom_accumulator += d
        while abs(s._zoom_accumulator) >= 120:
            step = 120 if s._zoom_accumulator > 0 else -120
            if event.modifiers() & Qt.ControlModifier: s.target_font_size = max(8, min(72, s.target_font_size + (2 if step > 0 else -2)))
            else: s.target_line_spacing = max(1.0, min(3.0, s.target_line_spacing + (0.1 if step > 0 else -0.1)))
            s._zoom_accumulator -= step
        s.settingsPreview.emit(s.target_font_size, s.target_line_spacing); s.layout_timer.start(); return True

    def handle_mouse_move(self, event):
        s = self.scene; s.last_mouse_scene_pos = event.scenePos()
        if s.outline_manager.handle_mouse_move(event): return True
        if s.is_drawing_arrow: self.study_handler.draw_temp_arrow(event.scenePos())
        key = s._get_word_key_at_pos(event.scenePos())
        if key != self._last_hovered_word_key:
            self._last_hovered_word_key = key; s.overlay_manager.on_word_hover(key) if key else s.overlay_manager.on_word_hover_leave()
        if s.strongs_enabled:
            sn_str, _ = s._get_strongs_at_pos(event.scenePos())
            if sn_str:
                if (event.scenePos() - self.last_strongs_pos).manhattanLength() > 10:
                    self.strongs_hover_timer.stop(); s.showStrongsTooltip.emit(event.scenePos(), None)
                    self.last_strongs_pos = event.scenePos(); self.strongs_hover_timer.start()
            else: self.strongs_hover_timer.stop(); s.showStrongsTooltip.emit(event.scenePos(), None)
        return False

    def handle_mouse_press(self, event):
        from src.scene.components.reader_items import VerseNumberItem, SentenceHandleItem
        if not isinstance(self.scene.itemAt(event.scenePos(), self.scene.views()[0].transform()), (VerseNumberItem, SentenceHandleItem)):
            self.scene._clear_verse_selection()
        return False

    def handle_mouse_release(self, event):
        s = self.scene
        if s.outline_manager.handle_mouse_release(event): return True
        if event.button() != Qt.LeftButton: return False
        c = s.main_text_item.textCursor()
        if c.hasSelection():
            s.current_selection = (c.selectionStart(), c.selectionEnd() - c.selectionStart())
            v = s.views()[0]; s.showMarkPopup.emit(v.viewport().mapToGlobal(v.mapFromScene(event.scenePos())), s._get_ref_from_pos(c.selectionStart()))
        else: s.current_selection = None
        s.render_verses(); return False

    def handle_mouse_double_click(self, e): return self.scene.outline_manager.handle_double_click(e)
    def handle_context_menu(self, e):
        s, v, p = self.scene, self.scene.views()[0], e.screenPos()
        h = s.interaction_manager.get_heading_at_pos(e.scenePos())
        if h:
            from src.utils.menu_utils import create_menu; m = create_menu(v)
            m.addAction("Get suggested symbols").triggered.connect(lambda: s.interaction_manager.show_suggested_symbols_dialog(h))
            m.exec(p); return True
        from src.scene.components.reader_items import VerseNumberItem
        i = s.itemAt(e.scenePos(), v.transform())
        if isinstance(i, VerseNumberItem): i.contextMenuRequested.emit(QPointF(p)); return True
        c = s.main_text_item.textCursor()
        if not c.hasSelection() and (pos := s.main_text_item.document().documentLayout().hitTest(s.main_text_item.mapFromScene(e.scenePos()), Qt.FuzzyHit)) != -1:
            c.setPosition(pos); c.select(QTextCursor.WordUnderCursor); s.main_text_item.setTextCursor(c)
        if c.hasSelection():
            s.current_selection = (c.selectionStart(), c.selectionEnd() - c.selectionStart())
            s.showMarkPopup.emit(p, s._get_ref_from_pos(c.selectionStart())); s.render_verses(); return True
        return False

    def on_strongs_hover_timeout(self):
        s = self.scene; sn_str, _ = s._get_strongs_at_pos(self.last_strongs_pos)
        if s.strongs_enabled and sn_str:
            sn = sn_str.split()[0]; entry = s.strongs_manager.get_entry(sn)
            if entry:
                v = s.views()[0]; p = v.viewport().mapToGlobal(v.mapFromScene(self.last_strongs_pos))
                s.showStrongsTooltip.emit(p, f"{sn}: {entry.get('gloss', '')}")

    def _handle_copy(self):
        s = self.scene; c = s.main_text_item.textCursor()
        if not c.hasSelection(): return
        st, en, d, parts = c.selectionStart(), c.selectionEnd(), s.main_text_item.document(), []
        import bisect; sits, eits = bisect.bisect_right(s.pos_verse_map, (st, "zzzzzz")), bisect.bisect_left(s.pos_verse_map, (en, ""))
        curr = st
        for i in range(sits, eits):
            vp, vr = s.pos_verse_map[i]; sc = QTextCursor(d); sc.setPosition(curr); sc.setPosition(vp, QTextCursor.KeepAnchor)
            parts.append(sc.selectedText()); parts.append(f" [{vr.split(':')[-1]}] "); curr = vp
        sc = QTextCursor(d); sc.setPosition(curr); sc.setPosition(en, QTextCursor.KeepAnchor); parts.append(sc.selectedText())
        t = "".join(parts).replace("\u2029", "\n")
        QGuiApplication.clipboard().setText(t if t.strip() else c.selectedText().replace("\u2029", "\n"))
