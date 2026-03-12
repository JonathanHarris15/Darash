import sys
import os
# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from PySide6.QtWidgets import QApplication
from scripts.lab.harness import HotReloadHarness
from src.ui.theme import Theme

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(Theme.get_global_stylesheet())
    
    # Sample content for the lab
    content = """# Release Notes - v0.1.2

Welcome to Jehu-Reader v0.1.2! This update focuses on internal stability and preparing for new features.

## Key Changes
- **Release Notes Feature**: Stay updated with the latest changes directly in the app.
- **Theme Engine Improvements**: Centralized design tokens for consistent UI styling.
- **Packaging & Updates**: Improved Windows installer and auto-update mechanism.

## Coming Soon
- Enhanced Study Guide integration.
- More translations and improved search operators.

Thank you for using Jehu-Reader!
"""
    
    def factory(cls):
        # We pass the sample content to the dialog
        return cls(content=content, version="0.1.2")

    # Hot-reload harness
    harness = HotReloadHarness(
        module_name="src.ui.components.release_note_dialog",
        class_name="ReleaseNoteDialog",
        factory_func=factory
    )
    harness.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
