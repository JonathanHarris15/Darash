import unittest
from unittest.mock import MagicMock, patch
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QKeyEvent
from src.scene.scene_input_handler import SceneInputHandler

class TestMacDeleteKey(unittest.TestCase):
    def setUp(self):
        self.mock_scene = MagicMock()
        self.mock_scene.last_mouse_scene_pos = QPointF(50, 50)
        self.mock_scene.views.return_value = [MagicMock()]
        self.mock_scene.study_manager = MagicMock()
        self.handler = SceneInputHandler(self.mock_scene)
        # Prevent Strongs timer from trying to start
        self.handler.strongs_hover_timer = MagicMock()

    def test_backspace_triggers_delete(self):
        """Verify that Backspace (Mac Delete) triggers the delete handler."""
        # Mock _handle_delete_key to see if it's called
        with patch.object(SceneInputHandler, '_handle_delete_key') as mock_delete:
            # Simulate Backspace key press
            event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Backspace, Qt.NoModifier)
            handled = self.handler.handle_key_press(event)
            
            self.assertTrue(handled, "Backspace should be handled")
            mock_delete.assert_called_once()

    def test_delete_still_works(self):
        """Verify that standard Delete still triggers the delete handler."""
        with patch.object(SceneInputHandler, '_handle_delete_key') as mock_delete:
            # Simulate Delete key press
            event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Delete, Qt.NoModifier)
            handled = self.handler.handle_key_press(event)
            
            self.assertTrue(handled, "Delete should be handled")
            mock_delete.assert_called_once()

if __name__ == '__main__':
    unittest.main()
