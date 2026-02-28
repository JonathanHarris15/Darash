import pytest
from PySide6.QtCore import Qt
from src.ui.main_window import MainWindow

@pytest.fixture
def main_window(qtbot):
    window = MainWindow()
    window.show()
    qtbot.addWidget(window)
    qtbot.waitExposed(window)
    return window

def test_placeholder_visible_when_no_centers(main_window, qtbot):
    # Close the initial reading view
    assert len(main_window.center_panels) == 1
    
    panel = main_window.center_panels[0]
    panel.close()
    
    # Wait for the event loop to process the deferred deletion
    qtbot.wait(50)
    
    # Wait for the cleanup to happen (it's called in _apply_current_percentages and _clean_center_panels)
    main_window._apply_current_percentages()
    
    valid_centers = [p for p in main_window.center_panels if p.isVisible()]
    assert len(valid_centers) == 0
    assert main_window.placeholder_dock.isVisible()

def test_placeholder_hidden_when_center_exists(main_window, qtbot):
    assert len(main_window.center_panels) == 1
    assert not main_window.placeholder_dock.isVisible()

def test_placeholder_visible_when_center_floats(main_window, qtbot):
    panel = main_window.center_panels[0]
    
    # Simulate floating
    panel.setFloating(True)
    
    # The topLevelChanged signal should be connected to _on_dock_location_changed,
    # which calls _apply_current_percentages after a 10ms timer
    qtbot.wait(50)
    
    assert panel.isFloating()
    assert main_window.placeholder_dock.isVisible()

def test_placeholder_visible_when_dock_hidden(main_window, qtbot):
    panel = main_window.center_panels[0]
    panel.hide()
    
    qtbot.wait(50)
    
    assert not panel.isVisible()
    assert main_window.placeholder_dock.isVisible()
