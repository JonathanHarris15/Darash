import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QTextCursor
from src.ui.components.note_editor import NoteEditor
from src.ui.components.formatting_toolbar import FormattingToolBar

def test_heading_application(qtbot):
    editor = NoteEditor()
    qtbot.addWidget(editor)
    toolbar = editor.toolbar
    
    # Select some text
    editor.editor.setPlainText("Line 1\nLine 2")
    cursor = editor.editor.textCursor()
    cursor.setPosition(0)
    editor.editor.setTextCursor(cursor)
    
    # Apply Heading 1
    toolbar.style_combo.setCurrentIndex(1) # Heading 1
    
    # Verify block format
    cursor = editor.editor.textCursor()
    cursor.setPosition(0) # Go to start of first block
    assert cursor.blockFormat().headingLevel() == 1
    
    # Verify char format (bold and size)
    fmt = cursor.block().charFormat() # Char format of the block
    assert fmt.fontPointSize() == 22
    assert fmt.fontWeight() == QFont.Bold

def test_heading_sync(qtbot):
    editor = NoteEditor()
    qtbot.addWidget(editor)
    toolbar = editor.toolbar
    
    # Create two blocks, second one is Heading 2
    editor.editor.setHtml("<p>Normal</p><h2>Heading</h2>")
    
    # Move cursor to first block
    cursor = editor.editor.textCursor()
    cursor.setPosition(0)
    editor.editor.setTextCursor(cursor)
    assert toolbar.style_combo.currentIndex() == 0
    
    # Move cursor to second block (heading)
    cursor.movePosition(QTextCursor.End)
    editor.editor.setTextCursor(cursor)
    
    assert toolbar.style_combo.currentIndex() == 2
