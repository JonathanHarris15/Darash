import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from PySide6.QtWidgets import QApplication
from src.core.verse_loader import VerseLoader
from scripts.lab.harness import HotReloadHarness

def main():
    app = QApplication(sys.argv)
    
    # dependencies
    loader = VerseLoader()
    
    def factory(cls):
        return cls(loader)

    # Use the HotReloadHarness
    harness = HotReloadHarness(
        module_name="src.ui.components.navigation",
        class_name="NavigationDock",
        factory_func=factory
    )
    harness.show()
    
    print("Hot-Reload Lab started. Edit src/ui/components/navigation.py and save to see changes.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
