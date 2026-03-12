import pytest
from unittest.mock import MagicMock
from PySide6.QtWidgets import QApplication

from src.ui.components.study_tree import StudyTreeWidget
from src.ui.components.study_tree_populator import StudyTreePopulator

@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])

@pytest.fixture
def mock_study_manager():
    sm = MagicMock()
    # Mock some data
    sm.data = {
        'marks': [{'type': 'highlight', 'color': '#ff0000', 'book': 'Gen', 'chapter': 1, 'verse_num': 1}],
        'notes': {'Gen 1:2': [{'id': '123', 'content': 'Test note'}]},
        'symbols': {'Gen 1:3': 'cross'}
    }
    sm.outline_manager.get_outlines.return_value = []
    return sm

def test_study_tree_populator_initialization(app, mock_study_manager):
    mock_symbol_manager = MagicMock()
    tree = StudyTreeWidget(mock_study_manager, mock_symbol_manager)
    populator = StudyTreePopulator(tree)
    
    # Trigger full layout refresh
    populator.populate_all()
    
    # Tree should have sections for Outlines, Marks, Symbols, Notes, Bookmarks
    top_level_items = [tree.topLevelItem(i).text(0) for i in range(tree.topLevelItemCount())]
    assert "Outlines" in top_level_items
    assert "Marks" in top_level_items
    assert "Symbols" in top_level_items
    assert "Notes" in top_level_items
    assert "Bookmarks" in top_level_items
