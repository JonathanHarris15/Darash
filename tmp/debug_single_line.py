import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from src.ui.components.spellcheck_title_edit import SpellcheckTitleEdit

app = QApplication(sys.argv)

def test():
    edit = SpellcheckTitleEdit()
    
    # Simulate keys
    from PySide6.QtGui import QKeyEvent
    
    def send_key(key, text=""):
        ev = QKeyEvent(QKeyEvent.KeyPress, key, Qt.NoModifier, text)
        edit.keyPressEvent(ev)
    
    send_key(Qt.Key_A, "A")
    send_key(Qt.Key_Return, "\n")
    send_key(Qt.Key_B, "B")
    
    print(f"Final text: '{edit.text()}'")
    if edit.text() == "AB":
        print("SUCCESS")
    elif "\n" in edit.text():
        print("FAILURE: Newline found")
    else:
        print("FAILURE: Other")

test()
