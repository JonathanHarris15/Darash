import os
import json
import unittest
import tempfile
from src.core.verse_loader import VerseLoader

class TestVerseLoader(unittest.TestCase):
    def setUp(self):
        # Create a temporary JSON file that mimics the structure of the ESV.json
        mock_data = {
            "books": {
                "Genesis": [
                    [
                        [
                            ["In the", "07225"], ["beginning", "07225"],
                            ["God", "0430"], ["created", "01254"]
                        ]
                    ]
                ],
                "John": [
                    [
                        [
                            ["In the", "1722"], ["beginning", "746"],
                            ["was", "2258"], ["the Word", "3056"]
                        ]
                    ]
                ]
            }
        }
        
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        json.dump(mock_data, self.temp_file)
        self.temp_file.close()

    def tearDown(self):
        os.remove(self.temp_file.name)

    def test_verse_loader_initialization(self):
        loader = VerseLoader(json_path=self.temp_file.name)
        
        self.assertEqual(len(loader.data), 2)
        self.assertIn("Genesis", loader.data)
        self.assertIn("John", loader.data)

    def test_verse_loading_and_parsing(self):
        loader = VerseLoader(json_path=self.temp_file.name)
        
        # Check flattening and token splitting
        self.assertEqual(len(loader.flat_verses), 2)
        
        gen_1_1 = loader.get_verse_by_ref("Genesis 1:1")
        self.assertIsNotNone(gen_1_1)
        self.assertEqual(gen_1_1["book"], "Genesis")
        self.assertEqual(gen_1_1["chapter"], "1")
        self.assertEqual(gen_1_1["verse_num"], "1")
        
        # "In the" should be split into "In" and "the"
        self.assertEqual(len(gen_1_1["tokens"]), 5) 
        self.assertEqual(gen_1_1["tokens"][0], ["In", "07225"])
        self.assertEqual(gen_1_1["tokens"][1], ["the", "07225"])
        self.assertEqual(gen_1_1["tokens"][2], ["beginning", "07225"])
        
        # Check text reconstruction
        self.assertEqual(gen_1_1["text"], "In the beginning God created")

    def test_get_verse_index(self):
        loader = VerseLoader(json_path=self.temp_file.name)
        
        self.assertEqual(loader.get_verse_index("Genesis 1:1"), 0.0)
        self.assertEqual(loader.get_verse_index("John 1:1"), 1.0)
        
        # Test sub-verse indexing (e.g., 'a' -> 0.001)
        self.assertAlmostEqual(loader.get_verse_index("Genesis 1:1a"), 0.001)
        self.assertAlmostEqual(loader.get_verse_index("Genesis 1:1b"), 0.002)
        
        self.assertEqual(loader.get_verse_index("Invalid 1:1"), -1.0)

    def test_get_verse(self):
        loader = VerseLoader(json_path=self.temp_file.name)
        
        verse = loader.get_verse("Genesis", 1, 1)
        self.assertIsNotNone(verse)
        self.assertEqual(verse["text"], "In the beginning God created")
        
        verse_invalid = loader.get_verse("Genesis", 2, 1)
        self.assertIsNone(verse_invalid)

if __name__ == '__main__':
    unittest.main()