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

class PseudoTabTitleBar(QWidget):
    def __init__(self, title, dock, main_window):
        super().__init__()
        self.dock = dock
        self.main_window = main_window
        self.is_pseudo_tab = True
        
        self.setFixedHeight(30)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.tab = QWidget()
        self.tab.setObjectName("PseudoTab")
        self.tab.setStyleSheet("""
            QWidget#PseudoTab {
                background-color: palette(window);
                border: 1px solid palette(dark);
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-top: 5px;
            }
        """)
        tab_layout = QHBoxLayout(self.tab)
        tab_layout.setContentsMargins(10, 2, 8, 2)
        tab_layout.setSpacing(8)
        
        self.label = QLabel(title)
        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(16, 16)
        self.close_btn.setStyleSheet("""
            QPushButton { 
                border: none; 
                font-weight: bold; 
                background: transparent; 
                border-radius: 8px;
            }
            QPushButton:hover { 
                background-color: #c42b1c; 
                color: white; 
            }
        """)
        self.close_btn.clicked.connect(dock.close)
        
        tab_layout.addWidget(self.label)
        tab_layout.addWidget(self.close_btn)
        
        layout.addWidget(self.tab)
        layout.addStretch()

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
        
        study_name = self.main_scene.study_manager.current_study_name
        self.setWindowTitle(f"Jehu Reader - {study_name}")

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

        # Setup Docks
        self.setup_docks()
        
        # Load and restore layout MUST happen after docks are created but before connections
        self._load_and_restore_layout()
        
        # Setup Connections
        self.setup_connections()
        
        # Appearance Dialog (Standalone window)
        self.appearance_dialog = AppearancePanel(self.main_scene, self)
        
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
        self._tab_update_timer.start(250)

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
                    p_title = state.get("title", "Panel")
                    
                    if p_type == "ReadingView":
                        self.add_reading_view(object_name=p_name)
                        restored_any = True
                    elif p_type == "Note":
                        self.add_note_panel(state.get("note_key"), state.get("ref"), object_name=p_name)
                        restored_any = True
                    elif p_type == "Outline":
                        self.add_outline_panel(state.get("outline_id"), object_name=p_name)
                        restored_any = True
            except Exception as e:
                print("Failed to restore panels:", e)
                
        if not restored_any:
            self.add_reading_view()
            
        state = settings.value("windowState")
        if state:
            self.restoreState(state)
            
        center_state = settings.value("center_workspace_state")
        if center_state:
            self.center_workspace.restoreState(center_state)
            
        self._is_applying_preset = False

    def setup_docks(self):
        from PySide6.QtWidgets import QTabWidget
        # Sandbox for the center workspace
        self.center_workspace.setDockNestingEnabled(True)
        self.center_workspace.setDockOptions(QMainWindow.AnimatedDocks | QMainWindow.AllowNestedDocks | QMainWindow.AllowTabbedDocks | QMainWindow.GroupedDragging | QMainWindow.ForceTabbedDocks)
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
        self.placeholder_dock = QDockWidget("Placeholder", self.center_workspace)
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
        self.nav_dock.jumpRequested.connect(self.main_scene.jump_to)
        self.nav_dock.strongsToggled.connect(self.main_scene.set_strongs_enabled)
        self.nav_dock.outlinesToggled.connect(self.main_scene.set_outlines_enabled)
        
        self.study_panel.jumpRequested.connect(self.main_scene.jump_to)
        self.study_panel.noteOpenRequested.connect(self.add_note_panel)
        self.study_panel.activeOutlineChanged.connect(self.main_scene.set_active_outline)
        
        # Render updates
        self.study_panel.dataChanged.connect(self.main_scene._render_study_overlays)
        self.study_panel.dataChanged.connect(self.main_scene._render_outline_overlays)
        self.study_panel.dataChanged.connect(self.main_scene.render_verses)
        
        self.main_scene.studyDataChanged.connect(self.study_panel.refresh)
        self.main_scene.outlineCreated.connect(self.study_panel.set_active_outline)

    # --- Panel Management ---
    def _add_center_dock(self, title, widget, object_name=None, force_split=False):
        dock = QDockWidget(title, self.center_workspace)
        dock.setObjectName(object_name or f"CenterDock_{uuid.uuid4().hex[:8]}")
        dock.setTitleBarWidget(PseudoTabTitleBar(title, dock, self))
        
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        dock.setWidget(widget)
        dock.setAttribute(Qt.WA_DeleteOnClose)
        dock.setAllowedAreas(Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea | Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        # Clean up tracked panels safely (accommodating for deleted C++ objects)
        self._clean_center_panels()
        
        if self.center_panels:
            if force_split:
                self.center_workspace.splitDockWidget(self.center_panels[-1], dock, Qt.Horizontal)
            else:
                self.center_workspace.tabifyDockWidget(self.center_panels[-1], dock)
        else:
            if self.placeholder_dock.isVisible() and not self.placeholder_dock.isFloating():
                self.center_workspace.tabifyDockWidget(self.placeholder_dock, dock)
            else:
                self.center_workspace.addDockWidget(Qt.TopDockWidgetArea, dock)
            self._is_applying_preset = True
            self._apply_current_percentages()
            
        self.center_panels.append(dock)
        
        # When a dock is dragged to create a split screen, re-balance the center panels
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

    def _update_dock_tabs(self):
        from PySide6.QtWidgets import QTabBar
        # 1. Update native QTabBar close buttons
        for tb in self.findChildren(QTabBar):
            if not getattr(tb, '_jehu_closable_setup', False):
                tb.setTabsClosable(True)
                tb.tabCloseRequested.connect(self._on_native_tab_close)
                tb._jehu_closable_setup = True
                
        # 2. Update pseudo-tabs visibility
        all_docks = self.center_panels + [self.left_dock, self.right_dock]
        for p in all_docks:
            try:
                # If deleted C++ object, skip
                p.parent()
                if p.isVisible() and not p.isFloating():
                    # Hide pseudo-tab if natively tabified
                    is_tabified = len(self.tabifiedDockWidgets(p)) > 0
                    tb = p.titleBarWidget()
                    if tb and hasattr(tb, 'is_pseudo_tab'):
                        tb.setVisible(not is_tabified)
                elif p.isFloating():
                    # Floating docks always show native title bar, but Qt forces our titleBarWidget if set
                    tb = p.titleBarWidget()
                    if tb and hasattr(tb, 'is_pseudo_tab'):
                        tb.setVisible(True)
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

    def add_reading_view(self, force_split=False, object_name=None):
        panel = ReadingViewPanel(self.main_scene, self.main_scene.study_manager)
        self._add_center_dock("Reading View", panel, object_name=object_name, force_split=force_split)

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
        
        editor.jumpRequested.connect(self.main_scene.jump_to)
        editor.finished.connect(lambda result: self._on_note_editor_finished(result, editor, note_key, dock))

    def _on_note_editor_finished(self, result, editor, note_key, dock):
        from PySide6.QtWidgets import QDialog
        if result == QDialog.Accepted:
            if note_key.startswith("standalone_"):
                self.main_scene.study_manager.data["notes"].setdefault(note_key, {})
                self.main_scene.study_manager.data["notes"][note_key]["title"] = editor.get_title()
                self.main_scene.study_manager.data["notes"][note_key]["text"] = editor.get_text()
                self.main_scene.study_manager.save_study()
            else:
                ref_parts = note_key.split('|')
                if len(ref_parts) >= 4:
                    self.main_scene.study_manager.add_note(ref_parts[0], ref_parts[1], ref_parts[2], int(ref_parts[3]), 
                                               editor.get_text(), editor.get_title())
            self.main_scene._render_study_overlays()
            self.main_scene.studyDataChanged.emit()
        elif result == NoteEditor.DELETE_CODE:
            self.main_scene.study_manager.delete_note(note_key)
            self.main_scene._render_study_overlays()
            self.main_scene.studyDataChanged.emit()
            
        dock.close()

    def add_outline_panel(self, outline_id, object_name=None):
        if not outline_id:
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
        panel.jumpRequested.connect(self.main_scene.jump_to)
        panel.outlineChanged.connect(self.main_scene.studyDataChanged.emit)
        
        title = "Outline Editor"
        if outline_id:
            node = self.main_scene.study_manager.outline_manager.get_node(outline_id)
            if node:
                title = f"Outline - {node.get('title', 'Unknown')}"
                
        self._add_center_dock(title, panel, object_name=object_name)

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
        new_study_act = QAction("New Study", self)
        new_study_act.triggered.connect(self._on_new_study)
        file_menu.addAction(new_study_act)
        
        open_study_act = QAction("Open Study", self)
        open_study_act.triggered.connect(self._on_open_study)
        file_menu.addAction(open_study_act)
        
        file_menu.addSeparator()
        exit_act = QAction("Exit", self)
        exit_act.triggered.connect(self.close)
        file_menu.addAction(exit_act)

        manage_symbols_act = QAction("Manage Symbols...", self)
        manage_symbols_act.triggered.connect(self._open_symbols_dialog)
        symbols_menu.addAction(manage_symbols_act)

    def _on_new_study(self):
        name, ok = QInputDialog.getText(self, "New Study", "Enter study name:")
        if ok and name:
            self.main_scene.study_manager.load_study(name)
            self.main_scene.load_settings()
            self.main_scene.recalculate_layout(self.main_scene.last_width)
            self.main_scene._render_study_overlays()
            self.setWindowTitle(f"Jehu Reader - {name}")
            self.study_panel.refresh()

    def _on_open_study(self):
        base_dir = self.main_scene.study_manager.base_dir
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
            
        study_dir = QFileDialog.getExistingDirectory(self, "Open Study", base_dir)
        if study_dir:
            name = os.path.basename(study_dir)
            self.main_scene.study_manager.load_study(name)
            self.main_scene.load_settings()
            self.main_scene.recalculate_layout(self.main_scene.last_width)
            self.main_scene._render_study_overlays()
            self.setWindowTitle(f"Jehu Reader - {name}")
            self.study_panel.refresh()

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
            self.add_reading_view(force_split=True)
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
            
        self.main_scene.study_manager.save_study()
        super().closeEvent(event)
