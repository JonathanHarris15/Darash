from PySide6.QtWidgets import QGraphicsObject
from PySide6.QtCore import Qt, QRectF

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
