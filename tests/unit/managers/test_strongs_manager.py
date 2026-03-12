import pytest
from src.managers.strongs_manager import StrongsManager
from unittest.mock import MagicMock

@pytest.fixture
def loader():
    loader = MagicMock()
    loader.flat_verses = [
        {"book": "Gen", "chapter": 1, "verse_num": 1, "ref": "Gen 1:1", "tokens": [["In", "H7225"], ["beginning", "H7225"]]},
        {"book": "Gen", "chapter": 1, "verse_num": 2, "ref": "Gen 1:2", "tokens": [["God", "H430"], ["created", "H1254"]]}
    ]
    return loader

def test_strongs_manager_index_usages(loader):
    manager = StrongsManager()
    manager.index_usages(loader)
    
    # H7225 has 2 tokens but snippet logic only records 1 usage per verse
    assert len(manager.usages["H7225"]) == 1
    # H430 has 1 usage
    assert len(manager.usages["H430"]) == 1

def test_get_top_strongs_words(loader):
    manager = StrongsManager()
    manager.index_usages(loader)
    
    # Request top words for Genesis (which is the only book in our mock)
    top_words = manager.get_top_strongs_words("book", "Gen", loader.flat_verses)
    
    # Should have 'in' as top (count 2 in Gen 1:1)
    assert len(top_words) >= 1
    assert top_words[0][0] == "in"
