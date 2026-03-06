import pytest
import json
from PySide6.QtCore import Qt, QSettings
from PySide6.QtWidgets import QDockWidget, QSplitter
from src.ui.main_window import MainWindow
from src.ui.components.reading_view_panel import ReadingViewPanel
from src.ui.components.outline_panel import OutlinePanel
from src.ui.components.note_editor import NoteEditor

@pytest.fixture
def main_window(qtbot):
    # Clear settings to start fresh
    QSettings("JehuReader", "MainWindow").clear()
    
    window = MainWindow()
    window.show()
    qtbot.addWidget(window)
    qtbot.waitExposed(window)
    return window

def test_initial_layout(main_window, qtbot):
    # Docks exist
    assert main_window.left_dock.isVisible()
    assert main_window.right_dock.isVisible()
    
    # 1 center panel initially
    assert len(main_window.center_panels) == 1
    
    # Placeholder dock is hidden because a center panel exists
    assert not main_window.placeholder_dock.isVisible()

def test_save_panels(main_window, qtbot):
    # Clear previous center panels
    for p in main_window.center_panels:
        p.close()
    qtbot.wait(100) # Wait for deferred deletion
    main_window.center_panels.clear()
    
    # Add a Reading View and a Note Panel
    main_window.add_reading_view(object_name="ReadingView1")
    main_window.add_note_panel("standalone_1", "Test Note", object_name="Note1")
    
    assert len(main_window.center_panels) == 2
    
    # Simulate closing the application (which calls closeEvent)
    main_window.close()
    
    # Verify settings are saved correctly
    settings = QSettings("JehuReader", "MainWindow")
    panels_json = settings.value("center_panels_state")
    assert panels_json is not None
    panels_state = json.loads(panels_json)
    
    assert len(panels_state) == 2
    objects = [s.get("objectName") for s in panels_state]
    assert "ReadingView1" in objects
    assert "Note1" in objects

def test_restore_panels(qtbot):
    # Set up QSettings manually to simulate saved state
    settings = QSettings("JehuReader", "MainWindow")
    settings.clear()
    state = [
        {"type": "ReadingView", "objectName": "ReadingView1", "title": "Reading View"},
        {"type": "Note", "objectName": "Note1", "title": "Note - Test Note", "note_key": "standalone_1", "ref": "Test Note"}
    ]
    settings.setValue("center_panels_state", json.dumps(state))
    
    new_window = MainWindow()
    new_window.show()
    qtbot.addWidget(new_window)
    qtbot.waitExposed(new_window)
    
    try:
        assert len(new_window.center_panels) == 2
        
        objects = [p.objectName() for p in new_window.center_panels]
        assert "ReadingView1" in objects
        assert "Note1" in objects
        
        # Verify the types of widgets loaded
        widgets = [type(p.widget()) for p in new_window.center_panels]
        assert ReadingViewPanel in widgets
        assert NoteEditor in widgets
        
        # Determine the note editor's injected details
        note_p = next(p.widget() for p in new_window.center_panels if isinstance(p.widget(), NoteEditor))
        assert note_p.note_key == "standalone_1"
        assert note_p.ref == "Test Note"
    finally:
        new_window.close()

def test_drop_on_placeholder_dock(main_window, qtbot):
    # Close all center panels to reveal the placeholder dock
    for p in main_window.center_panels:
        p.close()
    qtbot.wait(100)
    main_window._apply_current_percentages()
    
    assert len([p for p in main_window.center_panels if p.isVisible()]) == 0
    assert main_window.placeholder_dock.isVisible()
    
    # Open a new reading view
    main_window.add_reading_view()
    
    # The new reading view should take the place, and the placeholder must hide
    assert len([p for p in main_window.center_panels if p.isVisible()]) == 1
    assert not main_window.placeholder_dock.isVisible()

def test_split_existing_panels(main_window, qtbot):
    # Start with 1 reading view
    assert len(main_window.center_panels) == 1
    first_panel = main_window.center_panels[0]
    
    # Add another reading view (tabs by default; drag-to-split is a gesture)
    main_window.add_reading_view()
    
    assert len(main_window.center_panels) == 2
    
    # Both panels should be tracked; left/right docks remain visible
    assert main_window.left_dock.isVisible()
    assert main_window.right_dock.isVisible()
    assert first_panel.isVisible()
    assert main_window.center_panels[1].isVisible()

def test_close_tabified_panel(main_window, qtbot):
    # Start with 1 reading view
    assert len(main_window.center_panels) == 1
    # Add another one tabbed (default)
    main_window.add_reading_view()
    
    assert len(main_window.center_panels) == 2
    
    # Close the second panel
    main_window.center_panels[1].close()
    qtbot.wait(100)
    main_window._apply_current_percentages()
    
    # Only 1 panel should remain
    valid_centers = [p for p in main_window.center_panels if p.isVisible() and not p.isFloating()]
    assert len(valid_centers) == 1
    
    # Placeholder should not show
    assert not main_window.placeholder_dock.isVisible()

