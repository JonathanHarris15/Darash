import pytest
from PySide6.QtCore import Qt
from src.ui.components.spellcheck_title_edit import SpellcheckTitleEdit

def test_spellcheck_title_edit_single_line(qtbot):
    edit = SpellcheckTitleEdit()
    qtbot.addWidget(edit)
    
    # Try to insert a newline
    qtbot.keyClick(edit, Qt.Key_A)
    qtbot.keyClick(edit, Qt.Key_Return)
    qtbot.keyClick(edit, Qt.Key_B)
    
    # Newline should be blocked, resulting in "AB"
    assert edit.text() == "AB"
    
def test_spellcheck_title_edit_interface(qtbot):
    edit = SpellcheckTitleEdit("Initial Title")
    qtbot.addWidget(edit)
    assert edit.text() == "Initial Title"
    
    edit.setText("New Title")
    assert edit.text() == "New Title"
    
    # Verify highlighter is attached
    assert edit.highlighter is not None

def test_spellcheck_title_edit_paste(qtbot):
    edit = SpellcheckTitleEdit()
    qtbot.addWidget(edit)
    from PySide6.QtCore import QMimeData
    mime = QMimeData()
    mime.setText("Line 1\nLine 2")
    
    edit.insertFromMimeData(mime)
    # Newline should be replaced with space
    assert edit.text() == "Line 1 Line 2"
