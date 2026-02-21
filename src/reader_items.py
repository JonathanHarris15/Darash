from PySide6.QtWidgets import (
    QGraphicsTextItem, QGraphicsEllipseItem, QGraphicsLineItem,
    QStyle, QGraphicsItem, QGraphicsObject, QGraphicsPathItem
)
from PySide6.QtCore import Qt, QPointF, QLineF, Signal, QRectF
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
    """A graphics item that renders a straight arrow from start to end."""
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
        
        # Arrow head calculation
        angle = math.atan2(self.end_pos.y() - self.start_pos.y(), 
                           self.end_pos.x() - self.start_pos.x())
        
        head_len = 10
        head_angle = math.pi / 6 # 30 degrees
        
        p1 = self.end_pos - QPointF(head_len * math.cos(angle - head_angle),
                                   head_len * math.sin(angle - head_angle))
        p2 = self.end_pos - QPointF(head_len * math.cos(angle + head_angle),
                                   head_len * math.sin(angle + head_angle))
        
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
        self.setBrush(Qt.NoBrush)

class SnakeArrowItem(QGraphicsPathItem):
    """
    An arrow item that snakes through lines and gates.
    """
    def __init__(self, points, color, parent=None):
        super().__init__(parent)
        self.points = points # List of QPointF
        self.color = QColor(color)
        self.radius = 8.0 # Corner rounding radius
        self.setZValue(20)
        self.setAcceptedMouseButtons(Qt.NoButton)
        self.update_path()

    def update_path(self):
        if not self.points or len(self.points) < 2:
            return

        path = QPainterPath()
        start = self.points[0]
        path.moveTo(start)

        # Draw segments with rounded corners
        for i in range(1, len(self.points) - 1):
            p1 = self.points[i-1]
            p2 = self.points[i]
            p3 = self.points[i+1]

            # Vector p2 -> p1 and p2 -> p3
            v1 = p1 - p2
            v3 = p3 - p2
            
            d1 = math.sqrt(v1.x()**2 + v1.y()**2)
            d3 = math.sqrt(v3.x()**2 + v3.y()**2)
            
            curr_r = min(self.radius, d1 / 2, d3 / 2)
            
            if curr_r > 0.1:
                # Points where the curve starts and ends
                start_p = p2 + (v1 / d1) * curr_r
                end_p = p2 + (v3 / d3) * curr_r
                
                path.lineTo(start_p)
                path.quadTo(p2, end_p)
            else:
                path.lineTo(p2)

        # Final segment
        end = self.points[-1]
        path.lineTo(end)

        # Arrow head
        if len(self.points) >= 2:
            last_p = self.points[-2]
            angle = math.atan2(end.y() - last_p.y(), end.x() - last_p.x())
            
            head_len = 10
            head_angle = math.pi / 6 # 30 degrees
            
            p1 = end - QPointF(head_len * math.cos(angle - head_angle),
                               head_len * math.sin(angle - head_angle))
            p2 = end - QPointF(head_len * math.cos(angle + head_angle),
                               head_len * math.sin(angle + head_angle))
            
            arrow_head = QPainterPath(end)
            arrow_head.lineTo(p1)
            arrow_head.lineTo(p2)
            arrow_head.closeSubpath()
            path.addPath(arrow_head)

        self.setPath(path)
        pen = QPen(self.color, 2)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        self.setPen(pen)
        self.setBrush(Qt.NoBrush)

class VerseNumberItem(QGraphicsObject):
    """Clickable and draggable verse number item."""
    dragged = Signal(float) # dx
    clicked = Signal(bool) # shift pressed
    doubleClicked = Signal()
    contextMenuRequested = Signal(QPointF)
    released = Signal()

    def __init__(self, verse_num, ref, font, color, mark_font=None, parent=None):
        super().__init__(parent)
        self.verse_num = str(verse_num)
        self.ref = ref
        self.font = font
        self.color = color
        self.mark_font = mark_font if mark_font else font
        self.mark_type = None # heart, question, attention, star
        self.is_selected = False
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.PointingHandCursor)
        self._dragging = False
        self._drag_start_x = 0
        
        # Calculate dynamic height based on font
        from PySide6.QtGui import QFontMetrics
        metrics = QFontMetrics(self.font)
        self._height = metrics.height()
        
        # Also check mark font height for bounding rect
        m_metrics = QFontMetrics(self.mark_font)
        self._mark_height = m_metrics.height()
        
    def boundingRect(self):
        h = max(self._height, self._mark_height)
        # Left margin (-35) for icon+arrow, width (65) total, and height from font
        return QRectF(-35, 0, 65, h + 5)

    def paint(self, painter, option, widget=None):
        if self.is_selected:
            # Draw a small right-pointing arrow to indicate tabbing capability
            painter.setBrush(QBrush(self.color))
            painter.setPen(Qt.NoPen)
            
            # Position arrow closer to the number
            arrow_path = QPainterPath()
            arrow_path.moveTo(-8, 6)
            arrow_path.lineTo(-2, 10)
            arrow_path.lineTo(-8, 14)
            arrow_path.closeSubpath()
            painter.drawPath(arrow_path)
            
        painter.setFont(self.font)
        painter.setPen(self.color)
        painter.drawText(QRectF(0, 0, 30, self._height + 5), Qt.AlignLeft | Qt.AlignTop, self.verse_num)
        
        if self.mark_type:
            # Draw mark icon/symbol to the LEFT of the number
            mark_color = self.color
            symbol = ""
            if self.mark_type == "heart":
                symbol = "❤"; mark_color = QColor("#ff4b4b")
            elif self.mark_type == "question":
                symbol = "?"; mark_color = QColor("#4b9fff")
            elif self.mark_type == "attention":
                symbol = "!!"; mark_color = QColor("#ffcc00")
            elif self.mark_type == "star":
                symbol = "★"; mark_color = QColor("#ffcc00")
                
            if symbol:
                painter.setFont(self.mark_font)
                painter.setPen(mark_color)
                # Position mark further left of the verse number
                painter.drawText(QRectF(-28, 0, 30, self._mark_height + 5), Qt.AlignLeft | Qt.AlignTop, symbol)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(bool(event.modifiers() & Qt.ShiftModifier))
            self._dragging = True
            self._drag_start_x = event.scenePos().x()
            event.accept()
        else:
            super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        self.contextMenuRequested.emit(event.screenPos())
        event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.doubleClicked.emit()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging:
            dx = event.scenePos().x() - self._drag_start_x
            self.dragged.emit(dx)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._dragging:
            self._dragging = False
            self.released.emit()
            event.accept()
        else:
            super().mouseReleaseEvent(event)
