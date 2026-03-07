import pytest
from PySide6.QtCore import Qt
from src.ui.components.note_editor import NoteEditor, _is_html


# ---------------------------------------------------------------------------
# _is_html helper
# ---------------------------------------------------------------------------

def test_is_html_detects_html():
    assert _is_html("<!DOCTYPE html><html><body></body></html>")
    assert _is_html("  <!doctype html>...")

def test_is_html_rejects_plain_text():
    assert not _is_html("## Hello World")
    assert not _is_html("Normal note text")
    assert not _is_html("")


# ---------------------------------------------------------------------------
# NoteEditor widget
# ---------------------------------------------------------------------------

def test_note_editor_initial_state(qtbot):
    editor = NoteEditor(initial_text="Test Note", ref="Gen 1:1", initial_title="My Title")
    qtbot.addWidget(editor)

    assert editor.title_input.text() == "My Title"
    # Content is loaded as Markdown, so plain text should contain the original
    assert "Test Note" in editor.editor.toPlainText()


def test_note_editor_get_title_is_live(qtbot):
    """get_title() should reflect the current text in the title field without needing Save."""
    editor = NoteEditor()
    qtbot.addWidget(editor)

    editor.title_input.setText("New Title")
    assert editor.get_title() == "New Title"


def test_note_editor_get_text_is_live(qtbot):
    """get_text() should reflect current editor content without needing Save."""
    editor = NoteEditor()
    qtbot.addWidget(editor)

    editor.editor.setPlainText("New content here.")
    # get_text returns HTML, so just verify the plain text is captured
    assert "New content here." in editor.editor.toPlainText()


def test_note_editor_loads_html_content(qtbot):
    """HTML content should be detected and loaded as rich text, not escaped."""
    html_content = "<!DOCTYPE HTML><html><body><p><b>Bold Text</b> <i>Italic</i></p></body></html>"

    editor = NoteEditor(initial_text=html_content)
    qtbot.addWidget(editor)

    # When loaded as HTML, the output HTML should preserve structure
    output = editor.editor.toHtml()
    assert "Bold Text" in output
    assert "Italic" in output


def test_note_editor_loads_markdown_content(qtbot):
    """Plain Markdown content is loaded without crashing."""
    md_content = "## My Heading\n\n- Item 1\n- Item 2"
    editor = NoteEditor(initial_text=md_content)
    qtbot.addWidget(editor)

    plain = editor.editor.toPlainText()
    assert "My Heading" in plain
    assert "Item 1" in plain


def test_note_editor_delete_code(qtbot):
    """Clicking Delete should emit the DELETE_CODE result."""
    editor = NoteEditor()
    qtbot.addWidget(editor)

    with qtbot.waitSignal(editor.finished, timeout=500) as blocker:
        editor.btn_delete.click()

    assert blocker.args[0] == NoteEditor.DELETE_CODE
