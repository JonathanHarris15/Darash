import pytest
from unittest.mock import MagicMock
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QKeyEvent

from src.scene.scene_input_handler import SceneInputHandler

@pytest.fixture
def mock_scene():
    scene = MagicMock()
    scene.is_drawing_arrow = False
    scene._wheel_accumulator = 0
    scene._zoom_accumulator = 0
    scene.target_font_size = 18
    scene.target_line_spacing = 1.5
    scene.scroll_sens = 120.0
    scene.target_virtual_scroll_y = 0.0
    scene.loader.flat_verses = [{'ref': 'Gen 1:1'}]
    return scene

def test_input_handler_delegates_to_study_handler(mock_scene):
    handler = SceneInputHandler(mock_scene)
    handler.study_handler = MagicMock()
    
    # Test Delete Key
    del_event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Delete, Qt.NoModifier)
    assert handler.handle_key_press(del_event) is True
    handler.study_handler.handle_delete_key.assert_called_once()
    
    # Test Arrow Binding (A)
    a_event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_A, Qt.NoModifier)
    assert handler.handle_key_press(a_event) is True
    handler.study_handler.start_arrow_drawing.assert_called_once()
    
    # Test Strongs Binding (Q)
    q_event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Q, Qt.NoModifier)
    assert handler.handle_key_press(q_event) is True
    handler.study_handler.handle_strongs_lookup.assert_called_once()

def test_input_handler_wheel_accumulator(mock_scene):
    handler = SceneInputHandler(mock_scene)
    
    # Mock a wheel event (QGraphicsSceneWheelEvent retains its own delta() in Qt6)
    wheel_event = MagicMock()
    wheel_event.modifiers.return_value = Qt.NoModifier
    wheel_event.delta.return_value = 120  # Standard mouse scroll tick

    # Let's ensure normal scroll updates wheel accumulator
    mock_scene.state_manager.scroll_timer.isActive.return_value = False
    handler.handle_wheel(wheel_event)
    # 120 / 30 = 4 steps. Accumulator should be 0 after processing.
    assert mock_scene._wheel_accumulator == 0
    assert mock_scene.state_manager.scroll_timer.start.call_count == 1
