from PySide6.QtWidgets import QMainWindow
from PySide6.QtCore import Qt, QSettings
import json

class MainWindowLayoutMixin:
    """Mixin for MainWindow to handle layout and presets."""
    
    def _load_and_restore_layout(self):
        from src.ui.components.reading_view_panel import ReadingViewPanel
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

        if not restored_any:
            self.add_reading_view()

        state = settings.value("windowState")
        if state:
            self.restoreState(state)

        if restored_any:
            center_state = settings.value("center_workspace_state")
            if center_state:
                self.center_workspace.restoreState(center_state)

        self._is_applying_preset = False
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self._ensure_center_has_panel)

    def _apply_current_percentages(self):
        total_w = self.width()
        left_w = max(1, int(total_w * self._left_dock_pct))
        right_w = max(1, int(total_w * self._right_dock_pct))
        
        self._clean_center_panels()
        real_centers = [p for p in self.center_panels if p.isVisible() and not p.isFloating()]
        
        used_w = 0
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

    def _apply_layout_preset(self, left_pct, right_pct, close_extras=False):
        from src.ui.components.reading_view_panel import ReadingViewPanel
        self._left_dock_pct = left_pct
        self._right_dock_pct = right_pct
        self._is_applying_preset = True
        
        QSettings("JehuReader", "MainWindow").remove("windowState")
        QSettings("JehuReader", "MainWindow").remove("center_workspace_state")
        
        self.addDockWidget(Qt.LeftDockWidgetArea, self.left_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.right_dock)
        self.center_workspace.addDockWidget(Qt.TopDockWidgetArea, self.placeholder_dock)
        
        self.placeholder_dock.hide()
        
        if close_extras:
            self._clean_center_panels()
            valid_centers = [p for p in self.center_panels if p.isVisible() and not p.isFloating()]
            
            first_reading_view = None
            for p in valid_centers:
                if isinstance(p.widget(), ReadingViewPanel):
                    first_reading_view = p
                    break
                    
            if first_reading_view:
                for p in valid_centers:
                    if p != first_reading_view:
                        p.close()
            else:
                for p in valid_centers:
                    p.close()
                self.add_reading_view()
        else:
            self._clean_center_panels()
            valid_centers = [p for p in self.center_panels if p.isVisible() and not p.isFloating()]
            if valid_centers:
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
