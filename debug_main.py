import sys
from PySide6.QtWidgets import QApplication
from src.ui.main_window import MainWindow

def test():
    app = QApplication(sys.argv)
    print("App created")
    try:
        window = MainWindow()
        print("MainWindow created")
        window.show()
        print("Window shown")
        # Add a note panel to see if it works
        window.add_note_panel("test_key", "Test Ref")
        print("Note panel added")
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test()
