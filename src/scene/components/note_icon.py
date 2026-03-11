from PySide6.QtWidgets import QGraphicsEllipseItem
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QPen

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
