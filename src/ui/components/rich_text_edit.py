from PySide6.QtWidgets import QTextEdit
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import (
    QTextCharFormat, QTextCursor, QTextListFormat, QMouseEvent
)

class RichTextEdit(QTextEdit):
    """QTextEdit with anchor-click support and Tab/Shift+Tab indentation."""
    anchorClicked = Signal(QUrl)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cursorPositionChanged.connect(self._break_link_format)

    def _break_link_format(self):
        cursor = self.textCursor()
        if cursor.hasSelection(): return
        fmt = cursor.charFormat()
        if fmt.anchorHref():
            plain = QTextCharFormat(fmt)
            plain.setAnchor(False); plain.setAnchorHref(""); plain.setAnchorNames([]); plain.setFontUnderline(False); plain.clearForeground()
            self.setCurrentCharFormat(plain)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            anchor = self.anchorAt(event.position().toPoint())
            if anchor:
                self.anchorClicked.emit(QUrl(anchor))
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        anchor = self.anchorAt(event.position().toPoint())
        self.viewport().setCursor(Qt.PointingHandCursor if anchor else Qt.IBeamCursor)
        super().mouseMoveEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Tab: self._change_indent(+1); event.accept(); return
        if event.key() == Qt.Key_Backtab: self._change_indent(-1); event.accept(); return
        super().keyPressEvent(event)

    def _change_indent(self, delta: int):
        _BULLET_CYCLE = [QTextListFormat.ListDisc, QTextListFormat.ListCircle, QTextListFormat.ListSquare]
        cursor = self.textCursor(); lst = cursor.currentList()
        if lst:
            fmt = QTextListFormat(lst.format())
            new_indent = max(1, fmt.indent() + delta); fmt.setIndent(new_indent)
            if fmt.style() in _BULLET_CYCLE: fmt.setStyle(_BULLET_CYCLE[(new_indent - 1) % len(_BULLET_CYCLE)])
            block = cursor.block(); doc = self.document(); merged = False
            for adj_block in (block.previous(), block.next()):
                if not adj_block.isValid(): continue
                adj_cursor = QTextCursor(doc); adj_cursor.setPosition(adj_block.position())
                adj_lst = adj_cursor.currentList()
                if adj_lst and adj_lst.format().indent() == new_indent and adj_lst.format().style() == fmt.style():
                    adj_lst.add(block); merged = True; break
            if not merged: cursor.createList(fmt)
        else:
            block_fmt = cursor.blockFormat(); new_indent = max(0, block_fmt.indent() + delta)
            block_fmt.setIndent(new_indent); cursor.setBlockFormat(block_fmt)
