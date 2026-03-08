import sys
from PySide6.QtWidgets import QApplication
from src.utils.update_manager import UpdateManager
from src.core.constants import APP_VERSION

def main():
    print(f"Starting Jehu Reader v{APP_VERSION}...")
    app = QApplication(sys.argv)
    app.setApplicationName("Jehu Reader")
    
    # Check for updates
    release_info = UpdateManager.check_for_updates()
    if release_info:
        from PySide6.QtWidgets import QMessageBox
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Update Available")
        msg.setText(f"A new version ({release_info['tag_name']}) is available.")
        msg.setInformativeText("Would you like to download and install it now? The application will restart.")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.Yes)
        
        if msg.exec() == QMessageBox.Yes:
            if UpdateManager.start_update(release_info):
                sys.exit(0)
    
    print("Initializing UI...")
    window = MainWindow()
    window.showMaximized()
    
    print("Entering main loop...")
    exit_code = app.exec()
    print(f"Exiting with code {exit_code}")
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
