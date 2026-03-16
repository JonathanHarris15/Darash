import os
import uuid
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QDockWidget, QToolBar, QSizePolicy
)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt, QTimer, QSettings, QEvent

from src.ui.components.navigation import NavigationDock
from src.ui.components.symbol_dialog import SymbolDialog
from src.ui.components.study_panel import StudyPanel
from src.ui.components.appearance_panel import AppearancePanel
from src.ui.components.activity_bar import ActivityBar
from src.ui.components.placeholder_panel import PlaceholderPanel
from src.ui.components.pseudo_tab_title_bar import PseudoTabTitleBar

from src.ui.main_window_layout import MainWindowLayoutMixin
from src.ui.main_window_panels import MainWindowPanelsMixin

class MainWindow(QMainWindow, MainWindowLayoutMixin, MainWindowPanelsMixin):
    def __init__(self):
        super().__init__()
        self._is_applying_preset = True

        from src.scene.reader_scene import ReaderScene
        self.main_scene = ReaderScene()
        
        self.setWindowTitle("Jehu Reader")

        # Main Layout Structure
        self.center_workspace = QMainWindow()
        self.center_workspace.setObjectName("CenterWorkspace")
        self.setCentralWidget(self.center_workspace)
        
        self.setDocumentMode(True)
        self.center_workspace.setDocumentMode(True)
        
        # Activity Bar
        self.toolbar = QToolBar("Activity Bar")
        self.toolbar.setObjectName("ActivityBar")
        self.toolbar.setMovable(False)
        self.activity_bar = ActivityBar()
        self.toolbar.addWidget(self.activity_bar)
        self.addToolBar(Qt.LeftToolBarArea, self.toolbar)
        
        self.center_panels = []
        
        from src.ui.main_window_dock_manager import MainWindowDockManager
        self.dock_manager = MainWindowDockManager(self)
        
        from src.ui.components.reading_view_link_manager import ReadingViewLinkManager
        self.link_manager = ReadingViewLinkManager(self)
        self.split_link_buttons = []
        
        self.setup_docks()
        self._load_and_restore_layout()
        self.setup_connections()
        
        self.appearance_dialog = AppearancePanel(self.main_scene, self)
        self.appearance_dialog.settingsChanged.connect(self._broadcast_appearance_settings)
        
        from src.ui.export_manager import ExportManager
        self.export_manager = ExportManager(self)
        
        self.setup_menu()
        
        # Release Note Manager
        from src.managers.release_note_manager import ReleaseNoteManager
        self.release_note_manager = ReleaseNoteManager()
        if self.release_note_manager.should_show_release_note():
            QTimer.singleShot(1000, self._show_release_notes)
        
        self.left_dock.installEventFilter(self)
        self.right_dock.installEventFilter(self)
        self._is_applying_preset = False
        
        QTimer.singleShot(100, self._apply_current_percentages)
        
        self._tab_update_timer = QTimer(self)
        self._tab_update_timer.timeout.connect(self._update_dock_tabs)
        self._tab_update_timer.start(50)
        
        self._link_button_timer = QTimer(self)
        self._link_button_timer.timeout.connect(self._update_link_buttons)
        self._link_button_timer.start(200)

    def _update_link_buttons(self):
        try:
            for btn in self.split_link_buttons:
                try:
                    btn.setParent(None)
                    btn.deleteLater()
                except RuntimeError: pass
            self.split_link_buttons.clear()
            
            active_panels = []
            for p in self.center_panels:
                try:
                    if not p.isVisible() or p.isFloating(): continue
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
        except RuntimeError: pass

    def setup_docks(self):
        from PySide6.QtWidgets import QTabWidget
        self.center_workspace.setDockNestingEnabled(True)
        self.center_workspace.setDockOptions(
            QMainWindow.AnimatedDocks | QMainWindow.AllowNestedDocks | QMainWindow.AllowTabbedDocks | QMainWindow.GroupedDragging
        )
        self.center_workspace.setTabPosition(Qt.AllDockWidgetAreas, QTabWidget.North)
        
        self.setCorner(Qt.TopLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.BottomLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.TopRightCorner, Qt.RightDockWidgetArea)
        self.setCorner(Qt.BottomRightCorner, Qt.RightDockWidgetArea)
        
        self.left_dock = QDockWidget("Bible Directory", self)
        self.left_dock.setObjectName("LeftDock")
        self.left_dock.setTitleBarWidget(PseudoTabTitleBar("Bible Directory", self.left_dock, self))
        self.left_dock.setAllowedAreas(Qt.LeftDockWidgetArea)
        self.left_dock.setFeatures(QDockWidget.DockWidgetClosable)
        self.nav_dock = NavigationDock(self.main_scene.loader)
        self.left_dock.setWidget(self.nav_dock)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.left_dock)
        
        self.right_dock = QDockWidget("Study Overview", self)
        self.right_dock.setObjectName("RightDock")
        self.right_dock.setTitleBarWidget(PseudoTabTitleBar("Study Overview", self.right_dock, self))
        self.right_dock.setAllowedAreas(Qt.RightDockWidgetArea)
        self.right_dock.setFeatures(QDockWidget.DockWidgetClosable)
        self.study_panel = StudyPanel(self.main_scene.study_manager, self.main_scene.symbol_manager)
        self.right_dock.setWidget(self.study_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, self.right_dock)
        
        self.placeholder_dock = QDockWidget("", self.center_workspace)
        self.placeholder_dock.setObjectName("PlaceholderDock")
        self.placeholder_dock.setTitleBarWidget(QWidget())
        self.placeholder_dock.setWidget(PlaceholderPanel(self))
        self.placeholder_dock.setAllowedAreas(Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea | Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.placeholder_dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.center_workspace.addDockWidget(Qt.TopDockWidgetArea, self.placeholder_dock)
        
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
            self._is_applying_preset = True
            QTimer.singleShot(10, self._apply_current_percentages)

    def setup_connections(self):
        self.activity_bar.toggleBibleDir.connect(self._toggle_left_dock)
        self.activity_bar.toggleStudyOverview.connect(self._toggle_right_dock)
        self.activity_bar.openReadingView.connect(self.add_reading_view)
        self.activity_bar.openNotesPanel.connect(lambda: self.add_note_panel("", ""))
        self.activity_bar.openOutlinePanel.connect(lambda: self.add_outline_panel(None))

        self.nav_dock.jumpRequested.connect(self._broadcast_jump)
        self.nav_dock.strongsToggled.connect(self._broadcast_strongs_enabled)
        self.nav_dock.outlinesToggled.connect(self._broadcast_outlines_enabled)
        
        self.study_panel.jumpRequested.connect(self._broadcast_jump)
        self.study_panel.noteOpenRequested.connect(self.add_note_panel)
        self.study_panel.outlineOpenRequested.connect(self.add_outline_panel)
        self.study_panel.outlineDeleted.connect(self._close_outline_panel)
        self.study_panel.activeOutlineChanged.connect(self._broadcast_active_outline)
        self.study_panel.dataChanged.connect(self._render_all_study_data)
        
        self.main_scene.studyDataChanged.connect(self.study_panel.refresh)
        self.main_scene.studyDataChanged.connect(self._render_all_study_data)
        self.main_scene.outlineCreated.connect(self.study_panel.set_active_outline)
        self.main_scene.outlineCreated.connect(self.add_outline_panel)
        self.main_scene.noteOpenRequested.connect(self.add_note_panel)

    def _broadcast_appearance_settings(self):
        from src.ui.components.reading_view_panel import ReadingViewPanel
        src = self.main_scene
        for p in self.center_panels:
            try:
                widget = p.widget()
                if not isinstance(widget, ReadingViewPanel): continue
                scene = widget.reader_widget.scene
                if scene is src: continue
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
            except RuntimeError: pass

    def _render_all_study_data(self):
        from src.ui.components.reading_view_panel import ReadingViewPanel
        from src.ui.components.outline_panel import OutlinePanel
        self.main_scene._render_study_overlays()
        self.main_scene._render_outline_overlays()
        self.main_scene.render_verses()
        for p in self.center_panels:
            try:
                widget = p.widget()
                if isinstance(widget, ReadingViewPanel):
                    scene = widget.reader_widget.scene
                    scene._render_study_overlays(); scene._render_outline_overlays(); scene.render_verses()
                elif isinstance(widget, OutlinePanel):
                    widget.refresh()
            except RuntimeError: pass

    def _broadcast_jump(self, book, chapter, verse):
        from src.ui.components.reading_view_panel import ReadingViewPanel
        jumped = False
        for p in self.center_panels:
            try:
                if p.isVisible() and isinstance(p.widget(), ReadingViewPanel):
                    p.widget().reader_widget.scene.jump_to(book, chapter, verse)
                    jumped = True; break
            except RuntimeError: pass
        if not jumped:
            self.add_reading_view()
            self._broadcast_jump(book, chapter, verse)

    def _broadcast_active_outline(self, outline_id):
        from src.ui.components.reading_view_panel import ReadingViewPanel
        from src.ui.components.outline_panel import OutlinePanel
        self.main_scene.set_active_outline(outline_id)
        self.study_panel.set_active_outline(outline_id, emit_signal=False)
        for p in self.center_panels:
            try:
                if isinstance(p.widget(), ReadingViewPanel):
                    p.widget().reader_widget.scene.set_active_outline(outline_id)
                elif isinstance(p.widget(), OutlinePanel):
                    p.widget().update_active_state(p.widget().root_node_id == outline_id)
            except RuntimeError: pass

    def _broadcast_strongs_enabled(self, enabled):
        from src.ui.components.reading_view_panel import ReadingViewPanel
        self.main_scene.set_strongs_enabled(enabled)
        for p in self.center_panels:
            try:
                if isinstance(p.widget(), ReadingViewPanel):
                    p.widget().reader_widget.scene.set_strongs_enabled(enabled)
            except RuntimeError: pass

    def _broadcast_outlines_enabled(self, enabled):
        from src.ui.components.reading_view_panel import ReadingViewPanel
        self.main_scene.set_outlines_enabled(enabled)
        for p in self.center_panels:
            try:
                if isinstance(p.widget(), ReadingViewPanel):
                    p.widget().reader_widget.scene.set_outlines_enabled(enabled)
            except RuntimeError: pass

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
        appearance_act.triggered.connect(lambda: self.appearance_dialog.show() or self.appearance_dialog.raise_() or self.appearance_dialog.activateWindow())
        edit_menu.addAction(appearance_act)

        file_menu.addSeparator()
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
        manage_symbols_act.triggered.connect(lambda: SymbolDialog(self.main_scene.symbol_manager, self).exec())
        symbols_menu.addAction(manage_symbols_act)

        help_menu = menubar.addMenu("&Help")
        release_notes_act = QAction("Release Notes...", self)
        release_notes_act.triggered.connect(self._show_release_notes)
        help_menu.addAction(release_notes_act)
        
        help_menu.addSeparator()
        update_act = QAction("Check for Updates...", self)
        update_act.triggered.connect(self._check_for_updates_manual)
        help_menu.addAction(update_act)

    def _check_for_updates_manual(self):
        from src.utils.update_manager import UpdateManager
        from PySide6.QtWidgets import QMessageBox
        
        info = UpdateManager.get_latest_release_info()
        if not info:
            QMessageBox.critical(self, "Update Check Failed", "Could not connect to GitHub to check for updates.")
            return
            
        latest_tag = info.get('tag_name', 'v?').lstrip('v')
        from src.core.constants import APP_VERSION
        
        def to_tuple(v):
            try: return tuple(map(int, (v.split('.'))))
            except: return (0,0,0)

        if to_tuple(latest_tag) > to_tuple(APP_VERSION):
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Update Available")
            msg.setText(f"A new version (v{latest_tag}) is available.")
            msg.setInformativeText(f"Current version: v{APP_VERSION}\n\nWould you like to download and install it now?")
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            if msg.exec() == QMessageBox.Yes:
                if UpdateManager.start_update(info):
                    self.close()
        else:
            QMessageBox.information(self, "Up to Date", f"You are running the latest version (v{APP_VERSION}).")
        from src.ui.components.release_note_dialog import ReleaseNoteDialog
        content = self.release_note_manager.get_current_release_note()
        version = self.release_note_manager.version
        dialog = ReleaseNoteDialog(self, content=content, version=version)
        if dialog.exec():
            # If they closed it, count it as a "seen" event
            self.release_note_manager.increment_view_count()

    def closeEvent(self, event):
        if hasattr(self, '_tab_update_timer'): self._tab_update_timer.stop()
        if hasattr(self, '_link_button_timer'): self._link_button_timer.stop()
        
        import json
        settings = QSettings("JehuReader", "MainWindow")
        from src.ui.components.reading_view_panel import ReadingViewPanel
        from src.ui.components.note_editor import NoteEditor
        from src.ui.components.outline_panel import OutlinePanel
        
        panels_state = []
        for p in self.center_panels:
            try:
                w = p.widget()
                state = {"objectName": p.objectName(), "title": p.windowTitle()}
                if isinstance(w, ReadingViewPanel): state["type"] = "ReadingView"
                elif isinstance(w, NoteEditor):
                    state.update({"type": "Note", "note_key": getattr(w, "note_key", ""), "ref": getattr(w, "ref", "")})
                elif isinstance(w, OutlinePanel):
                    state.update({"type": "Outline", "outline_id": getattr(w, "outline_id", "")})
                if "type" in state: panels_state.append(state)
            except RuntimeError: pass
                
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
