import os
from spellchecker import SpellChecker
from src.utils.path_utils import get_user_data_path

class SpellcheckManager:
    """
    Manages the spellcheck engine and the custom dictionary of ignored words.
    """
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = SpellcheckManager()
        return cls._instance

    def __init__(self):
        try:
            self.spell = SpellChecker()
            self.enabled = True
        except Exception as e:
            print(f"Failed to initialize SpellChecker: {e}")
            self.spell = None
            self.enabled = False
            
        self.ignored_words_path = get_user_data_path("ignored_words.txt")
        self.ignored_words = set()
        self._load_ignored_words()

    def _load_ignored_words(self):
        """Loads ignored words from the user data directory."""
        if not self.enabled: return
        if os.path.exists(self.ignored_words_path):
            try:
                with open(self.ignored_words_path, "r", encoding="utf-8") as f:
                    self.ignored_words = {line.strip().lower() for line in f if line.strip()}
                if self.spell:
                    self.spell.word_frequency.load_words(self.ignored_words)
            except Exception as e:
                print(f"Error loading ignored words: {e}")

    def _save_ignored_words(self):
        """Saves ignored words to the user data directory."""
        if not self.enabled: return
        try:
            with open(self.ignored_words_path, "w", encoding="utf-8") as f:
                for word in sorted(self.ignored_words):
                    f.write(f"{word}\n")
        except Exception as e:
            print(f"Error saving ignored words: {e}")

    def is_misspelled(self, word: str) -> bool:
        """Checks if a word is misspelled, considering the ignored words."""
        if not self.enabled or not self.spell:
            return False
            
        if not word or not word.isalpha():
            return False
        
        word_lower = word.lower()
        if word_lower in self.ignored_words:
            return False
            
        return len(self.spell.unknown([word_lower])) > 0

    def get_suggestions(self, word: str):
        """Returns a list of suggested corrections for a misspelled word."""
        if not self.enabled or not self.spell:
            return []
        return list(self.spell.candidates(word.lower())) or []

    def ignore_word(self, word: str):
        """Adds a word to the custom dictionary and saves it."""
        if not self.enabled: return
        word_lower = word.lower()
        if word_lower not in self.ignored_words:
            self.ignored_words.add(word_lower)
            if self.spell:
                self.spell.word_frequency.load_words([word_lower])
            self._save_ignored_words()
