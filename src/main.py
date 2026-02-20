import sys
from PySide6.QtWidgets import QApplication
from src.ui import MainWindow

def main():
    print("Starting Jehu Reader...")
    app = QApplication(sys.argv)
    app.setApplicationName("Jehu Reader")
    
    print("Initializing UI...")
    window = MainWindow()
    window.showMaximized()
    
    print("Entering main loop...")
    exit_code = app.exec()
    print(f"Exiting with code {exit_code}")
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
