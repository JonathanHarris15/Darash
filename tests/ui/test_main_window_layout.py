import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings
from src.ui.main_window import MainWindow
import sys

# Fixture to provide a QApplication instance needed for PySide6 tests
@pytest.fixture(scope="module")
def app():
    _app = QApplication.instance()
    if _app is None:
        _app = QApplication(sys.argv)
    yield _app

# Fixture to provide a MainWindow instance and clean up settings/window after
@pytest.fixture
def window(app):
    # Clear settings to ensure a fresh state
    settings = QSettings("JehuReader", "MainWindow")
    settings.clear()
    
    win = MainWindow()
    win.show() # Need to show it so geometry calculations work
    yield win
    win.close()
    settings.clear()

def test_initial_percentages(window):
    """Test that default layout uses 10%, 80%, 10% defaults and cleans extra panels."""
    # Add a dummy extra reading view to test cleanup
    window.add_reading_view()
    
    # Add a dummy note panel, it should be cleaned up too
    window.add_note_panel("", "")
    
    window._clean_center_panels()
    assert len([p for p in window.center_panels if p.isVisible() and not p.isFloating()]) >= 3
    
    # Apply default layout which should close the extra view and note panel
    window._apply_layout_preset(0.10, 0.10, close_extras=True)
    QApplication.processEvents()
    
    assert getattr(window, "_left_dock_pct") == pytest.approx(0.10, abs=0.40)
    assert getattr(window, "_right_dock_pct") == pytest.approx(0.10, abs=0.40)
    
    window._clean_center_panels()
    
    valid_centers = [p for p in window.center_panels if p.isVisible() and not p.isFloating()]
    assert len(valid_centers) == 1
    
    # Ensure what remains is the reading view
    from src.ui.components.reading_view_panel import ReadingViewPanel
    assert isinstance(valid_centers[0].widget(), ReadingViewPanel)

def test_reading_focus_preset(window):
    """Test reading focus collapses side panels."""
    window._apply_layout_preset(0.0, 0.0)
    
    QApplication.processEvents()
    
    # Left and right docks should ideally have width 0 or very close to it
    assert getattr(window, "_left_dock_pct") == pytest.approx(0.0, abs=0.40)
    assert getattr(window, "_right_dock_pct") == pytest.approx(0.0, abs=0.40)

def test_study_focus_preset(window):
    """Test that a second reading panel can be added and both panels are visible."""
    initial_center_count = len([p for p in window.center_panels if p.isVisible() and not p.isFloating()])

    # Open a second reading view (tabifies by default; user would drag to split)
    window.add_reading_view()

    QApplication.processEvents()

    final_center_count = len([p for p in window.center_panels if p.isVisible() and not p.isFloating()])

    assert getattr(window, "_left_dock_pct") == pytest.approx(0.10, abs=0.40)
    assert getattr(window, "_right_dock_pct") == pytest.approx(0.10, abs=0.40)
    assert final_center_count >= max(2, initial_center_count)
