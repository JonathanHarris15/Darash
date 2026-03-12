import re
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PySide6.QtCore import Qt

class SpellcheckHighlighter(QSyntaxHighlighter):
    """
    QSyntaxHighlighter that underlines misspelled words.
    """
    def __init__(self, parent, spell_manager):
        super().__init__(parent)
        self.spell_manager = spell_manager
        
        self.misspelled_format = QTextCharFormat()
        self.misspelled_format.setUnderlineStyle(QTextCharFormat.SpellCheckUnderline)
        self.misspelled_format.setUnderlineColor(QColor("#ff4444")) # Soft red

    def highlightBlock(self, text):
        """Highlights misspelled words in the given text block."""
        if not text:
            return

        # Simple word regex: sequence of letters
        # We use finditer to get positions of all words
        for match in re.finditer(r"\b[A-Za-z']+\b", text):
            word = match.group()
            if self.spell_manager.is_misspelled(word):
                self.setFormat(match.start(), match.end() - match.start(), self.misspelled_format)
