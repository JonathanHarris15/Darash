from PySide6.QtWidgets import QGraphicsTextItem, QStyle, QGraphicsObject
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QFont, QFontMetrics

class NoFocusTextItem(QGraphicsTextItem):
    """Custom QGraphicsTextItem that doesn't draw a dashed focus rectangle."""
    def paint(self, painter, option, widget=None):
        if option.state & QStyle.State_HasFocus:
            option.state &= ~QStyle.State_HasFocus
        super().paint(painter, option, widget)

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
