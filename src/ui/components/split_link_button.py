from PySide6.QtWidgets import QToolButton, QWidget
from PySide6.QtCore import Qt, QPoint, QSize
from PySide6.QtGui import QIcon, QFont, QPaintEvent, QPainter, QColor

class SplitLinkButton(QToolButton):
    def __init__(self, left_dock, right_dock, link_manager, parent=None):
        super().__init__(parent)
        self.left_dock = left_dock
        self.right_dock = right_dock
        self.link_manager = link_manager
        
        self.setFixedSize(28, 28)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Toggle Scroll Linking")
        
        # We'll rely on text emoji for now
        font = self.font()
        font.setPointSize(14)
        self.setFont(font)
        
        self.setStyleSheet("""
            QToolButton {
                background-color: #333333;
                border: 1px solid #555555;
                border-radius: 14px;
                color: white;
            }
            QToolButton:hover {
                background-color: #444444;
                border: 1px solid #777777;
            }
            QToolButton:pressed {
                background-color: #222222;
            }
        """)
        
        self._update_icon()

    def mousePressEvent(self, e):
        """Force manual handling of clicks on press to guarantee reliability when overlapping splitters."""
        if e.button() == Qt.LeftButton:
            self._toggle_link()
            e.accept()
            return
        super().mousePressEvent(e)
        
    def _update_icon(self):
        is_linked = self.link_manager.is_linked(self.right_dock)
        if is_linked:
            self.setText("🔗")
            self.setStyleSheet(self.styleSheet().replace("#333333", "#2a4d69")) # slight blue tint when linked
        else:
            self.setText("⛓️‍💥") # broken chain
            self.setStyleSheet(self.styleSheet().replace("#2a4d69", "#333333"))

    def _toggle_link(self):
        try:
            self.right_dock.parent() # verify dock exists
        except RuntimeError:
            return
            
        is_linked = self.link_manager.is_linked(self.right_dock)
        self.link_manager.set_linked(self.right_dock, not is_linked)
        self._update_icon()

    def reposition(self):
        if not self.parent(): return
        
        try:
            self.left_dock.parent()
            self.right_dock.parent()
        except RuntimeError:
            self.hide()
            return
            
        if not self.left_dock.isVisible() or not self.right_dock.isVisible():
            self.hide()
            return
            
        if self.left_dock.isFloating() or self.right_dock.isFloating():
            self.hide()
            return
        
        # Calculate midpoint
        parent_widget = self.parentWidget()
        
        # Global rects
        left_rect = self.left_dock.geometry()
        right_rect = self.right_dock.geometry()
        
        # map rects to parent (center_workspace typically)
        left_parent_rect = parent_widget.mapFromGlobal(self.left_dock.parentWidget().mapToGlobal(left_rect.topLeft()))
        right_parent_rect = parent_widget.mapFromGlobal(self.right_dock.parentWidget().mapToGlobal(right_rect.topLeft()))
        
        # Calculate X divider between left and right docks
        # Left dock's right edge
        x_divider = left_parent_rect.x() + left_rect.width()
        
        # Adjust Y to be perfectly vertically centered on the left dock
        y_pos = left_parent_rect.y() + (left_rect.height() // 2)
        
        self.move(x_divider - (self.width() // 2), y_pos - (self.height() // 2))
        self.show()
