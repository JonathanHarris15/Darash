
import pytest
from unittest.mock import MagicMock
from src.scene.scene_outline_manager import SceneOutlineManager

def test_scene_outline_manager_create_outline():
    # Mock scene and its dependencies
    scene = MagicMock()
    scene.study_manager.outline_manager.create_outline = MagicMock(return_value={"id": "test-id"})
    
    manager = SceneOutlineManager(scene)
    
    # Call the new method
    result = manager.create_outline("Gen 1:1", "Gen 1:10", "Test Title")
    
    # Verify delegation and signals
    assert result == {"id": "test-id"}
    scene.study_manager.outline_manager.create_outline.assert_called_once_with("Gen 1:1", "Gen 1:10", "Test Title", "")
    scene.renderer._render_outline_overlays.assert_called_once()
    scene.studyDataChanged.emit.assert_called_once()
