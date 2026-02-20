from PySide6.QtWidgets import (
    QGraphicsTextItem, QGraphicsEllipseItem, QGraphicsLineItem,
    QStyle, QGraphicsItem, QGraphicsObject, QGraphicsPathItem
)
from PySide6.QtCore import Qt, QPointF, QLineF, Signal
from PySide6.QtGui import QBrush, QColor, QPen, QPainterPath
import math

class NoFocusTextItem(QGraphicsTextItem):
    """Custom QGraphicsTextItem that doesn't draw a dashed focus rectangle."""
    def paint(self, painter, option, widget=None):
        if option.state & QStyle.State_HasFocus:
            option.state &= ~QStyle.State_HasFocus
        super().paint(painter, option, widget)

class NoteIcon(QGraphicsEllipseItem):
    """Clickable icon representing a note."""
    def __init__(self, note_key, ref, scene_manager, parent=None):
        super().__init__(0, 0, 10, 10, parent)
        self.note_key = note_key
        self.ref = ref
        self.scene_manager = scene_manager
        self.setBrush(QBrush(QColor("cyan")))
        self.setPen(QPen(Qt.black, 1))
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setZValue(10)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # We assume the scene_manager has an open_note_by_key method
            self.scene_manager.open_note_by_key(self.note_key, self.ref)
            event.accept()
        else:
            super().mousePressEvent(event)

class ArrowItem(QGraphicsPathItem):
    """A single graphics item that renders an arrow from start to end."""
    def __init__(self, start_pos, end_pos, color, parent=None):
        super().__init__(parent)
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.color = QColor(color)
        self.setZValue(20)
        self.setAcceptedMouseButtons(Qt.NoButton)
        self.update_path()

    def update_path(self):
        path = QPainterPath(self.start_pos)
        path.lineTo(self.end_pos)
        
        # Arrow head
        # Use atan2(y2-y1, x2-x1) for direct vector angle in scene coordinates
        angle = math.atan2(self.end_pos.y() - self.start_pos.y(), 
                           self.end_pos.x() - self.start_pos.x())
        
        head_len = 10
        head_angle = math.pi / 6 # 30 degrees
        
        # Calculate offsets from the end point back towards the start
        p1 = self.end_pos - QPointF(head_len * math.cos(angle - head_angle),
                                   head_len * math.sin(angle - head_angle))
        p2 = self.end_pos - QPointF(head_len * math.cos(angle + head_angle),
                                   head_len * math.sin(angle + head_angle))
        
        # Refined arrowhead logic (standard for expert vector drawing)
        arrow_head = QPainterPath(self.end_pos)
        arrow_head.lineTo(p1)
        arrow_head.lineTo(p2)
        arrow_head.closeSubpath()
        path.addPath(arrow_head)
        
        self.setPath(path)
        pen = QPen(self.color, 2)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        self.setPen(pen)
        # Fill the arrowhead
        head_fill = QColor(self.color)
        head_fill.setAlpha(200)
        self.setBrush(QBrush(head_fill))
