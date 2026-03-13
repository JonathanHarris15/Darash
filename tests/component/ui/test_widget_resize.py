import pytest
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSize, QRectF, QTimer
from src.ui.reader_widget import ReaderWidget
from src.scene.reader_scene import ReaderScene

@pytest.fixture
def app(qtbot):
    test_app = QApplication.instance()
    if not test_app:
        test_app = QApplication(sys.argv)
    return test_app

def test_delayed_resize_triggers_recalculation(qtbot):
    # We use a real ReaderScene but mock its methods to verify resize propagates
    scene = ReaderScene()
    
    # ReaderWidget will use QTimer, but we can call apply_delayed_resize manually
    widget = ReaderWidget(scene=scene)
    qtbot.addWidget(widget)
    
    # Simulate a resize manually changing the widget size
    # We need to ensure the difference is > 2 pixels
    scene.last_width = 100
    widget.resize(800, 600)
    
    # Wait for the debounced timer or call manually
    # Let's call manually but ensure we wait for any signal processing
    with qtbot.waitSignal(scene.layoutFinished, timeout=2000):
        widget.apply_delayed_resize()
    
    # Ensure the bounds updated correctly
    assert scene.last_width == widget.view.viewport().rect().width()
    assert scene.last_width > 100
