import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from src.managers.study_manager import StudyManager

class TestStudyManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = self.temp_dir.name
        
        # We don't necessarily need a real VerseLoader for basic StudyManager tests
        self.mock_loader = MagicMock()
        
        self.manager = StudyManager(loader=self.mock_loader, base_dir=self.base_dir)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_initialization(self):
        self.assertEqual(self.manager.base_dir, self.base_dir)
        self.assertIsNotNone(self.manager.data)
        self.assertIn("symbols", self.manager.data)
        self.assertIn("marks", self.manager.data)

    def test_load_and_save_data(self):
        # Modify data and save
        self.manager.data["symbols"]["test_key"] = "test_symbol"
        self.manager.save_data()
        
        # Load in a new manager
        new_manager = StudyManager(loader=self.mock_loader, base_dir=self.base_dir)
        new_manager.load_data()
        
        self.assertIn("test_key", new_manager.data["symbols"])
        self.assertEqual(new_manager.data["symbols"]["test_key"], "test_symbol")

    def test_add_bookmark(self):
        self.manager.add_bookmark("Genesis", "1", "1", "#FF0000")
        
        self.assertEqual(len(self.manager.data["bookmarks"]), 1)
        b = self.manager.data["bookmarks"][0]
        self.assertEqual(b["ref"], "Genesis 1:1")
        self.assertEqual(b["color"], "#FF0000")
        
        # Test duplicate prevention
        self.manager.add_bookmark("Genesis", "1", "1", "#00FF00")
        self.assertEqual(len(self.manager.data["bookmarks"]), 1)
        
    def test_delete_bookmark(self):
        self.manager.add_bookmark("Genesis", "1", "1")
        self.manager.add_bookmark("John", "1", "1")
        
        self.manager.delete_bookmark("Genesis 1:1")
        self.assertEqual(len(self.manager.data["bookmarks"]), 1)
        self.assertEqual(self.manager.data["bookmarks"][0]["ref"], "John 1:1")

    def test_add_and_undo_symbol(self):
        self.manager.add_symbol("Genesis", "1", "1", 0, "symbol_1")
        key = "Genesis|1|1|0"
        self.assertIn(key, self.manager.data["symbols"])
        self.assertEqual(self.manager.data["symbols"][key], "symbol_1")
        
        # Test undo
        self.assertTrue(self.manager.undo())
        self.assertNotIn(key, self.manager.data["symbols"])
        
    def test_standalone_note(self):
        key = self.manager.add_standalone_note(title="My Note", text="Hello World", folder="")
        self.assertTrue(key.startswith("standalone_"))
        
        note = self.manager.data["notes"][key]
        self.assertEqual(note["title"], "My Note")
        self.assertEqual(note["text"], "Hello World")
        self.assertEqual(note["folder"], "")

    def test_logical_mark(self):
        # Adding a logical mark
        self.manager.add_logical_mark("Genesis|1|1|0", "arrow_right")
        self.assertIn("Genesis|1|1|0", self.manager.data["logical_marks"])
        self.assertEqual(self.manager.data["logical_marks"]["Genesis|1|1|0"], "arrow_right")
        
        # Test simulated delete
        del self.manager.data["logical_marks"]["Genesis|1|1|0"]
        self.assertNotIn("Genesis|1|1|0", self.manager.data["logical_marks"])

    def test_arrow(self):
        # Adding an arrow
        self.manager.add_arrow("Genesis|1|1|0", "Genesis|1|1|5", color="#FF0000", arrow_type="snake")
        self.assertIn("Genesis|1|1|0", self.manager.data["arrows"])
        arrows = self.manager.data["arrows"]["Genesis|1|1|0"]
        self.assertEqual(len(arrows), 1)
        self.assertEqual(arrows[0]["end_key"], "Genesis|1|1|5")
        self.assertEqual(arrows[0]["color"], "#FF0000")
        self.assertEqual(arrows[0]["type"], "snake")

        # Simulated delete
        del self.manager.data["arrows"]["Genesis|1|1|0"]
        self.assertNotIn("Genesis|1|1|0", self.manager.data["arrows"])

if __name__ == '__main__':
    unittest.main()