import pytest
from unittest.mock import MagicMock
from PySide6.QtCore import Qt
from PySide6.QtGui import QWheelEvent, QKeyEvent
from PySide6.QtCore import QPointF
from src.scene.reader_scene import ReaderScene

def test_reader_scene_event_delegation(qtbot):
    """
    Verify that ReaderScene delegates wheel and key events to its input_handler.
    This is a 'foolproof' regression test to prevent accidental deletion of event overrides.
    """
    scene = ReaderScene()
    
    # Mock the input handler
    mock_handler = MagicMock()
    scene.input_handler = mock_handler
    
    # 1. Test wheelEvent delegation
    mock_event = MagicMock()
    scene.wheelEvent(mock_event)
    mock_handler.handle_wheel.assert_called_once_with(mock_event)
    
    # 2. Test keyPressEvent delegation
    mock_key_event = MagicMock()
    scene.keyPressEvent(mock_key_event)
    mock_handler.handle_key_press.assert_called_once_with(mock_key_event)
    
    # 3. Test contextMenuEvent delegation (just for completeness)
    # This requires more complex mocking of the event, but let's at least check the method exists
    assert hasattr(scene, 'contextMenuEvent')
    assert hasattr(scene, 'mousePressEvent')
    assert hasattr(scene, 'mouseReleaseEvent')
    assert hasattr(scene, 'mouseMoveEvent')

def test_reader_scene_methods_existence():
    """Verify that critical overrides are present in the class definition."""
    # This checks that we didn't just inherit them from QGraphicsScene without overriding
    overrides = ReaderScene.__dict__
    assert 'wheelEvent' in overrides
    assert 'keyPressEvent' in overrides
    assert 'contextMenuEvent' in overrides
    assert 'mousePressEvent' in overrides
    assert 'mouseReleaseEvent' in overrides
    assert 'mouseMoveEvent' in overrides
