import os
import uuid
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QInputDialog, QFileDialog,
    QDockWidget, QSplitter, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QToolBar, QSizePolicy
)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt

from src.ui.components.navigation import NavigationDock
from src.ui.components.symbol_dialog import SymbolDialog
from src.ui.components.study_panel import StudyPanel
from src.ui.components.appearance_panel import AppearancePanel
from src.ui.components.activity_bar import ActivityBar
from src.ui.components.reading_view_panel import ReadingViewPanel
from src.ui.components.note_editor import NoteEditor
from src.ui.components.outline_panel import OutlinePanel
from src.ui.components.placeholder_panel import PlaceholderPanel
from src.ui.components.pseudo_tab_title_bar import PseudoTabTitleBar

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._is_applying_preset = True
        # Load global settings before scene init
        # self._load_global_layout_settings()

        # To keep scene logic simple during transition, we instantiate one primary ReadingViewPanel first 
        # to ensure there is a single source of truth for the 'scene' object.
        from src.scene.reader_scene import ReaderScene
        self.main_scene = ReaderScene()
        
        self.setWindowTitle("Jehu Reader")

        # Main Layout Structure
        # Create a nested QMainWindow to act as a sandbox for the central docks
        self.center_workspace = QMainWindow()
        self.center_workspace.setObjectName("CenterWorkspace")
        self.setCentralWidget(self.center_workspace)
        
        # Force the main window and center workspace into Document Mode so docks natively render as tabs
        self.setDocumentMode(True)
        self.center_workspace.setDocumentMode(True)
        
        # 1. Activity Bar (Far Left ToolBar)
        self.toolbar = QToolBar("Activity Bar")
        self.toolbar.setObjectName("ActivityBar")
        self.toolbar.setMovable(False)
        self.activity_bar = ActivityBar()
        self.toolbar.addWidget(self.activity_bar)
        self.addToolBar(Qt.LeftToolBarArea, self.toolbar)
        
        # Keep track of active central panels
        self.center_panels = []
        
        from src.ui.components.reading_view_link_manager import ReadingViewLinkManager
        self.link_manager = ReadingViewLinkManager(self)
        self.split_link_buttons = []

        # Setup Docks
        self.setup_docks()
        
        # Load and restore layout MUST happen after docks are created but before connections
        self._load_and_restore_layout()
        
        # Setup Connections
        self.setup_connections()
        
        # Appearance Dialog (Standalone window)
        self.appearance_dialog = AppearancePanel(self.main_scene, self)
        self.appearance_dialog.settingsChanged.connect(self._broadcast_appearance_settings)
        
        # Export Manager
        from src.utils.export_manager import ExportManager
        self.export_manager = ExportManager(self)
        
        # Menu Bar
        self.setup_menu()
        
        self.left_dock.installEventFilter(self)
        self.right_dock.installEventFilter(self)
        self._is_applying_preset = False
        
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, self._apply_current_percentages)
        
        # Continuously monitor for native QTabBars and dynamically hide pseudo-tabs when tabbed natively
        self._tab_update_timer = QTimer(self)
        self._tab_update_timer.timeout.connect(self._update_dock_tabs)
        self._tab_update_timer.start(50)
        
        self._link_button_timer = QTimer(self)
        self._link_button_timer.timeout.connect(self._update_link_buttons)
        self._link_button_timer.start(200)

    def _update_link_buttons(self):
        # Clean up old
        for btn in self.split_link_buttons:
            btn.setParent(None)
            btn.deleteLater()
        self.split_link_buttons.clear()
        
        # Find active (frontmost) visible center panels sorted left-to-right
        active_panels = []
        for p in self.center_panels:
            try:
                p.parent()
                if not p.isVisible() or p.isFloating(): continue
                # isVisible() is True for background tabs, but visibleRegion() is empty if hidden by a tab
                if not p.visibleRegion().isEmpty():
                    active_panels.append(p)
            except RuntimeError:
                pass
                
        active_panels.sort(key=lambda p: p.geometry().x())
        
        from src.ui.components.reading_view_panel import ReadingViewPanel
        from src.ui.components.split_link_button import SplitLinkButton
        
        for i in range(len(active_panels) - 1):
            left = active_panels[i]
            right = active_panels[i+1]
            
            if isinstance(left.widget(), ReadingViewPanel) and isinstance(right.widget(), ReadingViewPanel):
                btn = SplitLinkButton(left, right, self.link_manager, self.center_workspace)
                self.split_link_buttons.append(btn)
                btn.reposition()
                btn.raise_()

    def _load_and_restore_layout(self):
        from PySide6.QtCore import QSettings
        import json
        settings = QSettings("JehuReader", "MainWindow")
        
        try:
            self._left_dock_pct = float(settings.value("left_dock_pct", 0.10))
            self._right_dock_pct = float(settings.value("right_dock_pct", 0.10))
        except (ValueError, TypeError):
            self._left_dock_pct = 0.10
            self._right_dock_pct = 0.10
            
        geom = settings.value("geometry")
        if geom:
            self.restoreGeometry(geom)
        else:
            self.resize(1400, 900)
            
        panels_json = settings.value("center_panels_state")
        restored_any = False
        if panels_json:
            try:
                panels_state = json.loads(panels_json)
                for state in panels_state:
                    p_type = state.get("type")
                    p_name = state.get("objectName")

                    if p_type == "ReadingView":
                        self.add_reading_view(object_name=p_name)
                        restored_any = True
                    elif p_type == "Note":
                        self.add_note_panel(state.get("note_key"), state.get("ref"), object_name=p_name)
                        restored_any = True
                    elif p_type == "Outline":
                        outline_id = state.get("outline_id")
                        if outline_id:
                            self.add_outline_panel(outline_id, object_name=p_name, is_restoring=True)
                            restored_any = True
            except Exception as e:
                print("Failed to restore panels:", e)

        # Open a Reading View if nothing was restored (fresh install, placeholder-only,
        # or a corrupted/empty saved layout).
        if not restored_any:
            self.add_reading_view()

        state = settings.value("windowState")
        if state:
            self.restoreState(state)

        # Only restore the center workspace Qt dock state when there are panels
        # that match it. If we fell back to a fresh Reading View, restoring the
        # old dock state would immediately hide it behind the placeholder layout.
        if restored_any:
            center_state = settings.value("center_workspace_state")
            if center_state:
                self.center_workspace.restoreState(center_state)

        self._is_applying_preset = False

        # Deferred safety net: runs after the event loop starts and the window is
        # fully shown. If somehow the center is still empty (e.g. restoreState ate
        # the newly added dock), add a fresh Reading View.
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self._ensure_center_has_panel)

    def setup_docks(self):
        from PySide6.QtWidgets import QTabWidget
        # Sandbox for the center workspace
        self.center_workspace.setDockNestingEnabled(True)
        self.center_workspace.setDockOptions(
            QMainWindow.AnimatedDocks
            | QMainWindow.AllowNestedDocks
            | QMainWindow.AllowTabbedDocks
            | QMainWindow.GroupedDragging
            # NOTE: ForceTabbedDocks removed — required for drag-to-split
        )
        self.center_workspace.setTabPosition(Qt.AllDockWidgetAreas, QTabWidget.North)
        
        # Ensure left and right docks extend top-to-bottom completely
        self.setCorner(Qt.TopLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.BottomLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.TopRightCorner, Qt.RightDockWidgetArea)
        self.setCorner(Qt.BottomRightCorner, Qt.RightDockWidgetArea)
        
        # Left Dock: Bible Directory
        self.left_dock = QDockWidget("Bible Directory", self)
        self.left_dock.setObjectName("LeftDock")
        self.left_dock.setTitleBarWidget(PseudoTabTitleBar("Bible Directory", self.left_dock, self))
        self.left_dock.setAllowedAreas(Qt.LeftDockWidgetArea)
        self.left_dock.setFeatures(QDockWidget.DockWidgetClosable)
        
        self.nav_dock = NavigationDock(self.main_scene.loader)
        self.nav_dock.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.left_dock.setWidget(self.nav_dock)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.left_dock)
        
        # Right Dock: Study Overview
        self.right_dock = QDockWidget("Study Overview", self)
        self.right_dock.setObjectName("RightDock")
        self.right_dock.setTitleBarWidget(PseudoTabTitleBar("Study Overview", self.right_dock, self))
        self.right_dock.setAllowedAreas(Qt.RightDockWidgetArea)
        self.right_dock.setFeatures(QDockWidget.DockWidgetClosable)
        
        self.study_panel = StudyPanel(self.main_scene.study_manager, self.main_scene.symbol_manager)
        self.study_panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.right_dock.setWidget(self.study_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, self.right_dock)
        
        # Placeholder Dock -> Goes in Center Workspace
        self.placeholder_dock = QDockWidget("", self.center_workspace)
        self.placeholder_dock.setObjectName("PlaceholderDock")
        self.placeholder_dock.setTitleBarWidget(QWidget())
        self.placeholder_dock.setWidget(PlaceholderPanel(self))
        self.placeholder_dock.setAllowedAreas(Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea | Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.placeholder_dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.center_workspace.addDockWidget(Qt.TopDockWidgetArea, self.placeholder_dock)
        
        # Sync Activity Bar with dock visibility
        self.left_dock.visibilityChanged.connect(self.activity_bar.btn_bible.setChecked)
        self.right_dock.visibilityChanged.connect(self.activity_bar.btn_study.setChecked)

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.Resize:
            if obj in (self.left_dock, self.right_dock) and not getattr(self, '_is_applying_preset', False):
                total_w = float(max(1, self.width()))
                if self.left_dock.isVisible() and not self.left_dock.isFloating():
                    self._left_dock_pct = self.left_dock.width() / total_w
                if self.right_dock.isVisible() and not self.right_dock.isFloating():
                    self._right_dock_pct = self.right_dock.width() / total_w
        return super().eventFilter(obj, event)
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_left_dock_pct') and event.oldSize().isValid() and event.oldSize().width() != event.size().width():
            # Apply proportionally
            self._is_applying_preset = True
            from PySide6.QtCore import QTimer
            QTimer.singleShot(10, self._apply_current_percentages)

    def _clean_center_panels(self):
        valid_panels = []
        for d in self.center_panels:
            try:
                # Accessing any method raises RuntimeError if C++ object deleted
                d.parent()
                valid_panels.append(d)
            except RuntimeError:
                pass
        self.center_panels = valid_panels

    def _apply_current_percentages(self):
        total_w = self.width()
        left_w = max(1, int(total_w * self._left_dock_pct))
        right_w = max(1, int(total_w * self._right_dock_pct))
        
        self._clean_center_panels()
        real_centers = [p for p in self.center_panels if p.isVisible() and not p.isFloating()]
        
        used_w = 0
        widgets = []
        sizes = []
        
        outer_docks = []
        outer_sizes = []
        
        if self.left_dock.isVisible() and not self.left_dock.isFloating():
            outer_docks.append(self.left_dock)
            outer_sizes.append(left_w)
            used_w += left_w
            
        if self.right_dock.isVisible() and not self.right_dock.isFloating():
            outer_docks.append(self.right_dock)
            outer_sizes.append(right_w)
            used_w += right_w
            
        if outer_docks:
            self.resizeDocks(outer_docks, outer_sizes, Qt.Horizontal)
            
        center_w = max(1, total_w - used_w)
            
        if not real_centers:
            self.placeholder_dock.show()
        else:
            self.placeholder_dock.hide()
            inner_docks = []
            inner_sizes = []
            per_center_w = max(1, center_w // len(real_centers))
            for p in real_centers:
                inner_docks.append(p)
                inner_sizes.append(per_center_w)
                
            if inner_docks:
                self.center_workspace.resizeDocks(inner_docks, inner_sizes, Qt.Horizontal)
        
        self._is_applying_preset = False

    def setup_connections(self):
        # Activity Bar
        self.activity_bar.toggleBibleDir.connect(self._toggle_left_dock)
        self.activity_bar.toggleStudyOverview.connect(self._toggle_right_dock)
        
        self.activity_bar.openReadingView.connect(self.add_reading_view)
        self.activity_bar.openNotesPanel.connect(lambda: self.add_note_panel("", ""))
        self.activity_bar.openOutlinePanel.connect(lambda: self.add_outline_panel(None))

        # Panel Navigation & Synchronized State
        self.nav_dock.jumpRequested.connect(self._broadcast_jump)
        self.nav_dock.strongsToggled.connect(self._broadcast_strongs_enabled)
        self.nav_dock.outlinesToggled.connect(self._broadcast_outlines_enabled)
        
        self.study_panel.jumpRequested.connect(self._broadcast_jump)
        self.study_panel.noteOpenRequested.connect(self.add_note_panel)
        self.study_panel.outlineOpenRequested.connect(self.add_outline_panel)
        self.study_panel.outlineDeleted.connect(self._close_outline_panel)
        self.study_panel.activeOutlineChanged.connect(self._broadcast_active_outline)
        
        # Render updates
        self.study_panel.dataChanged.connect(self._render_all_study_data)
        
        self.main_scene.studyDataChanged.connect(self.study_panel.refresh)
        self.main_scene.outlineCreated.connect(self.study_panel.set_active_outline)
        self.main_scene.noteOpenRequested.connect(self.add_note_panel)

    def _broadcast_appearance_settings(self):
        """Copy all appearance settings from main_scene to every secondary reading view."""
        src = self.main_scene
        for p in self.center_panels:
            try:
                p.parent()
                widget = p.widget()
                if not isinstance(widget, ReadingViewPanel):
                    continue
                scene = widget.reader_widget.scene
                if scene is src:
                    continue
                # Copy target values
                scene.target_font_size = src.target_font_size
                scene.target_font_family = src.target_font_family
                scene.target_line_spacing = src.target_line_spacing
                scene.target_verse_num_size = src.target_verse_num_size
                scene.target_side_margin = src.target_side_margin
                scene.target_tab_size = src.target_tab_size
                scene.target_arrow_opacity = src.target_arrow_opacity
                scene.target_verse_mark_size = src.target_verse_mark_size
                scene.target_logical_mark_opacity = src.target_logical_mark_opacity
                scene.target_sentence_break_enabled = src.target_sentence_break_enabled
                scene.text_color = src.text_color
                scene.ref_color = src.ref_color
                scene.logical_mark_color = src.logical_mark_color
                scene.setBackgroundBrush(src.backgroundBrush())
                scene.apply_layout_changes()
            except RuntimeError:
                pass

    def _render_all_study_data(self):
        """Broadcast study panel data changes to all active reading scenes."""
        self.main_scene._render_study_overlays()
        self.main_scene._render_outline_overlays()
        self.main_scene.render_verses()
        
        for p in self.center_panels:
            try:
                p.parent()
                widget = p.widget()
                if isinstance(widget, ReadingViewPanel):
                    scene = widget.reader_widget.scene
                    if scene != self.main_scene:
                        scene._render_study_overlays()
                        scene._render_outline_overlays()
                        scene.render_verses()
                elif isinstance(widget, OutlinePanel):
                    widget.refresh()
            except RuntimeError:
                pass

    def _broadcast_jump(self, book, chapter, verse):
        jumped = False
        for p in self.center_panels:
            try:
                p.parent()
                if p.isVisible() and isinstance(p.widget(), ReadingViewPanel):
                    p.widget().reader_widget.scene.jump_to(book, chapter, verse)
                    jumped = True
                    break
            except RuntimeError:
                pass
        if not jumped:
            self.add_reading_view()
            self._broadcast_jump(book, chapter, verse)

    def _broadcast_active_outline(self, outline_id):
        self.main_scene.set_active_outline(outline_id)
        self.study_panel.set_active_outline(outline_id, emit_signal=False)
        for p in self.center_panels:
            try:
                p.parent()
                if isinstance(p.widget(), ReadingViewPanel):
                    p.widget().reader_widget.scene.set_active_outline(outline_id)
                elif isinstance(p.widget(), OutlinePanel):
                    is_active = (p.widget().root_node_id == outline_id)
                    p.widget().update_active_state(is_active)
            except RuntimeError:
                pass

    def _close_outline_panel(self, outline_id):
        for p in list(self.center_panels): # Copy list since closing modifies it
            try:
                p.parent()
                if isinstance(p.widget(), OutlinePanel):
                    if p.widget().root_node_id == outline_id:
                        p.close()
            except RuntimeError:
                pass

    def _broadcast_strongs_enabled(self, enabled):
        self.main_scene.set_strongs_enabled(enabled)
        for p in self.center_panels:
            try:
                p.parent()
                if isinstance(p.widget(), ReadingViewPanel):
                    p.widget().reader_widget.scene.set_strongs_enabled(enabled)
            except RuntimeError:
                pass

    def _broadcast_outlines_enabled(self, enabled):
        self.main_scene.set_outlines_enabled(enabled)
        for p in self.center_panels:
            try:
                p.parent()
                if isinstance(p.widget(), ReadingViewPanel):
                    p.widget().reader_widget.scene.set_outlines_enabled(enabled)
            except RuntimeError:
                pass

    # --- Panel Management ---
    def _add_center_dock(self, title, widget, object_name=None):
        dock = QDockWidget(title, self.center_workspace)
        dock.setObjectName(object_name or f"CenterDock_{uuid.uuid4().hex[:8]}")
        # Suppress the default dock title bar with a 0-height empty widget.
        # The native tab bar (top of center_workspace) already shows the panel
        # name and close button. When floating, the OS window decoration takes over.
        dock.setTitleBarWidget(QWidget())
        
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        dock.setWidget(widget)
        dock.setAttribute(Qt.WA_DeleteOnClose)
        dock.setAllowedAreas(Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea | Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        # Clean up tracked panels safely (accommodating for deleted C++ objects)
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
            # Append BEFORE _apply_current_percentages so it sees the new dock
            # and correctly hides the placeholder.
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

    def _on_dock_location_changed(self, *args):
        # When a panel is moved (e.g., dragged to create a split-screen), re-balance 
        # the center panels so they don't turn into tiny slivers. Re-applying 
        # percentages evenly distributes the center space among visible center panels.
        # We process this synchronously without a timer because native Qt dragging can block event loops.
        self._is_applying_preset = True
        self._apply_current_percentages()
        if hasattr(self, 'link_manager'):
            self.link_manager.refresh_connections()
        if hasattr(self, '_update_link_buttons'):
            self._update_link_buttons()

    def _ensure_center_has_panel(self):
        """
        Safety net called once after the event loop starts (singleShot 0).
        If center_panels is empty (nothing was restored and nothing was added),
        open a Reading View so the user never lands on the bare placeholder.
        """
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
            # Fully hide any tab whose title is empty (the placeholder dock)
            for i in range(tb.count()):
                if tb.tabText(i).strip() == '':
                    tb.setTabVisible(i, False)

        # 2. Center panels: toggle title bar based on tabified state.
        #    - Tabified → empty widget (native tab bar above handles title+close, no duplicate row)
        #    - Split/standalone → None (restore Qt's default draggable title bar)
        #    Only set when state changes to avoid 50ms thrashing.
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
                        p.setTitleBarWidget(None)  # restore default draggable title bar
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
        # Share expensive loaded dictionaries / indexes with secondary scenes
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
        
        # Make sure outline panels know if they are the active one for this new reading view
        # (Though active_outline is broadcast, reading views share the main_scene's state)
        for p in self.center_panels:
            try:
                p.parent()
                if isinstance(p.widget(), OutlinePanel):
                    is_active = (p.widget().root_node_id == self.main_scene.active_outline_id)
                    p.widget().update_active_state(is_active)
            except RuntimeError:
                pass
        
        # Connect the new scene to the global study panel
        # When a scene modifies data (adds a bookmark), it emits studyDataChanged.
        # study_panel.dataChanged is the global bus that tells all scenes to re-render.
        scene.studyDataChanged.connect(self.study_panel.dataChanged.emit)
        scene.studyDataChanged.connect(self.study_panel.refresh)
        scene.outlineCreated.connect(self.study_panel.set_active_outline)
        scene.noteOpenRequested.connect(self.add_note_panel)

    def add_note_panel(self, note_key, ref, object_name=None):
        # Provide a fallback if opening from empty
        if not note_key:
            note_key = f"standalone_{uuid.uuid4().hex[:8]}"
            ref = "General Note"
            
        note_data = self.main_scene.study_manager.data["notes"].get(note_key, "")
        existing_text = note_data.get("text", "") if isinstance(note_data, dict) else note_data
        existing_title = note_data.get("title", "") if isinstance(note_data, dict) else ""
        
        # Customize NoteEditor not to act like a modal dialog
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
        """Smart link navigation from inside a Note panel.

        - No reading view open → open one and jump there.
        - Reading view already split alongside note → just jump.
        - Reading view exists but is tabbed/hidden → raise it to front then jump.
        """
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
            # No reading view — open one then jump
            self.add_reading_view()
            self._broadcast_jump(book, chapter, verse)
            return

        # Check if note is the ONLY visible non-tabbed panel (fullscreen-ish)
        note_siblings = []
        try:
            note_siblings = self.center_workspace.tabifiedDockWidgets(note_dock)
        except RuntimeError:
            pass

        reading_dock = reading_docks[0]
        # Raise the reading view if it's tabbed or hidden
        try:
            reading_dock.show()
            reading_dock.raise_()
        except RuntimeError:
            pass

        self._broadcast_jump(book, chapter, verse)

    def _on_note_saved(self, note_key, editor):
        """Persist the note without closing the panel."""
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
        from PySide6.QtWidgets import QDialog
        if result == NoteEditor.DELETE_CODE:
            self.main_scene.study_manager.delete_note(note_key)
            self.main_scene._render_study_overlays()
            self.main_scene.studyDataChanged.emit()
            dock.close()

    def add_outline_panel(self, outline_id, object_name=None, is_restoring=False):
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
        
        # Init button state
        panel.update_active_state(outline_id == self.main_scene.active_outline_id)

    # --- Actions ---
    def _toggle_left_dock(self, checked):
        if checked:
            self.left_dock.show()
        else:
            self.left_dock.hide()

    def _toggle_right_dock(self, checked):
        if checked:
            self.right_dock.show()
        else:
            self.right_dock.hide()

    def setup_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        edit_menu = menubar.addMenu("&Edit")
        view_menu = menubar.addMenu("&View")
        symbols_menu = menubar.addMenu("&Symbols")
        
        layout_presets_menu = view_menu.addMenu("Layout Presets")
        
        default_layout_act = QAction("Default Layout", self)
        default_layout_act.triggered.connect(lambda: self._apply_layout_preset(0.10, 0.10, close_extras=True))
        layout_presets_menu.addAction(default_layout_act)
        
        reading_focus_act = QAction("Reading Focus", self)
        reading_focus_act.triggered.connect(lambda: self._apply_layout_preset(0.0, 0.0))
        layout_presets_menu.addAction(reading_focus_act)
        
        study_focus_act = QAction("Study Focus", self)
        study_focus_act.triggered.connect(self._apply_study_focus_preset)
        layout_presets_menu.addAction(study_focus_act)
        
        appearance_act = QAction("Appearance Settings", self)
        appearance_act.triggered.connect(self._show_appearance_settings)
        edit_menu.addAction(appearance_act)

        file_menu.addSeparator()
        
        # --- Export Menu ---
        export_menu = file_menu.addMenu("Export")
        
        export_notes_act = QAction("Export Notes...", self)
        export_notes_act.triggered.connect(lambda: self.export_manager.trigger_export_dialog("Notes"))
        export_menu.addAction(export_notes_act)
        
        export_outline_act = QAction("Export Outline...", self)
        export_outline_act.triggered.connect(lambda: self.export_manager.trigger_export_dialog("Outlines"))
        export_menu.addAction(export_outline_act)

        file_menu.addSeparator()
        exit_act = QAction("Exit", self)
        exit_act.triggered.connect(self.close)
        file_menu.addAction(exit_act)

        manage_symbols_act = QAction("Manage Symbols...", self)
        manage_symbols_act.triggered.connect(self._open_symbols_dialog)
        symbols_menu.addAction(manage_symbols_act)

    def _apply_layout_preset(self, left_pct, right_pct, close_extras=False):
        self._left_dock_pct = left_pct
        self._right_dock_pct = right_pct
        self._is_applying_preset = True
        
        # Reset overall window layout completely to clear any dragged dock positions
        from PySide6.QtCore import QSettings
        QSettings("JehuReader", "MainWindow").remove("windowState")
        QSettings("JehuReader", "MainWindow").remove("center_workspace_state")
        
        # Move required docks back to their default side locations (in case user dragged them elsewhere)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.left_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.right_dock)
        self.center_workspace.addDockWidget(Qt.TopDockWidgetArea, self.placeholder_dock)
        
        self.placeholder_dock.hide()
        
        if close_extras:
            self._clean_center_panels()
            valid_centers = [p for p in self.center_panels if p.isVisible() and not p.isFloating()]
            
            # Find the first ReadingViewPanel to keep open
            first_reading_view = None
            for p in valid_centers:
                if isinstance(p.widget(), ReadingViewPanel):
                    first_reading_view = p
                    break
                    
            if first_reading_view:
                # Close all OTHER center panels
                for p in valid_centers:
                    if p != first_reading_view:
                        p.close()
            else:
                # No reading view found, close everything and make a new one
                for p in valid_centers:
                    p.close()
                self.add_reading_view()
        else:
            # Even if we aren't closing extras, make sure center panels are back in the center
            self._clean_center_panels()
            valid_centers = [p for p in self.center_panels if p.isVisible() and not p.isFloating()]
            if valid_centers:
                # Re-tabify all center panels together if they were dragged around into weird splits
                first_panel = valid_centers[0]
                self.center_workspace.addDockWidget(Qt.TopDockWidgetArea, first_panel)
                for p in valid_centers[1:]:
                    self.center_workspace.tabifyDockWidget(first_panel, p)
        
        if left_pct > 0:
            self.left_dock.show()
        else:
            self.left_dock.hide()
            
        if right_pct > 0:
            self.right_dock.show()
        else:
            self.right_dock.hide()
            
        self._apply_current_percentages()
        
    def _apply_study_focus_preset(self):
        self._clean_center_panels()
        valid_centers = [p for p in self.center_panels if p.isVisible() and not p.isFloating()]
        if len(valid_centers) < 2:
            self.add_reading_view()
        self._apply_layout_preset(0.10, 0.10)

    def _open_symbols_dialog(self):
        dialog = SymbolDialog(self.main_scene.symbol_manager, self)
        dialog.symbolsChanged.connect(self.main_scene._render_study_overlays)
        dialog.exec()

    def _show_appearance_settings(self):
        self.appearance_dialog.show()
        self.appearance_dialog.raise_()
        self.appearance_dialog.activateWindow()

    def closeEvent(self, event):
        from PySide6.QtCore import QSettings
        import json
        settings = QSettings("JehuReader", "MainWindow")
        
        panels_state = []
        for p in self.center_panels:
            try:
                p.parent() # check if alive
                w = p.widget()
                state = {"objectName": p.objectName(), "title": p.windowTitle()}
                if isinstance(w, ReadingViewPanel):
                    state["type"] = "ReadingView"
                elif isinstance(w, NoteEditor):
                    state["type"] = "Note"
                    state["note_key"] = getattr(w, "note_key", "")
                    state["ref"] = getattr(w, "ref", "")
                elif isinstance(w, OutlinePanel):
                    state["type"] = "Outline"
                    state["outline_id"] = getattr(w, "outline_id", "")
                
                if "type" in state:
                    panels_state.append(state)
            except RuntimeError:
                pass
                
        settings.setValue("center_panels_state", json.dumps(panels_state))
        
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        settings.setValue("center_workspace_state", self.center_workspace.saveState())
        
        total_w = float(max(1, self.width()))
        if self.left_dock.isVisible() and not self.left_dock.isFloating():
            settings.setValue("left_dock_pct", self.left_dock.width() / total_w)
            
        if self.right_dock.isVisible() and not self.right_dock.isFloating():
            settings.setValue("right_dock_pct", self.right_dock.width() / total_w)
            
        self.main_scene.study_manager.save_data()
        super().closeEvent(event)
