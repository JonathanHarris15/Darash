"""
SplitOverlayWidget — transparent overlay drawn on top of center_workspace
that shows the VS Code-style drop-zone suggestion when dragging a center panel.
"""
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPainter, QColor, QPen


class SplitOverlayWidget(QWidget):
    """
    A fully-transparent-for-input overlay child of center_workspace.
    Draws a semi-transparent highlight rectangle to indicate where a dragged
    panel will be placed if the user releases the mouse here.
    """

    _FILL  = QColor(0, 120, 215, 70)   # VS Code-style blue, mostly transparent
    _BORDER = QColor(0, 120, 215, 220)  # Solid border on the same blue

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._rect: QRect | None = None
        self.hide()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show_suggestion(self, rect: QRect) -> None:
        """Show the highlight over *rect* (in parent/center_workspace coords)."""
        self._rect = rect
        self.resize(self.parentWidget().size())
        self.raise_()
        self.show()
        self.update()

    def clear(self) -> None:
        """Hide the overlay and remove the suggestion rectangle."""
        self._rect = None
        self.hide()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802
        if self._rect is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.fillRect(self._rect, self._FILL)
        painter.setPen(QPen(self._BORDER, 2))
        painter.drawRect(self._rect.adjusted(1, 1, -1, -1))
        painter.end()
