from PySide6.QtWidgets import QScrollBar, QStyle, QStyleOptionSlider, QLabel
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtCore import Qt
from src.core.constants import SEARCH_HIGHLIGHT_COLOR

class JumpScrollBar(QScrollBar):
    """
    A custom vertical scrollbar that allows clicking on the track to jump 
    directly to a position and renders search match markers and bible sections.
    """
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.match_y_positions = [] # Normalized 0.0 to 1.0
        self.sections = [] # List of {y_start, y_end, color, name} (normalized)
        self.is_hovered = False
        self.setMouseTracking(True)
        
        # Custom Tooltip that follows mouse smoothly
        self.floating_label = QLabel(None, Qt.ToolTip | Qt.WindowTransparentForInput)
        self.floating_label.setStyleSheet("""
            background-color: #333;
            color: white;
            border: 1px solid #555;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 13px;
        """)
        self.floating_label.hide()

    def set_matches(self, y_positions, total_height):
        if total_height > 0:
            self.match_y_positions = [y / total_height for y in y_positions]
        else:
            self.match_y_positions = []
        self.update()

    def set_sections(self, section_data, total_height):
        """Sets the normalized ranges for bible sections."""
        self.sections = []
        if total_height > 0:
            for s in section_data:
                self.sections.append({
                    "y_start": s["y_start"] / total_height,
                    "y_end": s["y_end"] / total_height,
                    "color": s["color"],
                    "name": s["name"]
                })
        self.update()

    def enterEvent(self, event):
        self.is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.is_hovered = False
        self.floating_label.hide()
        self.update()
        super().leaveEvent(event)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        groove_rect = self.style().subControlRect(QStyle.CC_ScrollBar, opt, QStyle.SC_ScrollBarGroove, self)
        if groove_rect.isEmpty():
            groove_rect = self.rect()
            
        if groove_rect.contains(event.pos()):
            rel_y = (event.pos().y() - groove_rect.y()) / max(1, groove_rect.height())
            for s in self.sections:
                if s["y_start"] <= rel_y <= s["y_end"]:
                    self.floating_label.setText(s["name"])
                    self.floating_label.adjustSize()
                    # Offset to the left of the scrollbar
                    self.floating_label.move(event.globalPos().x() - self.floating_label.width() - 20, 
                                           event.globalPos().y() - self.floating_label.height() // 2)
                    self.floating_label.show()
                    return
        self.floating_label.hide()

    def paintEvent(self, event):
        super().paintEvent(event)
        
        painter = QPainter(self)
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        groove_rect = self.style().subControlRect(QStyle.CC_ScrollBar, opt, QStyle.SC_ScrollBarGroove, self)
        if groove_rect.isEmpty():
            groove_rect = self.rect()
        
        # 1. Paint Sections (Only when hovering)
        if self.is_hovered:
            for s in self.sections:
                y_start = groove_rect.y() + (s["y_start"] * groove_rect.height())
                color = QColor(s["color"])
                color.setAlpha(255) 
                painter.setPen(QPen(color, 2))
                painter.drawLine(groove_rect.left(), int(y_start), groove_rect.right(), int(y_start))

        # 2. Paint Search Matches (Always visible)
        if self.match_y_positions:
            painter.setPen(SEARCH_HIGHLIGHT_COLOR)
            for rel_y in self.match_y_positions:
                y = groove_rect.y() + (rel_y * groove_rect.height())
                painter.drawLine(groove_rect.left(), int(y), groove_rect.right(), int(y))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            opt = QStyleOptionSlider()
            self.initStyleOption(opt)
            control = self.style().hitTestComplexControl(QStyle.CC_ScrollBar, opt, event.pos(), self)
            
            if control in [QStyle.SC_ScrollBarAddPage, QStyle.SC_ScrollBarSubPage, QStyle.SC_ScrollBarGroove]:
                groove_rect = self.style().subControlRect(QStyle.CC_ScrollBar, opt, QStyle.SC_ScrollBarGroove, self)
                slider_rect = self.style().subControlRect(QStyle.CC_ScrollBar, opt, QStyle.SC_ScrollBarSlider, self)
                
                if self.orientation() == Qt.Vertical:
                    click_pos = event.pos().y()
                    groove_start = groove_rect.y()
                    groove_len = groove_rect.height()
                    slider_len = slider_rect.height()
                    target_handle_pos = click_pos - groove_start - (slider_len / 2)
                    available_span = max(1, groove_len - slider_len)
                    val = self.style().sliderValueFromPosition(self.minimum(), self.maximum(), int(target_handle_pos), available_span, opt.upsideDown)
                    self.setValue(val)
        super().mousePressEvent(event)
