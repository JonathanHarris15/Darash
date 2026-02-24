import unittest
from src.utils.reader_utils import get_word_idx_from_pos, get_word_offset_in_verse

class TestReaderUtils(unittest.TestCase):
    def setUp(self):
        self.mock_verse_data = {
            "text": "In the beginning God created",
            "tokens": [
                ["In", "07225"], 
                ["the", "07225"],
                ["beginning", "07225"],
                ["God", "0430"], 
                ["created", "01254"]
            ]
        }

    def test_get_word_offset_in_verse(self):
        # "In" starts at 0
        self.assertEqual(get_word_offset_in_verse(self.mock_verse_data, 0), 0)
        
        # "the" starts at index 3 ("In " is 3 chars)
        self.assertEqual(get_word_offset_in_verse(self.mock_verse_data, 1), 3)
        
        # "beginning" starts at index 7 ("In the " is 7 chars)
        self.assertEqual(get_word_offset_in_verse(self.mock_verse_data, 2), 7)
        
        # "God" starts at index 17 ("In the beginning " is 17 chars)
        self.assertEqual(get_word_offset_in_verse(self.mock_verse_data, 3), 17)

    def test_get_word_idx_from_pos(self):
        # Pos 0-1 corresponds to "In"
        self.assertEqual(get_word_idx_from_pos(self.mock_verse_data, 0), 0)
        self.assertEqual(get_word_idx_from_pos(self.mock_verse_data, 1), 0)
        
        # Pos 3-5 corresponds to "the"
        self.assertEqual(get_word_idx_from_pos(self.mock_verse_data, 4), 1)
        
        # Pos 17 corresponds to "God"
        self.assertEqual(get_word_idx_from_pos(self.mock_verse_data, 18), 3)

        # Out of bounds
        self.assertEqual(get_word_idx_from_pos(None, 0), -1)
        self.assertEqual(get_word_idx_from_pos(self.mock_verse_data, -5), -1)
        # Position beyond text length will eventually just fall out or return -1
        self.assertEqual(get_word_idx_from_pos(self.mock_verse_data, 100), -1)

if __name__ == '__main__':
    unittest.main()