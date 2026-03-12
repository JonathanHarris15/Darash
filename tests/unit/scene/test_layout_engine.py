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

def test_layout_engine_initialization(scene):
    assert isinstance(scene.layout_engine, LayoutEngine)
    assert scene.layout_engine.scene == scene

def test_get_ref_from_pos(scene):
    # Mock some pos_verse_map data
    scene.pos_verse_map = [(10, "Gen 1:1"), (20, "Gen 1:2"), (30, "Gen 1:3")]
    
    engine = scene.layout_engine
    assert engine._get_ref_from_pos(5) is None
    assert engine._get_ref_from_pos(10) == "Gen 1:1"
    assert engine._get_ref_from_pos(15) == "Gen 1:1"
    assert engine._get_ref_from_pos(25) == "Gen 1:2"
    assert engine._get_ref_from_pos(35) == "Gen 1:3"

def test_get_verse_y_midpoint(scene):
    scene.verse_y_map = {"Gen 1:1": (0, 100), "Gen 1:2": (100, 200)}
    engine = scene.layout_engine
    assert engine.get_verse_y_midpoint("Gen 1:1", "Gen 1:2") == 100
    assert engine.get_verse_y_midpoint("Unknown", "Gen 1:1") == 0

def test_recalculate_layout_emits_signals(scene, qtbot):
    with qtbot.waitSignal(scene.layoutStarted):
        with qtbot.waitSignal(scene.layoutFinished):
            scene.layout_engine.recalculate_layout(800)
    
    assert scene.last_width == 800
    assert scene.total_height > 0
