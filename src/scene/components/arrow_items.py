from PySide6.QtWidgets import QGraphicsPathItem, QGraphicsObject
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QBrush, QColor, QPen, QPainterPath, QPainter
import math

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
        self.body_path = QPainterPath(self.start_pos)
        self.body_path.lineTo(self.end_pos)
        
        # Arrow head calculation
        angle = math.atan2(self.end_pos.y() - self.start_pos.y(), 
                           self.end_pos.x() - self.start_pos.x())
        
        head_len = 10
        head_angle = math.pi / 6 # 30 degrees
        
        p1 = self.end_pos - QPointF(head_len * math.cos(angle - head_angle),
                                   head_len * math.sin(angle - head_angle))
        p2 = self.end_pos - QPointF(head_len * math.cos(angle + head_angle),
                                   head_len * math.sin(angle + head_angle))
        
        self.head_path = QPainterPath(self.end_pos)
        self.head_path.lineTo(p1)
        self.head_path.lineTo(p2)
        self.head_path.closeSubpath()
        
        full_path = QPainterPath(self.body_path)
        full_path.addPath(self.head_path)
        self.setPath(full_path)
        
        pen = QPen(self.color, 2)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        self.setPen(pen)
        self.setBrush(Qt.NoBrush)

    def paint(self, painter, option, widget=None):
        painter.setPen(self.pen())
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(self.body_path)
        
        painter.setBrush(QBrush(self.color))
        painter.drawPath(self.head_path)

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

        self.body_path = QPainterPath()
        start = self.points[0]
        self.body_path.moveTo(start)

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
                
                self.body_path.lineTo(start_p)
                self.body_path.quadTo(p2, end_p)
            else:
                self.body_path.lineTo(p2)

        # Final segment
        end = self.points[-1]
        self.body_path.lineTo(end)

        self.head_path = QPainterPath()
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
            
            self.head_path.moveTo(end)
            self.head_path.lineTo(p1)
            self.head_path.lineTo(p2)
            self.head_path.closeSubpath()

        full_path = QPainterPath(self.body_path)
        full_path.addPath(self.head_path)
        self.setPath(full_path)
        
        pen = QPen(self.color, 2)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        self.setPen(pen)
        self.setBrush(Qt.NoBrush)

    def paint(self, painter, option, widget=None):
        painter.setPen(self.pen())
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(self.body_path)
        
        painter.setBrush(QBrush(self.color))
        painter.drawPath(self.head_path)

class GhostArrowIconItem(QGraphicsObject):
    """
    A small icon placed at the top-right corner of a word that is part of a
    ghost arrow connection. Invisible arrows; interactions happen via hover.
    """
    SIZE = 9  # icon diameter in pixels

    def __init__(self, word_rect, own_key, partner_key, ghost_manager, parent=None):
        super().__init__(parent)
        self.word_rect = word_rect          # QRectF of the linked word
        self.own_key = own_key
        self.partner_key = partner_key
        self.ghost_manager = ghost_manager  # SceneOverlayManager
        self._hovered = False
        self.setZValue(25)
        self.setAcceptedMouseButtons(Qt.NoButton)
        # Position at top-right corner of the word
        self.setPos(word_rect.right() - self.SIZE / 2,
                    word_rect.top() - self.SIZE / 2)

    def boundingRect(self):
        return QRectF(0, 0, self.SIZE, self.SIZE)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        # Outer circle
        alpha = 230 if self._hovered else 160
        color = QColor(180, 220, 255, alpha)
        painter.setPen(QPen(QColor(100, 170, 255, alpha), 1.2))
        painter.setBrush(QBrush(color))
        r = self.SIZE
        painter.drawEllipse(0, 0, r, r)
        # Inner cross (⊗-like)
        painter.setPen(QPen(QColor(40, 80, 140, alpha), 1.0))
        mid = r / 2
        margin = 2.5
        painter.drawLine(QPointF(mid, margin), QPointF(mid, r - margin))
        painter.drawLine(QPointF(margin, mid), QPointF(r - margin, mid))

    def set_hovered(self, hovered: bool):
        if self._hovered != hovered:
            self._hovered = hovered
            self.update()
