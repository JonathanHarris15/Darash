from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QTextCursor
from src.ui.components.rich_text_edit import RichTextEdit
from src.managers.spellcheck_manager import SpellcheckManager

class SpellcheckTitleEdit(RichTextEdit):
    """
    A single-line version of RichTextEdit specifically for titles.
    Mimics QLineEdit behavior (Enter to finish, no newlines) but with spellcheck.
    """
    returnPressed = Signal()

    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self.setAcceptRichText(False)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setTabChangesFocus(True)
        self.setLineWrapMode(RichTextEdit.NoWrap)
        
        # Default single-line height
        self.setFixedHeight(30)
        
        if text:
            self.setPlainText(text)
            
        self.enableSpellcheck(SpellcheckManager.get_instance())

    def text(self):
        """Standard QLineEdit compatibility."""
        return self.toPlainText()

    def setText(self, text):
        """Standard QLineEdit compatibility."""
        self.setPlainText(text)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.returnPressed.emit()
            event.accept()
            return
        
        # Block Tab/Shift+Tab from being handled by RichTextEdit (preventing list/indent)
        if event.key() == Qt.Key_Tab or event.key() == Qt.Key_Backtab:
            event.ignore() # Let parent handle focus changes
            return
            
        super().keyPressEvent(event)

    def insertFromMimeData(self, source):
        """Ensure pasted text is flattened to a single line."""
        text = source.text().replace("\n", " ").replace("\r", " ")
        self.insertPlainText(text)
