import uuid
from PySide6.QtWidgets import QDockWidget, QWidget, QSizePolicy
from PySide6.QtCore import Qt

class MainWindowPanelsMixin:
    """Mixin for MainWindow to handle high-level panel creation and orchestration."""
    
    def _ensure_center_has_panel(self):
        self.dock_manager._clean_center_panels()
        if not self.center_panels:
            self.add_reading_view()

    def _clean_center_panels(self):
        self.dock_manager._clean_center_panels()

    def _update_dock_tabs(self):
        try:
            self.dock_manager._update_dock_tabs()
        except Exception: pass

    def add_reading_view(self, object_name=None):
        from src.scene.reader_scene import ReaderScene
        from src.ui.components.reading_view_panel import ReadingViewPanel
        from src.ui.components.outline_panel import OutlinePanel

        shared = {
            'loader': self.main_scene.loader,
            'study_manager': self.main_scene.study_manager,
            'symbol_manager': self.main_scene.symbol_manager,
            'strongs_manager': self.main_scene.strongs_manager
        }
        scene = ReaderScene(self, shared_resources=shared)
        scene.set_strongs_enabled(self.main_scene.strongs_enabled)
        scene.set_outlines_enabled(self.main_scene.outlines_enabled)
        scene.set_active_outline(self.main_scene.active_outline_id)
        
        panel = ReadingViewPanel(scene, self.main_scene.study_manager)
        dock = self.dock_manager._add_center_dock("Reading View", panel, object_name=object_name)
        
        for p in self.center_panels:
            try:
                p.parent()
                if isinstance(p.widget(), OutlinePanel):
                    is_active = (p.widget().root_node_id == self.main_scene.active_outline_id)
                    p.widget().update_active_state(is_active)
            except RuntimeError: pass
        
        scene.studyDataChanged.connect(self.study_panel.dataChanged.emit)
        scene.studyDataChanged.connect(self.study_panel.refresh)
        scene.outlineCreated.connect(self.study_panel.set_active_outline)
        scene.outlineCreated.connect(self.add_outline_panel)
        scene.noteOpenRequested.connect(self.add_note_panel)

    def add_note_panel(self, note_key, ref, object_name=None):
        from src.ui.components.note_editor import NoteEditor
        if not note_key:
            note_key = f"standalone_{uuid.uuid4().hex[:8]}"
            ref = "General Note"
            
        note_data = self.main_scene.study_manager.data["notes"].get(note_key, "")
        existing_text = note_data.get("text", "") if isinstance(note_data, dict) else note_data
        existing_title = note_data.get("title", "") if isinstance(note_data, dict) else ""
        
        editor = NoteEditor(existing_text, ref, initial_title=existing_title)
        editor.setWindowFlags(Qt.Widget)
        editor.note_key = note_key
        editor.ref = ref
        
        dock = self.dock_manager._add_center_dock(f"Note - {ref}", editor, object_name=object_name)
        
        editor.jumpRequested.connect(lambda book, ch, vs: self._handle_note_jump(book, ch, vs, dock))
        editor.noteSaved.connect(lambda html: self._on_note_saved(note_key, editor))
        editor.exportRequested.connect(lambda: self.export_manager.trigger_export_dialog("Notes"))
        editor.finished.connect(lambda result: self._on_note_editor_finished(result, editor, note_key, dock))

    def _handle_note_jump(self, book, chapter, verse, note_dock):
        from src.ui.components.reading_view_panel import ReadingViewPanel
        self.dock_manager._clean_center_panels()
        reading_docks = []
        for p in self.center_panels:
            try:
                p.parent()
                if p is note_dock: continue
                if isinstance(p.widget(), ReadingViewPanel): reading_docks.append(p)
            except RuntimeError: pass

        if not reading_docks:
            self.add_reading_view()
            self._broadcast_jump(book, chapter, verse); return

        reading_dock = reading_docks[0]
        try:
            reading_dock.show(); reading_dock.raise_()
        except RuntimeError: pass
        self._broadcast_jump(book, chapter, verse)

    def _on_note_saved(self, note_key, editor):
        if note_key.startswith("standalone_"):
            self.main_scene.study_manager.data["notes"].setdefault(note_key, {})
            self.main_scene.study_manager.data["notes"][note_key]["title"] = editor.get_title()
            self.main_scene.study_manager.data["notes"][note_key]["text"] = editor.get_text()
            self.main_scene.study_manager.save_data()
        else:
            ref_parts = note_key.split('|')
            if len(ref_parts) >= 4:
                self.main_scene.study_manager.add_note(
                    ref_parts[0], ref_parts[1], ref_parts[2], int(ref_parts[3]),
                    editor.get_text(), editor.get_title()
                )
        self.main_scene._render_study_overlays()
        self.main_scene.studyDataChanged.emit()
        self.study_panel.refresh()

    def _on_note_editor_finished(self, result, editor, note_key, dock):
        from src.ui.components.note_editor import NoteEditor
        if result == NoteEditor.DELETE_CODE:
            self.main_scene.study_manager.delete_note(note_key)
            self.main_scene._render_study_overlays()
            self.main_scene.studyDataChanged.emit()
            dock.close()

    def add_outline_panel(self, outline_id, object_name=None, is_restoring=False):
        from src.ui.components.outline_panel import OutlinePanel
        if not outline_id:
            if is_restoring: return
            from src.ui.components.outline_dialog import OutlineDialog
            dialog = OutlineDialog(self, title="New Outline")
            if dialog.exec():
                data = dialog.get_data()
                if data["title"]:
                    node = self.main_scene.study_manager.outline_manager.create_outline(data["start_ref"], data["end_ref"], data["title"])
                    outline_id = node["id"]; self.main_scene.studyDataChanged.emit()
                else: return
            else: return

        panel = OutlinePanel(self.main_scene.study_manager.outline_manager, outline_id)
        panel.jumpRequested.connect(self._broadcast_jump)
        panel.outlineChanged.connect(self.main_scene.studyDataChanged.emit)
        panel.editRequested.connect(self._broadcast_active_outline)
        
        title = "Outline Editor"
        if outline_id:
            node = self.main_scene.study_manager.outline_manager.get_node(outline_id)
            if node: title = f"Outline - {node.get('title', 'Unknown')}"
                
        self.dock_manager._add_center_dock(title, panel, object_name=object_name)
        panel.update_active_state(outline_id == self.main_scene.active_outline_id)

    def _close_outline_panel(self, outline_id):
        from src.ui.components.outline_panel import OutlinePanel
        for p in list(self.center_panels):
            try:
                p.parent()
                if isinstance(p.widget(), OutlinePanel) and p.widget().root_node_id == outline_id: p.close()
            except RuntimeError: pass
