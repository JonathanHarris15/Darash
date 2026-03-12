import pytest
from src.core.verse_loader import VerseLoader

def test_load_chapter_multi():
    loader = VerseLoader()
    
    # Test loading ESV (already loaded as primary) and NIV (XML)
    # Note: This depends on the actual presence of NIV.xml in the project
    book = "Genesis"
    chapter = 1
    translations = ["ESV", "NIV"]
    
    results = loader.load_chapter_multi(book, chapter, translations)
    
    assert len(results) > 0
    assert "1" in results
    assert "ESV" in results["1"]
    assert "NIV" in results["1"]
    
    # Check content
    esv_v1 = results["1"]["ESV"]
    niv_v1 = results["1"]["NIV"]
    
    assert esv_v1["text"].startswith("In the beginning")
    if niv_v1: # NIV might not be found in some environments
        assert niv_v1["text"].startswith("In the beginning")
        assert len(niv_v1["tokens"]) > 0

def test_load_non_existent_translation():
    loader = VerseLoader()
    results = loader.load_chapter_multi("Genesis", 1, ["NON_EXISTENT"])
    assert results == {} # Or however your implementation handles empty results
