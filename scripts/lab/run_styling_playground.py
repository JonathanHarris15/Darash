import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from PySide6.QtWidgets import QApplication
from scripts.lab.harness import HotReloadHarness

def main():
    app = QApplication(sys.argv)
    
    # Use the HotReloadHarness
    harness = HotReloadHarness(
        module_name="src.ui.components.styling_playground",
        class_name="StylingPlaygroundPanel"
    )
    harness.show()
    harness.resize(600, 800)
    
    print("Hot-Reload Lab started. Edit src/ui/components/styling_playground.py or src/ui/theme.py and save to see changes.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
