import pytest
from src.utils.snake_path_finder import SnakePathFinder
from PySide6.QtCore import QPointF, QRectF
from unittest.mock import MagicMock

@pytest.fixture
def mock_scene():
    scene = MagicMock()
    scene.layout_version = 1
    scene.side_margin = 50
    scene.last_width = 800
    scene.study_manager.data = {"arrows": {}}
    return scene

def test_snake_path_finder_initialization(mock_scene):
    finder = SnakePathFinder(mock_scene)
    assert finder.scene == mock_scene

def test_calculate_path_same_line(mock_scene):
    finder = SnakePathFinder(mock_scene)
    start_pos = QPointF(100, 100)
    end_pos = QPointF(200, 100)
    
    # Mock scene methods used by finder
    mock_scene._get_word_center.side_effect = lambda key: start_pos if "start" in key else end_pos
    
    line_rect = QRectF(50, 90, 700, 20)
    # Mock _get_line_info as it's an internal helper that uses layout
    finder._get_line_info = MagicMock(return_value=(line_rect, 0))
    
    path = finder.calculate_path("start", "end")
    assert len(path) == 4
    assert path[0] == start_pos
    assert path[-1] == end_pos
    # Check that it goes above or below (gutter logic)
    assert path[1].y() != 100 
