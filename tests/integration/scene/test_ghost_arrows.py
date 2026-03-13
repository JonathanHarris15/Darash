import unittest
from unittest.mock import MagicMock, patch, call
from PySide6.QtCore import QRectF, QPointF
from src.scene.scene_overlay_manager import SceneOverlayManager
from src.scene.components.reader_items import GhostArrowIconItem, ArrowItem, SnakeArrowItem


class TestGhostArrowOverlay(unittest.TestCase):
    """Tests for ghost arrow rendering via SceneOverlayManager."""

    def setUp(self):
        self.mock_scene = MagicMock()
        self.mock_scene.study_overlay_items = []
        self.mock_scene.verse_pos_map = {"Genesis 1:1": 0}
        self.mock_scene._get_text_rects.return_value = [QRectF(0, 0, 10, 10)]
        self.mock_scene.layout_engine._get_word_rect.return_value = QRectF(0, 0, 10, 10)
        self.mock_scene._is_rect_visible.return_value = True

        self.mock_scene._get_word_offset_in_verse.return_value = 0
        self.mock_scene._get_word_center.return_value = QPointF(25, 7)

        mock_loader = MagicMock()
        mock_loader.get_verse_by_ref.return_value = {
            "tokens": [("In", ""), ("the", ""), ("beginning", "")]
        }
        self.mock_scene.loader = mock_loader

        mock_study_manager = MagicMock()
        mock_study_manager.data = {
            "marks": [],
            "logical_marks": {},
            "symbols": {},
            "notes": {},
            "arrows": {}
        }
        self.mock_scene.study_manager = mock_study_manager

        self.overlay_manager = SceneOverlayManager(self.mock_scene)
        self.overlay_manager.path_finder = MagicMock()

    # ----------------------------------------------------------
    # Ghost arrow renders icons, NOT an ArrowItem
    # ----------------------------------------------------------

    def test_ghost_arrow_renders_two_icons_not_arrow_item(self):
        self.mock_scene.study_manager.data["arrows"]["Genesis|1|1|0"] = [
            {"end_key": "Genesis|1|1|2", "color": "#ffffff99", "type": "ghost"}
        ]
        self.overlay_manager._render_arrows_layer()

        items = self.mock_scene.study_overlay_items
        # Exactly two GhostArrowIconItems should be present
        ghost_icons = [i for i in items if isinstance(i, GhostArrowIconItem)]
        regular_arrows = [i for i in items if isinstance(i, (ArrowItem, SnakeArrowItem))]

        self.assertEqual(len(ghost_icons), 2,
                         "Expected exactly 2 GhostArrowIconItems for a ghost arrow")
        self.assertEqual(len(regular_arrows), 0,
                         "Ghost arrow must not produce a visible ArrowItem or SnakeArrowItem")

    def test_ghost_icon_keys_are_set_correctly(self):
        self.mock_scene.study_manager.data["arrows"]["Genesis|1|1|0"] = [
            {"end_key": "Genesis|1|1|2", "color": "#ffffff99", "type": "ghost"}
        ]
        self.overlay_manager._render_arrows_layer()

        items = self.mock_scene.study_overlay_items
        ghost_icons = [i for i in items if isinstance(i, GhostArrowIconItem)]

        own_keys = {i.own_key for i in ghost_icons}
        partner_keys = {i.partner_key for i in ghost_icons}

        self.assertIn("Genesis|1|1|0", own_keys)
        self.assertIn("Genesis|1|1|2", own_keys)
        # Each icon's partner is the other word
        for icon in ghost_icons:
            self.assertNotEqual(icon.own_key, icon.partner_key)

    def test_ghost_icon_map_populated(self):
        self.mock_scene.study_manager.data["arrows"]["Genesis|1|1|0"] = [
            {"end_key": "Genesis|1|1|2", "color": "#ffffff99", "type": "ghost"}
        ]
        self.overlay_manager._render_arrows_layer()

        self.assertIn("Genesis|1|1|0", self.overlay_manager._ghost_icon_map)
        self.assertIn("Genesis|1|1|2", self.overlay_manager._ghost_icon_map)

    # ----------------------------------------------------------
    # Existing arrow types still work (regression)
    # ----------------------------------------------------------

    def test_straight_arrow_still_renders_arrow_item(self):
        self.mock_scene.study_manager.data["arrows"]["Genesis|1|1|0"] = [
            {"end_key": "Genesis|1|1|2", "color": "#FF0000", "type": "straight"}
        ]
        self.overlay_manager._render_arrows_layer()
        items = self.mock_scene.study_overlay_items
        self.assertEqual(len([i for i in items if isinstance(i, ArrowItem)]), 1)

    def test_snake_arrow_still_renders_snake_item(self):
        self.overlay_manager.path_finder.calculate_path.return_value = [
            QPointF(0, 0), QPointF(10, 10)
        ]
        self.mock_scene.study_manager.data["arrows"]["Genesis|1|1|0"] = [
            {"end_key": "Genesis|1|1|2", "color": "#00FF00", "type": "snake"}
        ]
        self.overlay_manager._render_arrows_layer()
        items = self.mock_scene.study_overlay_items
        self.assertEqual(len([i for i in items if isinstance(i, SnakeArrowItem)]), 1)

    # ----------------------------------------------------------
    # Ghost hover coordination
    # ----------------------------------------------------------

    def test_hover_enter_adds_highlights(self):
        self.mock_scene.study_manager.data["arrows"]["Genesis|1|1|0"] = [
            {"end_key": "Genesis|1|1|2", "color": "#ffffff99", "type": "ghost"}
        ]
        self.overlay_manager._render_arrows_layer()

        # Hover over the start word
        self.overlay_manager.on_word_hover("Genesis|1|1|0")
        self.assertEqual(len(self.overlay_manager._active_ghost_highlights), 2)

    def test_hover_leave_clears_highlights(self):
        self.mock_scene.study_manager.data["arrows"]["Genesis|1|1|0"] = [
            {"end_key": "Genesis|1|1|2", "color": "#ffffff99", "type": "ghost"}
        ]
        self.overlay_manager._render_arrows_layer()
        self.overlay_manager.on_word_hover("Genesis|1|1|0")
        self.overlay_manager.on_word_hover_leave()
        self.assertEqual(len(self.overlay_manager._active_ghost_highlights), 0)


