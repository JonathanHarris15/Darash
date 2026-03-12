import unittest
from unittest.mock import MagicMock, call
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSize, QRectF
from src.ui.reader_widget import ReaderWidget
from src.scene.reader_scene import ReaderScene

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

class TestWidgetResize(unittest.TestCase):
    def test_delayed_resize_triggers_recalculation(self):
        # We use a real ReaderScene but mock its methods to verify resize propagates
        scene = ReaderScene()
        scene.recalculate_layout = MagicMock()
        scene._render_study_overlays = MagicMock()
        scene.last_width = 100
        
        # ReaderWidget will use QTimer, but we can call apply_delayed_resize manually
        widget = ReaderWidget(scene=scene)
        
        # Simulate a resize manually changing the widget size
        widget.resize(800, 600)
        
        # Manually force the delayed resize application to bypass timer wait
        widget.apply_delayed_resize()
        
        # setSceneRect is called inside apply_delayed_resize which checks width difference
        # Since width changed from 100 to 800, it should trigger recalculate_layout and _render_study_overlays
        scene.recalculate_layout.assert_called_once()
        scene._render_study_overlays.assert_called_once()
        
        # Ensure the bounds updated correctly
        self.assertEqual(scene.last_width, widget.view.viewport().rect().width())

if __name__ == '__main__':
    unittest.main()
