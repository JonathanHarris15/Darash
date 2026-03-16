import sys
import traceback
import os
from PySide6.QtWidgets import QApplication
from src.utils.update_manager import UpdateManager
from src.core.constants import APP_VERSION
from src.ui.main_window import MainWindow
from src.utils.path_utils import get_user_data_path

def crash_logger(exctype, value, tb):
    """Global exception handler to catch and log crashes in released builds."""
    import datetime
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    try:
        log_path = get_user_data_path("crash_log.txt")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n--- CRASH LOG: {datetime.datetime.now()} ---\n")
            f.write(error_msg)
    except: pass
    print(error_msg, file=sys.stderr)

sys.excepthook = crash_logger

def main():
    print(f"Starting Jehu Reader v{APP_VERSION}...")
    app = QApplication(sys.argv)
    app.setApplicationName("Jehu Reader")
    
    from src.core.theme import Theme
    app.setStyleSheet(Theme.get_global_stylesheet())
    
    # Check for updates
    release_info, error_msg = UpdateManager.check_for_updates()
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
