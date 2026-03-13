import unittest
from unittest.mock import MagicMock
from PySide6.QtCore import QRectF, QPointF
from src.scene.scene_overlay_manager import SceneOverlayManager
from src.scene.components.reader_items import LogicalMarkItem, ArrowItem, SnakeArrowItem

class TestSceneOverlayManager(unittest.TestCase):
    def setUp(self):
        self.mock_scene = MagicMock()
        self.mock_scene.study_overlay_items = []
        self.mock_scene.verse_pos_map = {"Genesis 1:1": 0}
        self.mock_scene.verse_y_map = {"Genesis 1:1": (0.0, 20.0)}
        self.mock_scene._get_text_rects.return_value = [QRectF(0, 0, 10, 10)]
        self.mock_scene._is_rect_visible.return_value = True
        self.mock_scene._get_word_offset_in_verse.return_value = 5
        self.mock_scene._get_word_center.return_value = QPointF(5, 5)

        # Mock loader returning a dummy token structure
        self.mock_loader = MagicMock()
        self.mock_loader.get_verse_by_ref.return_value = {
            "tokens": [("In", ""), ("the", ""), ("beginning", "")]
        }
        self.mock_scene.loader = self.mock_loader

        # Mock study manager data
        self.mock_study_manager = MagicMock()
        self.mock_study_manager.data = {
            "marks": [],
            "logical_marks": {},
            "symbols": {},
            "notes": {},
            "arrows": {}
        }
        self.mock_scene.study_manager = self.mock_study_manager

        self.overlay_manager = SceneOverlayManager(self.mock_scene)
        # Mock the path finder directly to prevent issues with it needing real scene data
        self.overlay_manager.path_finder = MagicMock()
        self.overlay_manager.path_finder.calculate_path.return_value = [QPointF(0,0), QPointF(10,10)]

    def test_render_marks_layer(self):
        self.mock_study_manager.data["marks"].append({
            "book": "Genesis", "chapter": "1", "verse_num": "1",
            "start": 0, "length": 5, "type": "highlight", "color": "#FFFF00"
        })
        self.overlay_manager._render_marks_layer()
        # Ensure a QGraphicsRectItem was created for the highlight
        self.assertEqual(len(self.mock_scene.study_overlay_items), 1)

    def test_render_logical_marks_layer(self):
        self.mock_study_manager.data["logical_marks"]["Genesis|1|1|0"] = "relation"
        self.overlay_manager._render_logical_marks_layer()
        self.assertEqual(len(self.mock_scene.study_overlay_items), 1)
        self.assertIsInstance(self.mock_scene.study_overlay_items[0], LogicalMarkItem)

    def test_render_arrows_layer(self):
        self.mock_study_manager.data["arrows"]["Genesis|1|1|0"] = [
            {"end_key": "Genesis|1|1|2", "color": "#FF0000", "type": "straight"}
        ]
        self.overlay_manager._render_arrows_layer()
        self.assertEqual(len(self.mock_scene.study_overlay_items), 1)
        self.assertIsInstance(self.mock_scene.study_overlay_items[0], ArrowItem)

    def test_render_snake_arrows_layer(self):
        self.mock_study_manager.data["arrows"]["Genesis|1|1|0"] = [
            {"end_key": "Genesis|1|1|2", "color": "#00FF00", "type": "snake"}
        ]
        self.overlay_manager._render_arrows_layer()
        self.assertEqual(len(self.mock_scene.study_overlay_items), 1)
        self.assertIsInstance(self.mock_scene.study_overlay_items[0], SnakeArrowItem)

if __name__ == '__main__':
    unittest.main()
