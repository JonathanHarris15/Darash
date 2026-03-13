import sys
import os
from PySide6.QtWidgets import QApplication

# Add src to path
sys.path.append(os.getcwd())

def test_note_editor():
    print("Testing NoteEditor initialization...")
    from src.ui.components.note_editor import NoteEditor
    try:
        editor = NoteEditor(initial_text="Test", ref="Gen 1:1", initial_title="Title")
        print("NoteEditor initialized successfully.")
        return True
    except Exception as e:
        print(f"FAILED to initialize NoteEditor: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_outline_panel():
    print("\nTesting OutlinePanel initialization...")
    from src.ui.components.outline_panel import OutlinePanel
    from unittest.mock import MagicMock
    try:
        mock_manager = MagicMock()
        # Mock what refresh() needs
        mock_manager.get_node.return_value = {
            "id": "root",
            "title": "Root",
            "range": {"start": "Gen 1:1", "end": "Gen 1:2"},
            "children": []
        }
        panel = OutlinePanel(mock_manager, root_node_id="root")
        print("OutlinePanel initialized successfully.")
        return True
    except Exception as e:
        print(f"FAILED to initialize OutlinePanel: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    app = QApplication(sys.argv)
    n = test_note_editor()
    o = test_outline_panel()
    if n and o:
        print("\nBoth editors initialized successfully in headless mode.")
    else:
        sys.exit(1)
