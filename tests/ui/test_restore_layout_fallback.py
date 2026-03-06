"""
Regression tests for _load_and_restore_layout fallback behaviour.

Ensures the app always opens with a Reading View panel when:
  - There are no saved settings (fresh install)
  - The saved center_panels_state is an empty list
  - The saved center_panels_state contains no recognisable panel types
  - A stale center_workspace_state from a placeholder session is saved
"""
import json
import sys
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings
from src.ui.main_window import MainWindow
from src.ui.components.reading_view_panel import ReadingViewPanel


# ── helpers ──────────────────────────────────────────────────────────────────

def _fresh_window(qtbot):
    """Create a MainWindow with clean settings."""
    settings = QSettings("JehuReader", "MainWindow")
    settings.clear()
    win = MainWindow()
    win.show()
    qtbot.addWidget(win)
    qtbot.waitExposed(win)
    return win


def _has_reading_view(win) -> bool:
    win._clean_center_panels()
    valid = [p for p in win.center_panels if p.isVisible() and not p.isFloating()]
    return any(isinstance(p.widget(), ReadingViewPanel) for p in valid)


# ── tests ─────────────────────────────────────────────────────────────────────

def test_fresh_install_opens_reading_view(qtbot):
    """No saved state at all → Reading View should open, not the placeholder."""
    settings = QSettings("JehuReader", "MainWindow")
    settings.clear()

    win = MainWindow()
    win.show()
    qtbot.addWidget(win)
    qtbot.waitExposed(win)

    assert _has_reading_view(win), "Fresh install must open with a Reading View"
    assert not win.placeholder_dock.isVisible(), "Placeholder must be hidden"


def test_empty_panels_list_opens_reading_view(qtbot):
    """center_panels_state saved as [] → still opens a Reading View."""
    settings = QSettings("JehuReader", "MainWindow")
    settings.clear()
    settings.setValue("center_panels_state", json.dumps([]))

    win = MainWindow()
    win.show()
    qtbot.addWidget(win)
    qtbot.waitExposed(win)

    assert _has_reading_view(win), "Empty panels list must fall back to Reading View"
    assert not win.placeholder_dock.isVisible()


def test_unknown_panel_types_opens_reading_view(qtbot):
    """Saved state with unrecognised panel types → fallback to Reading View."""
    settings = QSettings("JehuReader", "MainWindow")
    settings.clear()
    settings.setValue("center_panels_state", json.dumps([
        {"type": "UnknownWidget", "objectName": "x"}
    ]))

    win = MainWindow()
    win.show()
    qtbot.addWidget(win)
    qtbot.waitExposed(win)

    assert _has_reading_view(win), "Unknown panel types must fall back to Reading View"
    assert not win.placeholder_dock.isVisible()


def test_stale_workspace_state_does_not_hide_fallback(qtbot):
    """
    A saved center_workspace_state (Qt dock byte-state) from a previous
    placeholder-only session must NOT override the fallback Reading View.
    This was the original bug: restoreState stamped a placeholder layout
    over the freshly-added Reading View.
    """
    settings = QSettings("JehuReader", "MainWindow")
    settings.clear()

    # Simulate what was saved when only the placeholder was showing:
    # center_panels_state = [] (no real panels)
    # center_workspace_state = whatever Qt saved (we use a dummy non-empty value;
    #   a real Qt dock state would suppress the new dock, but an unrecognised
    #   byte string is ignored by restoreState, so we test the guard logic itself).
    settings.setValue("center_panels_state", json.dumps([]))
    settings.setValue("center_workspace_state", b"stale_bytes")

    win = MainWindow()
    win.show()
    qtbot.addWidget(win)
    qtbot.waitExposed(win)

    assert _has_reading_view(win), (
        "A stale center_workspace_state must not suppress the fallback Reading View"
    )
    assert not win.placeholder_dock.isVisible()


def test_valid_saved_layout_is_restored(qtbot):
    """When a real Reading View was saved, it should be restored correctly."""
    settings = QSettings("JehuReader", "MainWindow")
    settings.clear()
    settings.setValue("center_panels_state", json.dumps([
        {"type": "ReadingView", "objectName": "ReadingView_restored", "title": "Reading View"}
    ]))

    win = MainWindow()
    win.show()
    qtbot.addWidget(win)
    qtbot.waitExposed(win)

    assert _has_reading_view(win), "A saved Reading View panel must be restored"
    objects = [p.objectName() for p in win.center_panels]
    assert "ReadingView_restored" in objects
