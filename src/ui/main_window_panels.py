import uuid
from PySide6.QtWidgets import QDockWidget, QWidget, QSizePolicy
from PySide6.QtCore import Qt

class MainWindowPanelsMixin:
    """Mixin for MainWindow to handle panel management."""
    
    def _add_center_dock(self, title, widget, object_name=None):
        from src.ui.components.outline_panel import OutlinePanel
        from src.ui.components.note_editor import NoteEditor
        from src.ui.components.reading_view_panel import ReadingViewPanel

        dock = QDockWidget(title, self.center_workspace)
        dock.setObjectName(object_name or f"CenterDock_{uuid.uuid4().hex[:8]}")
        # Suppress the default dock title bar with a 0-height empty widget.
        dock.setTitleBarWidget(QWidget())
        
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        dock.setWidget(widget)
        dock.setAttribute(Qt.WA_DeleteOnClose)
        dock.setAllowedAreas(Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea | Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        # Clean up tracked panels safely
        self._clean_center_panels()
        
        if self.center_panels:
            # Find active visible center panels to determine if we are already split
            active_panels = []
            for p in self.center_panels:
                try:
                    if p.isVisible() and not p.isFloating() and not p.visibleRegion().isEmpty():
                        active_panels.append(p)
                except RuntimeError:
                    pass

            if len(active_panels) <= 1:
                # 0 or 1 visible split area -> Split the screen
                target = active_panels[0] if active_panels else self.center_panels[-1]
                self.center_workspace.splitDockWidget(target, dock, Qt.Horizontal)
                self.center_panels.append(dock)
                self._is_applying_preset = True
                self._apply_current_percentages()
            else:
                # >1 split area -> Stack on top based on priority
                target = None
                
                # Priority 1: Outline
                for p in active_panels:
                    if isinstance(p.widget(), OutlinePanel):
                        target = p
                        break
                        
                # Priority 2: Note
                if not target:
                    for p in active_panels:
                        if isinstance(p.widget(), NoteEditor):
                            target = p
                            break
                            
                # Priority 3: Reading View
                if not target:
                    for p in active_panels:
                        if isinstance(p.widget(), ReadingViewPanel):
                            target = p
                            break
                            
                # Fallback: Just use the last active panel
                if not target:
                    target = active_panels[-1]

                self.center_workspace.tabifyDockWidget(target, dock)
                self.center_panels.append(dock)
        else:
            if self.placeholder_dock.isVisible() and not self.placeholder_dock.isFloating():
                self.center_workspace.tabifyDockWidget(self.placeholder_dock, dock)
            else:
                self.center_workspace.addDockWidget(Qt.TopDockWidgetArea, dock)
            self.center_panels.append(dock)
            self._is_applying_preset = True
            self._apply_current_percentages()
        
        # Re-balance whenever this dock moves, floats, or changes visibility
        dock.dockLocationChanged.connect(self._on_dock_location_changed)
        dock.topLevelChanged.connect(self._on_dock_location_changed)
        dock.visibilityChanged.connect(self._on_dock_location_changed)
        
        dock.show()
        dock.raise_()
        return dock

    def _clean_center_panels(self):
        valid_panels = []
        for d in self.center_panels:
            try:
                d.parent()
                valid_panels.append(d)
            except RuntimeError:
                pass
        self.center_panels = valid_panels

    def _on_dock_location_changed(self, *args):
        self._is_applying_preset = True
        self._apply_current_percentages()
        if hasattr(self, 'link_manager'):
            self.link_manager.refresh_connections()
        if hasattr(self, '_update_link_buttons'):
            self._update_link_buttons()

    def _ensure_center_has_panel(self):
        self._clean_center_panels()
        if not self.center_panels:
            self.add_reading_view()

    def _update_dock_tabs(self):
        from PySide6.QtWidgets import QTabBar
        # 1. Update native QTabBar close buttons and hide the placeholder's empty tab slot
        for tb in self.findChildren(QTabBar):
            if not getattr(tb, '_jehu_closable_setup', False):
                tb.setTabsClosable(True)
                tb.tabCloseRequested.connect(self._on_native_tab_close)
                tb._jehu_closable_setup = True
            for i in range(tb.count()):
                if tb.tabText(i).strip() == '':
                    tb.setTabVisible(i, False)

        # 2. Center panels: toggle title bar based on tabified state.
        self._clean_center_panels()
        for p in self.center_panels:
            try:
                p.parent()
                siblings = self.center_workspace.tabifiedDockWidgets(p)
                is_tabified = len(siblings) > 0
                last = getattr(p, '_title_bar_tabified', None)
                if is_tabified != last:
                    p._title_bar_tabified = is_tabified
                    if is_tabified:
                        empty = QWidget()
                        empty._is_suppressor = True
                        p.setTitleBarWidget(empty)
                    else:
                        p.setTitleBarWidget(None)
            except RuntimeError:
                pass

        # 3. Keep pseudo-tabs in sync for the left/right side docks only
        for p in [self.left_dock, self.right_dock]:
            try:
                p.parent()
                tb = p.titleBarWidget()
                if tb and hasattr(tb, 'is_pseudo_tab'):
                    tb.setVisible(p.isVisible() and not p.isFloating())
            except RuntimeError:
                pass

    def _on_native_tab_close(self, index):
        from PySide6.QtWidgets import QTabBar
        tb = self.sender()
        if not isinstance(tb, QTabBar): return
        title = tb.tabText(index).replace('&', '')
        
        all_docks = self.center_panels + [self.left_dock, self.right_dock]
        for p in all_docks:
            try:
                if p.isVisible() and p.windowTitle().replace('&', '') == title:
                    p.close()
                    break
            except RuntimeError:
                pass

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
        dock = self._add_center_dock("Reading View", panel, object_name=object_name)
        
        for p in self.center_panels:
            try:
                p.parent()
                if isinstance(p.widget(), OutlinePanel):
                    is_active = (p.widget().root_node_id == self.main_scene.active_outline_id)
                    p.widget().update_active_state(is_active)
            except RuntimeError:
                pass
        
        scene.studyDataChanged.connect(self.study_panel.dataChanged.emit)
        scene.studyDataChanged.connect(self.study_panel.refresh)
        scene.outlineCreated.connect(self.study_panel.set_active_outline)
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
        
        dock = self._add_center_dock(f"Note - {ref}", editor, object_name=object_name)
        
        editor.jumpRequested.connect(lambda book, ch, vs: self._handle_note_jump(book, ch, vs, dock))
        editor.noteSaved.connect(lambda html: self._on_note_saved(note_key, editor))
        editor.exportRequested.connect(lambda: self.export_manager.trigger_export_dialog("Notes"))
        editor.finished.connect(lambda result: self._on_note_editor_finished(result, editor, note_key, dock))

    def _handle_note_jump(self, book, chapter, verse, note_dock):
        from src.ui.components.reading_view_panel import ReadingViewPanel
        self._clean_center_panels()
        reading_docks = []
        for p in self.center_panels:
            try:
                p.parent()
                if p is note_dock:
                    continue
                if isinstance(p.widget(), ReadingViewPanel):
                    reading_docks.append(p)
            except RuntimeError:
                pass

        if not reading_docks:
            self.add_reading_view()
            self._broadcast_jump(book, chapter, verse)
            return

        reading_dock = reading_docks[0]
        try:
            reading_dock.show()
            reading_dock.raise_()
        except RuntimeError:
            pass

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
            if is_restoring:
                return
            
            from src.ui.components.outline_dialog import OutlineDialog
            dialog = OutlineDialog(self, title="New Outline")
            if dialog.exec():
                data = dialog.get_data()
                if data["title"]:
                    node = self.main_scene.study_manager.outline_manager.create_outline(
                        data["start_ref"], data["end_ref"], data["title"]
                    )
                    outline_id = node["id"]
                    self.main_scene.studyDataChanged.emit()
                else:
                    return
            else:
                return

        panel = OutlinePanel(self.main_scene.study_manager.outline_manager, outline_id)
        panel.jumpRequested.connect(self._broadcast_jump)
        panel.outlineChanged.connect(self.main_scene.studyDataChanged.emit)
        panel.editRequested.connect(self._broadcast_active_outline)
        
        title = "Outline Editor"
        if outline_id:
            node = self.main_scene.study_manager.outline_manager.get_node(outline_id)
            if node:
                title = f"Outline - {node.get('title', 'Unknown')}"
                
        self._add_center_dock(title, panel, object_name=object_name)
        panel.update_active_state(outline_id == self.main_scene.active_outline_id)

    def _close_outline_panel(self, outline_id):
        from src.ui.components.outline_panel import OutlinePanel
        for p in list(self.center_panels):
            try:
                p.parent()
                if isinstance(p.widget(), OutlinePanel):
                    if p.widget().root_node_id == outline_id:
                        p.close()
            except RuntimeError:
                pass
