import os
import pytest
from PySide6.QtWidgets import QApplication
from src.utils.exporter import Exporter

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

def test_pdf_export(qapp, tmp_path):
    output_pdf = tmp_path / "test.pdf"
    content = "<h1>Test Heading</h1><p>This is a test paragraph.</p>"
    Exporter.export_to_pdf(content, str(output_pdf))
    assert output_pdf.exists()
    assert output_pdf.stat().st_size > 0

def test_docx_export(qapp, tmp_path):
    output_docx = tmp_path / "test.docx"
    content_data = [
        {'type': 'heading', 'text': 'Test Heading', 'level': 1},
        {'type': 'paragraph', 'text': 'This is a test paragraph.'}
    ]
    Exporter.export_to_docx(content_data, str(output_docx))
    assert output_docx.exists()
    assert output_docx.stat().st_size > 0

def test_pdf_export_options(qapp, tmp_path):
    output_pdf = tmp_path / "test_options.pdf"
    content = "<h1>Test Options</h1><p>Testing font size and orientation.</p>"
    options = {
        "font_size": 20,
        "orientation": "Landscape",
        "line_spacing": 2.0
    }
    Exporter.export_to_pdf(content, str(output_pdf), options)
    assert output_pdf.exists()
