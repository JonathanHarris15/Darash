import pytest
from PySide6.QtWidgets import QApplication
from src.scene.reader_scene import ReaderScene
from src.scene.layout_engine import LayoutEngine

@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])

@pytest.fixture
def scene(app):
    return ReaderScene()

def test_reader_pipeline_layout_does_not_crash_on_bad_tokens(scene, qtbot):
    """
    Integration test replacing the VerseLoader data with various edge cases
    to ensure LayoutEngine and OverlayRenderer don't crash when computing chunk boundaries.
    """
    # 1. Provide edge case token lists to simulate XML parsers or simple word lists
    mock_verses = [
        {
            'ref': 'Gen 1:1', 'book': 'Genesis', 'chapter': '1', 'verse_num': '1',
            'text': 'In the beginning',
            'tokens': [["In"], ["the"], ["beginning"]] # Token length 1 (caused ValueError before)
        },
        {
            'ref': 'Gen 1:2', 'book': 'Genesis', 'chapter': '1', 'verse_num': '2',
            'text': 'God created',
            'tokens': [["God", "H430"], ["created", "H1254"]] # Token length 2 (standard JSON)
        }
    ]
    
    scene.loader.flat_verses = mock_verses
    # Update indices
    scene.loader.ref_to_idx = {'Gen 1:1': 0, 'Gen 1:2': 1}
    scene.loader.ref_map = {v['ref']: v for v in mock_verses}
    
    # We must patch load_chapter_multi to return our mock verses cleanly for the translations required
    original_load = scene.loader.load_chapter_multi
    def mock_load_multi(book, chapter, translations):
        results = {}
        for v in mock_verses:
            if v['book'] == book and int(v['chapter']) == chapter:
                results[v['verse_num']] = { 'ESV': v } 
        return results
    scene.loader.load_chapter_multi = mock_load_multi
    
    # Recalculate layout
    try:
        scene.recalculate_layout(800)
    except ValueError as e:
        pytest.fail(f"LayoutEngine raised ValueError on layout calculation: {e}")
        
    # Ensure maps populated
    assert 'Gen 1:1' in scene.verse_y_map
    assert 'Gen 1:2' in scene.verse_y_map
    
    # Let's ensure _get_word_idx_from_pos doesn't crash on standard interaction logic
    verse_1 = mock_verses[0]
    idx1 = scene.layout_engine._get_word_idx_from_pos(verse_1, 0)
    assert idx1 == 0 # "In"
    
    verse_2 = mock_verses[1]
    idx2 = scene.layout_engine._get_word_idx_from_pos(verse_2, 5) # "God cr" -> index 1 is "created"
    assert idx2 == 1
    
    scene.loader.load_chapter_multi = original_load
