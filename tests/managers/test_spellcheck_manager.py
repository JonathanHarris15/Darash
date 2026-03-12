import os
import pytest
from src.managers.spellcheck_manager import SpellcheckManager

@pytest.fixture
def spell_manager(tmp_path, monkeypatch):
    # Mock get_user_data_path to use a temporary directory
    mock_path = tmp_path / "ignored_words.txt"
    monkeypatch.setattr("src.managers.spellcheck_manager.get_user_data_path", lambda x: str(tmp_path / x))
    return SpellcheckManager()

def test_is_misspelled_basic(spell_manager):
    assert spell_manager.is_misspelled("hello") == False
    assert spell_manager.is_misspelled("hallo") == True  # Assuming hallo is not in default dict
    assert spell_manager.is_misspelled("123") == False   # Non-alpha should be ignored
    assert spell_manager.is_misspelled("") == False

def test_ignore_word(spell_manager):
    word = "hallo"
    assert spell_manager.is_misspelled(word) == True
    spell_manager.ignore_word(word)
    assert spell_manager.is_misspelled(word) == False
    assert word in spell_manager.ignored_words

def test_persistence(tmp_path, monkeypatch):
    mock_file = tmp_path / "ignored_words.txt"
    monkeypatch.setattr("src.managers.spellcheck_manager.get_user_data_path", lambda x: str(tmp_path / x))
    
    mgr1 = SpellcheckManager()
    mgr1.ignore_word("customword")
    
    # Reload in a new manager instance
    mgr2 = SpellcheckManager()
    assert "customword" in mgr2.ignored_words
    assert mgr2.is_misspelled("customword") == False

def test_get_suggestions(spell_manager):
    suggestions = spell_manager.get_suggestions("hallo")
    assert len(suggestions) > 0
    assert "hello" in suggestions or "halo" in suggestions
