import uuid
from PySide6.QtWidgets import QDockWidget, QWidget, QSizePolicy, QTabBar
from PySide6.QtCore import Qt

class MainWindowDockManager:
    """Handles low-level dock tracking, cleanup, and layout re-balancing."""
    
    def __init__(self, main_window):
        self.mw = main_window

    def _add_center_dock(self, title, widget, object_name=None):
        from src.ui.components.outline_panel import OutlinePanel
        from src.ui.components.note_editor import NoteEditor
        from src.ui.components.reading_view_panel import ReadingViewPanel

        dock = QDockWidget(title, self.mw.center_workspace)
        dock.setObjectName(object_name or f"CenterDock_{uuid.uuid4().hex[:8]}")
        dock.setTitleBarWidget(QWidget()) # Empty title bar
        
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        dock.setWidget(widget)
        dock.setAttribute(Qt.WA_DeleteOnClose)
        dock.setAllowedAreas(Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea | Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        self._clean_center_panels()
        
        if self.mw.center_panels:
            active_panels = []
            for p in self.mw.center_panels:
                try:
                    if p.isVisible() and not p.isFloating() and not p.visibleRegion().isEmpty():
                        active_panels.append(p)
                except RuntimeError: pass

            if len(active_panels) <= 1:
                target = active_panels[0] if active_panels else self.mw.center_panels[-1]
                self.mw.center_workspace.splitDockWidget(target, dock, Qt.Horizontal)
                self.mw.center_panels.append(dock)
                self.mw._is_applying_preset = True
                self.mw._apply_current_percentages()
            else:
                target = None
                for p in active_panels:
                    if isinstance(p.widget(), OutlinePanel): target = p; break
                if not target:
                    for p in active_panels:
                        if isinstance(p.widget(), NoteEditor): target = p; break
                if not target:
                    for p in active_panels:
                        if isinstance(p.widget(), ReadingViewPanel): target = p; break
                if not target: target = active_panels[-1]

                self.mw.center_workspace.tabifyDockWidget(target, dock)
                self.mw.center_panels.append(dock)
        else:
            if self.mw.placeholder_dock.isVisible() and not self.mw.placeholder_dock.isFloating():
                self.mw.center_workspace.tabifyDockWidget(self.mw.placeholder_dock, dock)
            else:
                self.mw.center_workspace.addDockWidget(Qt.TopDockWidgetArea, dock)
            self.mw.center_panels.append(dock)
            self.mw._is_applying_preset = True
            self.mw._apply_current_percentages()
        
        dock.dockLocationChanged.connect(self._on_dock_location_changed)
        dock.topLevelChanged.connect(self._on_dock_location_changed)
        dock.visibilityChanged.connect(self._on_dock_location_changed)
        
        dock.show(); dock.raise_()
        return dock

    def _clean_center_panels(self):
        valid = []
        for d in self.mw.center_panels:
            try:
                d.parent(); valid.append(d)
            except RuntimeError: pass
        self.mw.center_panels = valid

    def _on_dock_location_changed(self, *args):
        self.mw._is_applying_preset = True
        self.mw._apply_current_percentages()
        if hasattr(self.mw, 'link_manager'): self.mw.link_manager.refresh_connections()
        if hasattr(self.mw, '_update_link_buttons'): self.mw._update_link_buttons()

    def _update_dock_tabs(self):
        for tb in self.mw.findChildren(QTabBar):
            if not getattr(tb, '_jehu_closable_setup', False):
                tb.setTabsClosable(True); tb.tabCloseRequested.connect(self._on_native_tab_close); tb._jehu_closable_setup = True
            for i in range(tb.count()):
                if tb.tabText(i).strip() == '': tb.setTabVisible(i, False)

        self._clean_center_panels()
        for p in self.mw.center_panels:
            try:
                p.parent(); siblings = self.mw.center_workspace.tabifiedDockWidgets(p)
                is_tabified = len(siblings) > 0
                if is_tabified != getattr(p, '_title_bar_tabified', None):
                    p._title_bar_tabified = is_tabified
                    p.setTitleBarWidget(QWidget() if is_tabified else None)
            except RuntimeError: pass

        for p in [self.mw.left_dock, self.mw.right_dock]:
            try:
                p.parent(); tb = p.titleBarWidget()
                if tb and hasattr(tb, 'is_pseudo_tab'): tb.setVisible(p.isVisible() and not p.isFloating())
            except RuntimeError: pass

    def _on_native_tab_close(self, index):
        tb = self.mw.sender()
        if not isinstance(tb, QTabBar): return
        title = tb.tabText(index).replace('&', '').strip()
        
        # Find the dock that matches this title.
        # We search center panels and side docks. 
        # We don't check p.isVisible() because inactive tabs are not visible.
        for p in self.mw.center_panels + [self.mw.left_dock, self.mw.right_dock]:
            try:
                if p.windowTitle().replace('&', '').strip() == title:
                    p.close()
                    break
            except RuntimeError: pass
