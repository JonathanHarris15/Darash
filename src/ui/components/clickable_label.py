from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt, Signal

class ClickableLabel(QLabel):
    clicked = Signal()
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self.setStyleSheet(self.styleSheet().replace("background-color: rgba(30, 30, 30, 200)", "background-color: rgba(60, 60, 60, 220)"))
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet(self.styleSheet().replace("background-color: rgba(60, 60, 60, 220)", "background-color: rgba(30, 30, 30, 200)"))
        super().leaveEvent(event)
