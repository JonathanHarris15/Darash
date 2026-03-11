from PySide6.QtWidgets import QGraphicsObject
from PySide6.QtCore import Qt, QPointF, Signal, QRectF
from PySide6.QtGui import QBrush, QColor, QPen, QPainterPath, QPainter, QFontMetrics
from src.core.constants import VERSE_NUMBER_RESERVED_WIDTH

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
        self.s_ref = None # Set by SentenceHandleItem
        self.font = font
        self.color = color
        self.mark_font = mark_font if mark_font else font
        self.mark_type = None # heart, question, attention, star
        self.is_selected = False
        self.is_search_result = False
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.PointingHandCursor)
        self._dragging = False
        self._drag_start_x = 0
        
        # Calculate dynamic height based on font
        metrics = QFontMetrics(self.font)
        self._height = metrics.height()
        
        # Also check mark font height for bounding rect
        m_metrics = QFontMetrics(self.mark_font)
        self._mark_height = m_metrics.height()
        
    def boundingRect(self):
        h = max(self._height, self._mark_height)
        # Left margin (-35) for icon+arrow, width (35 + reserved_width) total, and height from font
        return QRectF(-35, 0, 35 + VERSE_NUMBER_RESERVED_WIDTH, h + 5)

    def paint(self, painter, option, widget=None):
        if getattr(self, 'is_search_result', False):
            from src.core.constants import SEARCH_HIGHLIGHT_COLOR
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(SEARCH_HIGHLIGHT_COLOR))
            # Just behind the verse number
            painter.drawRect(QRectF(-2, 2, VERSE_NUMBER_RESERVED_WIDTH + 4, self._height + 2))
            
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
        painter.drawText(QRectF(0, 0, VERSE_NUMBER_RESERVED_WIDTH, self._height + 5), Qt.AlignLeft | Qt.AlignTop, self.verse_num)
        
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
                painter.drawText(QRectF(-28, 0, VERSE_NUMBER_RESERVED_WIDTH, self._mark_height + 5), Qt.AlignLeft | Qt.AlignTop, symbol)

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

class SentenceHandleItem(VerseNumberItem):
    """Draggable handle for sub-sentences when sentence breaking is enabled."""
    def __init__(self, ref, s_ref, font, color, parent=None):
        super().__init__("", ref, font, color, parent=parent)
        self.s_ref = s_ref # e.g. Book 1:1|2
        
    def paint(self, painter, option, widget=None):
        if self.is_selected:
            # Draw a small right-pointing arrow to indicate tabbing capability
            painter.setBrush(QBrush(self.color))
            painter.setPen(Qt.NoPen)
            
            # Position arrow same as VerseNumberItem
            arrow_path = QPainterPath()
            arrow_path.moveTo(-8, 6)
            arrow_path.lineTo(-2, 10)
            arrow_path.lineTo(-8, 14)
            arrow_path.closeSubpath()
            painter.drawPath(arrow_path)
            
        # Draw a subtle "dot" to show where the handle is
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self.color))
        painter.setOpacity(0.5)
        painter.drawEllipse(1, 4, 4, 4) # Small dot
        painter.setOpacity(1.0)
