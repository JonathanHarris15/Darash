import unittest
from unittest.mock import MagicMock, patch
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QKeyEvent, QMouseEvent
from src.scene.reader_scene import ReaderScene
from src.scene.scene_input_handler import SceneInputHandler
from src.utils.reader_utils import get_word_idx_from_pos

class TestSceneInteractionArrows(unittest.TestCase):
    def setUp(self):
        # We need a mocked ReaderScene because doing this with real QGraphicsView
        # requires an actual application event loop and display.
        self.mock_scene = MagicMock()
        self.mock_scene.is_drawing_arrow = False
        self.mock_scene.arrow_start_key = None
        self.mock_scene.arrow_start_center = None
        self.mock_scene.last_mouse_scene_pos = QPointF(50, 50)
        self.mock_scene.views.return_value = [MagicMock()]
        
        # Give the first view a mocked mapping
        mock_view = self.mock_scene.views()[0]
        mock_view.mapToScene.return_value = QPointF(50, 50)
        
        self.mock_study_manager = MagicMock()
        self.mock_scene.study_manager = self.mock_study_manager
        
        self.handler = SceneInputHandler(self.mock_scene)
        # Prevent Strongs timer from trying to start
        self.handler.strongs_hover_timer = MagicMock()
        self.mock_scene.temp_arrow_item = None

    def test_start_arrow_drawing(self):
        # Simulate pressing 'A' to start drawing an arrow
        self.mock_scene._get_word_key_at_pos.return_value = "Genesis|1|1|0"
        self.mock_scene._get_word_center.return_value = QPointF(50, 50)
        
        event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_A, Qt.NoModifier)
        handled = self.handler.handle_key_press(event)
        
        self.assertTrue(handled)
        self.assertTrue(self.mock_scene.is_drawing_arrow)
        self.assertEqual(self.mock_scene.arrow_start_key, "Genesis|1|1|0")
        self.assertEqual(self.mock_scene.arrow_start_center, QPointF(50, 50))
        # Ensure a temporary arrow was created
        self.mock_scene.addItem.assert_called()

    @patch('src.utils.menu_utils.create_menu')
    def test_finish_arrow_drawing(self, mock_create_menu):
        # Set up an ongoing draw
        self.mock_scene.is_drawing_arrow = True
        self.mock_scene.arrow_start_key = "Genesis|1|1|0"
        self.mock_scene.arrow_start_center = QPointF(50, 50)
        
        # Simulate releasing 'A' over a different word
        self.mock_scene._get_word_key_at_pos.return_value = "Genesis|1|1|5"
        
        # Set up the mock menu to return the standard action so we get a straight arrow
        mock_menu_instance = MagicMock()
        mock_create_menu.return_value = mock_menu_instance
        # Suppose the first addAction is Standard
        mock_act_standard = MagicMock()
        mock_menu_instance.addAction.side_effect = [mock_act_standard, MagicMock(), MagicMock()]
        mock_menu_instance.exec.return_value = mock_act_standard

        event = QKeyEvent(QKeyEvent.KeyRelease, Qt.Key_A, Qt.NoModifier)
        handled = self.handler.handle_key_release(event)
        
        self.assertTrue(handled)
        self.assertFalse(self.mock_scene.is_drawing_arrow)
        self.assertIsNone(self.mock_scene.arrow_start_key)
        self.assertIsNone(self.mock_scene.arrow_start_center)
        # Ensure study manager was called to persist the arrow
        self.mock_study_manager.add_arrow.assert_called_with(
            "Genesis|1|1|0", "Genesis|1|1|5", "#99ffffff", arrow_type="straight"
        )
        self.mock_scene._render_study_overlays.assert_called()

    def test_arrow_drawing_coordinate_mapping(self):
        """
        Tests that underlying coordinate mapping correctly extracts duplicate words
        (e.g. testing the find() bugfix natively bypassing Qt layouts).
        """
        verse_data = {
            "book": "Genesis", "chapter": 1, "verse_num": 1,
            "text": "God made God",
            "tokens": [["God", "0430"], ["made", "0125"], ["God", "0430"]]
        }
        
        # God made God
        # 012345678901
        
        # Word 0: "God" is pos 0-2 (so hit tests between 0 and 3)
        self.assertEqual(get_word_idx_from_pos(verse_data, 0), 0)
        self.assertEqual(get_word_idx_from_pos(verse_data, 1), 0)
        self.assertEqual(get_word_idx_from_pos(verse_data, 2), 0)
        self.assertEqual(get_word_idx_from_pos(verse_data, 3), 0) # Trailing Space/Bounds
        
        # Word 1: "made" is pos 4-7 (so hit tests 4 to 8)
        self.assertEqual(get_word_idx_from_pos(verse_data, 4), 1)
        self.assertEqual(get_word_idx_from_pos(verse_data, 5), 1)
        self.assertEqual(get_word_idx_from_pos(verse_data, 7), 1)
        self.assertEqual(get_word_idx_from_pos(verse_data, 8), 1) # Trailing Space/Bounds
        
        # Word 2: "God" (The duplicate) is pos 9-11
        # In the original broken code, hit testing index 10 would return index 0
        # because "God" was found at 0. Let's make sure it returns 2 now.
        self.assertEqual(get_word_idx_from_pos(verse_data, 9), 2)
        self.assertEqual(get_word_idx_from_pos(verse_data, 10), 2)
        self.assertEqual(get_word_idx_from_pos(verse_data, 11), 2)

if __name__ == '__main__':
    unittest.main()
