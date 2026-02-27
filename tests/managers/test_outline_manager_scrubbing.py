import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.managers.outline_manager import OutlineManager

class MockLoader:
    def __init__(self):
        self.flat_verses = [{'ref': f'v{v}'} for v in range(1, 101)]

    def get_verse_index(self, ref):
        try:
            val = float(ref.replace('v', '')) - 1
            if val < 0 or val >= len(self.flat_verses):
                return -1.0
            return val
        except:
            return -1.0

class MockStudyManager:
    def __init__(self, data=None):
        self.data = data or {"outlines": []}
        self.loader = MockLoader()
        
    def save_study(self):
        pass

def outline_manager():
    # Setup an outline tree:
    # Root: v1-v10
    #   C1: v1-v5
    #   C2: v6-v10
    data = {
        "outlines": [
            {
                "id": "root",
                "title": "Main Outline",
                "range": {"start": "v1", "end": "v10"},
                "children": [
                    {
                        "id": "c1",
                        "title": "Point 1",
                        "range": {"start": "v1", "end": "v5"},
                        "children": []
                    },
                    {
                        "id": "c2",
                        "title": "Point 2",
                        "range": {"start": "v6", "end": "v10"},
                        "children": []
                    }
                ]
            }
        ]
    }
    sm = MockStudyManager(data)
    return OutlineManager(sm)

def test_drag_down_internal_end_expands_point(manager):
    loader = manager.study_manager.loader
    changed = manager.adjust_node_boundary("root", "c1", False, 2, loader)
    assert changed is True
    root = manager.get_node("root")
    assert root["children"][0]["range"]["end"] == "v7"
    assert root["children"][1]["range"]["start"] == "v8"

def test_drag_up_internal_start_expands_point(manager):
    loader = manager.study_manager.loader
    changed = manager.adjust_node_boundary("root", "c2", True, -2, loader)
    assert changed is True
    root = manager.get_node("root")
    assert root["children"][1]["range"]["start"] == "v4"
    assert root["children"][0]["range"]["end"] == "v3"
    
def test_drag_down_external_end_expands_outline(manager):
    loader = manager.study_manager.loader
    changed = manager.adjust_node_boundary("root", "c2", False, 5, loader)
    assert changed is True
    root = manager.get_node("root")
    assert root["range"]["end"] == "v15"
    assert root["children"][1]["range"]["end"] == "v15"

def test_constraint_prevents_collapsing_node(manager):
    loader = manager.study_manager.loader
    manager.adjust_node_boundary("root", "c2", True, 5, loader)
    root = manager.get_node("root")
    assert root["children"][1]["range"]["start"] == "v10"
    assert root["children"][1]["range"]["end"] == "v10"
    assert root["children"][0]["range"]["end"] == "v9"
    
def test_constraint_prevents_collapsing_end(manager):
    loader = manager.study_manager.loader
    manager.adjust_node_boundary("root", "c1", False, -5, loader)
    root = manager.get_node("root")
    assert root["children"][0]["range"]["start"] == "v1"
    assert root["children"][0]["range"]["end"] == "v1"
    assert root["children"][1]["range"]["start"] == "v2"

if __name__ == '__main__':
    print("Running tests...")
    test_drag_down_internal_end_expands_point(outline_manager())
    test_drag_up_internal_start_expands_point(outline_manager())
    test_drag_down_external_end_expands_outline(outline_manager())
    test_constraint_prevents_collapsing_node(outline_manager())
    test_constraint_prevents_collapsing_end(outline_manager())
    print("All tests passed successfully!")
