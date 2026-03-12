import pytest
import os
from PySide6.QtCore import QSettings
from src.managers.release_note_manager import ReleaseNoteManager

@pytest.fixture
def temp_settings_dir(tmp_path):
    settings_file = tmp_path / "test_settings.ini"
    return str(settings_file)

@pytest.fixture
def manager(temp_settings_dir, tmp_path):
    # Mock resources dir
    notes_dir = tmp_path / "resources" / "release_notes"
    notes_dir.mkdir(parents=True)
    
    # Create some mock notes
    (notes_dir / "v0.1.1.md").write_text("# v0.1.1", encoding="utf-8")
    (notes_dir / "v0.1.2.md").write_text("# v0.1.2", encoding="utf-8")
    
    # Instantiate manager
    m = ReleaseNoteManager()
    # Override settings and notes_dir for testing
    m.settings = QSettings(temp_settings_dir, QSettings.IniFormat)
    m.notes_dir = str(notes_dir)
    m.version = "0.1.2"
    return m

def test_should_show_release_note_first_run(manager):
    assert manager.should_show_release_note() is True
    manager.increment_view_count()
    assert manager.should_show_release_note() is True

def test_should_stop_showing_after_5_views(manager):
    for _ in range(5):
        assert manager.should_show_release_note() is True
        manager.increment_view_count()
    assert manager.should_show_release_note() is False

def test_reset_on_version_update(manager):
    # Simulate 5 views on old version
    manager.settings.setValue("release_notes/last_seen_version", "0.1.1")
    manager.settings.setValue("release_notes/view_count", 5)
    
    # Current version is 0.1.2, should show again
    assert manager.should_show_release_note() is True
    # Count should be reset to 0 internally when should_show_release_note logic detects version change
    assert int(manager.settings.value("release_notes/view_count")) == 0

def test_get_all_release_notes(manager):
    notes = manager.get_all_release_notes()
    assert notes == ["0.1.2", "0.1.1"]

def test_get_note_content(manager):
    content = manager.get_note_content("0.1.2")
    assert content == "# v0.1.2"
    
    content = manager.get_note_content("9.9.9")
    assert "No release notes available" in content
