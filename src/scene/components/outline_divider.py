from PySide6.QtWidgets import QGraphicsObject
from PySide6.QtCore import Qt, QPointF, Signal, QRectF
from PySide6.QtGui import QBrush, QColor, QPen, QPainter
import math

class OutlineDividerItem(QGraphicsObject):
    """
    A draggable horizontal line representing a split in the outline.
    """
    dragStarted = Signal(object, QPointF)
    
    def __init__(self, parent_node, split_idx, y, x_start, x_end, pen, is_double=False, text_level=None, parent=None):
        super().__init__(parent)
        self.parent_node = parent_node
        self.split_idx = split_idx
        self.y = y
        self.x_start = x_start
        self.x_end = x_end
        self.pen = pen
        self.is_double = is_double
        self.text_level = text_level
        self.is_inline = False
        self.inline_x = 0
        self.inline_y_top = 0
        self.inline_y_bot = 0
        
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.SizeVerCursor)
        self.setZValue(15)

    def boundingRect(self):
        # Wider bounding rect for easier grabbing and fully containing the new inline stretch
        if self.is_inline:
            return QRectF(self.x_start, self.inline_y_top - 10, self.x_end - self.x_start, (self.inline_y_bot - self.inline_y_top) + 20)
        return QRectF(self.x_start, self.y - 10, self.x_end - self.x_start, 20)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        
        if self.is_inline:
            painter.setPen(self.pen)
            
            top_y = self.inline_y_top
            bot_y = self.inline_y_bot
            
            # Vertical step line
            painter.drawLine(QPointF(self.inline_x, top_y), QPointF(self.inline_x, bot_y))
            # Branch right to the end margin
            painter.drawLine(QPointF(self.inline_x, top_y), QPointF(self.x_end, top_y))
            # Branch left to the start margin
            painter.drawLine(QPointF(self.x_start, bot_y), QPointF(self.inline_x, bot_y))
            
        elif self.text_level is not None:
            # Render spaced numbers for deep levels
            from PySide6.QtGui import QFont
            font = QFont("Consolas", 10)
            painter.setFont(font)
            painter.setPen(self.pen)
            
            # Subtle background to make numbers more readable
            bg_rect = self.boundingRect()
            bg_rect.setHeight(14)
            bg_rect.moveCenter(QPointF(bg_rect.center().x(), self.y))
            
            painter.setBrush(QBrush(QColor(40, 40, 40, 150)))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(bg_rect, 2, 2)
            
            painter.setPen(self.pen)
            
            # Increase spacing as level goes deeper
            # level 5 -> 4 spaces, level 6 -> 8 spaces, etc.
            spacing = " " * (max(1, self.text_level - 4) * 4)
            txt = f"{self.text_level}{spacing}" * 100
            painter.drawText(self.boundingRect(), Qt.AlignLeft | Qt.AlignVCenter, txt)
        elif self.is_double:
            # Outer Boundary: Double line
            painter.setPen(self.pen)
            painter.drawLine(QPointF(self.x_start, self.y - 2), QPointF(self.x_end, self.y - 2))
            painter.drawLine(QPointF(self.x_start, self.y + 2), QPointF(self.x_end, self.y + 2))
        else:
            # Standard line styles (Solid, Dash, etc. based on pen)
            painter.setPen(self.pen)
            painter.drawLine(QPointF(self.x_start, self.y), QPointF(self.x_end, self.y))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragStarted.emit(self, event.scenePos())
            event.accept()
        else:
            super().mousePressEvent(event)
