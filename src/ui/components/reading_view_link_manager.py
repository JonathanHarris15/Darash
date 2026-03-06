from PySide6.QtCore import QObject, Signal

class ReadingViewLinkManager(QObject):
    link_state_changed = Signal()

    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self._unlinked_docks = set()
        self._connected_scenes = set()
        self._syncing_scroll = False

    def get_master_panel(self):
        """Returns the leftmost, non-floating, non-tabified ReadingViewPanel."""
        best_dock = None
        best_x = float('inf')
        
        for dock in self.main_window.center_panels:
            try:
                dock.parent()
                if dock.isFloating() or not dock.isVisible():
                    continue
                # Tabified panels behind the active tab shouldn't be master
                # Actually, any visible non-floating panel could be master if it's leftmost.
                # In Qt, geometry().x() tells us visual order relatively well in a layout.
                geo = dock.geometry()
                if geo.x() < best_x:
                    best_x = geo.x()
                    best_dock = dock
            except RuntimeError:
                pass
                
        if best_dock:
            from src.ui.components.reading_view_panel import ReadingViewPanel
            widget = best_dock.widget()
            if isinstance(widget, ReadingViewPanel):
                return best_dock, widget.reader_widget.scene
                
        return None, None

    def is_linked(self, dock):
        return dock not in self._unlinked_docks

    def set_linked(self, dock, linked: bool):
        if linked:
            self._unlinked_docks.discard(dock)
            # Instantly jump the follower to the master's exact scroll position
            _, master_scene = self.get_master_panel()
            if master_scene:
                follower_scene = dock.widget().reader_widget.scene
                follower_scene.set_scroll_y(master_scene.virtual_scroll_y)
        else:
            self._unlinked_docks.add(dock)
        self.link_state_changed.emit()
        self.refresh_bookmark_visibility()

    def refresh_bookmark_visibility(self):
        master_dock, _ = self.get_master_panel()
        for dock in self.main_window.center_panels:
            try:
                dock.parent()
                from src.ui.components.reading_view_panel import ReadingViewPanel
                widget = dock.widget()
                if isinstance(widget, ReadingViewPanel):
                    if dock == master_dock:
                        widget.bookmark_sidebar.setVisible(True)
                    else:
                        is_follower_linked = self.is_linked(dock)
                        # Hide bookmarks if it's a linked follower, show if unlinked
                        widget.bookmark_sidebar.setVisible(not is_follower_linked)
            except RuntimeError:
                pass

    def refresh_connections(self):
        # We now connect to ALL active ReadingViewPanels' scenes to allow
        # bidirectional scrolling.
        
        current_scenes = set()
        for dock in self.main_window.center_panels:
            try:
                dock.parent()
                from src.ui.components.reading_view_panel import ReadingViewPanel
                if isinstance(dock.widget(), ReadingViewPanel):
                    scene = dock.widget().reader_widget.scene
                    current_scenes.add(scene)
            except RuntimeError:
                pass
                
        # Disconnect any old scenes that were closed
        for scene in list(self._connected_scenes):
            if scene not in current_scenes:
                try:
                    scene.scrollChanged.disconnect(self._on_any_scroll_changed)
                except (RuntimeError, TypeError):
                    pass
                self._connected_scenes.remove(scene)
                
        # Connect new scenes
        for scene in current_scenes:
            if scene not in self._connected_scenes:
                scene.scrollChanged.connect(lambda v, s=scene: self._on_any_scroll_changed(s))
                self._connected_scenes.add(scene)
            
        self.refresh_bookmark_visibility()
            
    def _on_any_scroll_changed(self, source_scene):
        if self._syncing_scroll:
            return
            
        # Is the source scene panel linked? If not, its scrolling stays private.
        source_dock = None
        for dock in self.main_window.center_panels:
            try:
                dock.parent()
                if getattr(dock.widget(), 'reader_widget', None) and dock.widget().reader_widget.scene == source_scene:
                    source_dock = dock
                    break
            except RuntimeError:
                pass
                
        if not source_dock or not self.is_linked(source_dock):
            return
            
        target_y = source_scene.virtual_scroll_y
        
        # We are syncing, set flag to prevent infinite loops
        self._syncing_scroll = True
        try:
            for dock in self.main_window.center_panels:
                try:
                    dock.parent()
                    if dock == source_dock:
                        continue
                        
                    if self.is_linked(dock):
                        from src.ui.components.reading_view_panel import ReadingViewPanel
                        if isinstance(dock.widget(), ReadingViewPanel):
                            scene = dock.widget().reader_widget.scene
                            if scene.virtual_scroll_y != target_y:
                                scene.target_virtual_scroll_y = target_y
                                scene.virtual_scroll_y = target_y
                                scene.check_chunk_boundaries()
                                scene._sync_physical_scroll()
                except RuntimeError:
                    pass
        finally:
            self._syncing_scroll = False
