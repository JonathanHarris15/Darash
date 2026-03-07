from PySide6.QtWidgets import (
    QGraphicsTextItem, QGraphicsEllipseItem, QGraphicsLineItem,
    QStyle, QGraphicsItem, QGraphicsObject, QGraphicsPathItem
)
from PySide6.QtCore import Qt, QPointF, QLineF, Signal, QRectF
from PySide6.QtGui import QBrush, QColor, QPen, QPainterPath, QPainter
from src.core.constants import VERSE_NUMBER_RESERVED_WIDTH
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


class TranslationIndicatorItem(QGraphicsObject):
    """Tiny label indicating translation, anchored to the right edge of the margin."""
    def __init__(self, text, scene, color, parent=None):
        super().__init__(parent)
        self.text = text
        self.color = color
        
        # Scale directly with scene font size (approx 30%)
        from PySide6.QtGui import QFont
        size = max(6, int(scene.font_size * 0.32))
        self.font = QFont(scene.font_family, size)
        self.font.setBold(True)
        
        from PySide6.QtGui import QFontMetrics
        metrics = QFontMetrics(self.font)
        self._width = metrics.horizontalAdvance(self.text)
        self._height = metrics.height()
        self._ascent = metrics.ascent()
        self.setZValue(11)
        self.setAcceptedMouseButtons(Qt.NoButton)

    def boundingRect(self):
        # Anchor at (0,0) as the BOTTOM-RIGHT corner of the baseline.
        # X goes from -width to 0. Y goes from -ascent to descent.
        return QRectF(-self._width, -self._ascent, self._width, self._height)

    def paint(self, painter, option, widget=None):
        painter.setFont(self.font)
        painter.setPen(self.color)
        painter.setOpacity(0.6)
        # origin Y is the baseline
        painter.drawText(QPointF(-self._width, 0), self.text)

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
        from PySide6.QtGui import QFontMetrics
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

class LogicalMarkItem(QGraphicsObject):
    """
    Renders a logical mark symbol (text/icon) centered behind a word.
    """
    def __init__(self, key, symbol_text, target_rect, color, font_size=16, parent=None):
        super().__init__(parent)
        self.key = key # book|chap|verse|word_idx
        self.symbol_text = symbol_text
        self.target_rect = target_rect
        self.color = color
        self.font = None
        self.font_size = font_size
        self.setAcceptedMouseButtons(Qt.NoButton)
        self.setZValue(-0.5) # Behind text (0), but above highlights (-1)?
        # Highlights are Z=-1. This should be behind text.
        # If highlights are translucent, this behind highlights is fine.
        # But if highlights are opaque (wait, they are translucent), this should be visible.
        # Actually, if this is "opaque behind word", it should be Z=-0.5 so it's on top of highlight but behind text.

    def paint(self, painter, option, widget=None):
        painter.setPen(self.color)
        if not self.font:
            self.font = painter.font()
            self.font.setPixelSize(int(self.target_rect.height() * 2.0)) # Even larger size
            self.font.setBold(True)
            
        painter.setFont(self.font)
        
        # Draw centered in target_rect
        metrics = painter.fontMetrics()
        w = metrics.horizontalAdvance(self.symbol_text)
        h = metrics.height()
        
        x = self.target_rect.center().x() - w / 2
        y = self.target_rect.center().y() + h / 4 # Baseline offset
        
        painter.drawText(x, y, self.symbol_text)

    def boundingRect(self):
        return self.target_rect

class OutlineDividerItem(QGraphicsObject):
    """
    A draggable horizontal line representing a split in the outline.
    """
    dragStarted = Signal(QPointF)
    
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
            self.dragStarted.emit(event.scenePos())
            event.accept()
        else:
            super().mousePressEvent(event)
