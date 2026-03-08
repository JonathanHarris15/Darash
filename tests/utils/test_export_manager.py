import pytest
from src.ui.main_window import MainWindow
from src.utils.export_manager import ExportManager
from src.ui.components.export_dialog import ExportDialog

def test_trigger_export_dialog_does_not_crash(qtbot, monkeypatch):
    """Ensure trigger_export_dialog does not crash with AttributeError on activeWindow()."""
    main_window = MainWindow()
    qtbot.addWidget(main_window)
    
    export_manager = ExportManager(main_window)
    
    # Mock ExportDialog.exec to not block the test
    monkeypatch.setattr(ExportDialog, "exec", lambda self: None)
    
    # Triggers the specific code path that crashed and accesses center_workspace.activeWindow()
    export_manager.trigger_export_dialog("Notes")
    
    # Also test the fallback path when export_type is None
    export_manager.trigger_export_dialog()
