import pytest
from unittest.mock import MagicMock
from PySide6.QtCore import Qt
from src.ui.components.outline_panel import OutlinePanel

@pytest.fixture
def mock_outline_manager():
    manager = MagicMock()
    # Mock a root node
    manager.get_node.return_value = {
        "id": "root",
        "title": "Test Outline",
        "range": {"start": "Genesis 1:1", "end": "Genesis 1:31"},
        "children": [
            {
                "id": "child1",
                "title": "Section 1",
                "summary": "Summary 1",
                "range": {"start": "Genesis 1:1", "end": "Genesis 1:10"},
                "children": []
            }
        ]
    }
    return manager

def test_outline_panel_send_to_note(qtbot, mock_outline_manager):
    panel = OutlinePanel(mock_outline_manager, root_node_id="root")
    qtbot.addWidget(panel)
    
    # Trigger send to note
    panel._on_send_to_note()
    
    # Verify that add_standalone_note was called on study_manager
    study_manager = mock_outline_manager.study_manager
    study_manager.add_standalone_note.assert_called_once()
    
    args, kwargs = study_manager.add_standalone_note.call_args
    assert kwargs["title"] == "Test Outline"
    assert "<h1>Test Outline</h1>" in kwargs["text"]
    assert "Summary 1" in kwargs["text"]
    assert "Genesis 1:1" in kwargs["text"]

def test_outline_panel_ui_rearrangement(qtbot, mock_outline_manager):
    panel = OutlinePanel(mock_outline_manager, root_node_id="root")
    qtbot.addWidget(panel)
    
    # Check that send_to_note_btn exists
    assert panel.send_to_note_btn.text() == "Send to Note"
    
    # Check that ref_format_combo is in the layout
    # (Checking the structure is harder, but we can verify it exists)
    assert panel.ref_format_combo is not None