class TestGhostArrowDeletion(unittest.TestCase):
    """Tests for ghost arrow deletion via SceneInputHandler."""

    def _make_handler(self, arrows):
        """Create a SceneInputHandler with a mock scene containing the given arrows."""
        from src.scene.scene_input_handler import SceneInputHandler
        from src.scene.scene_study_input_handler import SceneStudyInputHandler
        mock_scene = MagicMock()
        mock_scene.study_manager.data = {
            "symbols": {},
            "arrows": arrows,
            "logical_marks": {}
        }
        mock_scene.views.return_value = [MagicMock()]
        handler = SceneInputHandler(mock_scene)
        # Prevent Strongs timer from trying to start
        handler.strongs_hover_timer = MagicMock()
        return handler, mock_scene

    def _call_delete_for_key(self, handler, mock_scene, key_str):
        """Simulate _handle_delete_key finding key_str at the mouse position."""
        from src.scene.scene_input_handler import SceneInputHandler
        mock_scene.last_mouse_scene_pos = QPointF(0, 0)
        # itemAt returns None (no OutlineDividerItem)
        mock_scene.itemAt.return_value = None
        mock_scene._get_word_key_at_pos.return_value = key_str
        handler.study_handler.handle_delete_key()

    def test_delete_by_start_key_removes_arrow(self):
        arrows = {
            "Genesis|1|1|0": [
                {"end_key": "Genesis|1|1|2", "color": "#fff", "type": "ghost"}
            ]
        }
        handler, mock_scene = self._make_handler(arrows)
        self._call_delete_for_key(handler, mock_scene, "Genesis|1|1|0")
        self.assertNotIn("Genesis|1|1|0", mock_scene.study_manager.data["arrows"])

    def test_delete_by_end_key_removes_ghost_arrow(self):
        arrows = {
            "Genesis|1|1|0": [
                {"end_key": "Genesis|1|1|2", "color": "#fff", "type": "ghost"}
            ]
        }
        handler, mock_scene = self._make_handler(arrows)
        self._call_delete_for_key(handler, mock_scene, "Genesis|1|1|2")
        # The start key entry should be gone (list was emptied)
        remaining = mock_scene.study_manager.data["arrows"]
        self.assertFalse(
            any(
                a.get('end_key') == "Genesis|1|1|2" and a.get('type') == 'ghost'
                for lst in remaining.values() for a in lst
            ),
            "Ghost arrow should be removed when deleting the end word"
        )

    def test_delete_by_end_key_keeps_other_arrows(self):
        """Deleting a ghost arrow by end-key must not affect other arrows on the same start word."""
        arrows = {
            "Genesis|1|1|0": [
                {"end_key": "Genesis|1|1|2", "color": "#fff", "type": "ghost"},
                {"end_key": "Genesis|1|1|5", "color": "#fff", "type": "straight"},
            ]
        }
        handler, mock_scene = self._make_handler(arrows)
        self._call_delete_for_key(handler, mock_scene, "Genesis|1|1|2")
        # Start key should still exist with one arrow remaining
        remaining = mock_scene.study_manager.data["arrows"].get("Genesis|1|1|0", [])
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["end_key"], "Genesis|1|1|5")


if __name__ == '__main__':
    unittest.main()
