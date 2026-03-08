# Export to PDF and DOCX Plan

## Goals
Implement a robust export system for Reading View, Notes, and Outlines, allowing for both PDF and DOCX formats where applicable.

## Libraries
- **PySide6.QtPrintSupport**: Use `QPrinter` and `QPainter` for PDF generation.
- **python-docx**: (To be added) For generating .docx files.

## Components to Create

### 1. `src/utils/pdf_exporter.py`
- `PDFExporter` class:
    - Handles rendering `QTextDocument` to a PDF via `QPrinter`.
    - Methods to convert from:
        - Verse Range (Reading View).
        - Markdown/Rich Text (Notes).
        - Outline Tree (Outlines).
    - Support for "Dark to Light" theme conversion.
    - Support for including Marks/Symbols.

### 2. `src/ui/components/export_dialog.py`
- `ExportDialog(QDialog)`:
    - Left side: `QScrollArea` or similar with a `QLabel` (or `QGraphicsView`) showing a preview of the first page.
    - Right side: `QVBoxLayout` with dynamic options based on what's being exported.
    - Bottom: "Set Download Path" and "Export" buttons.

### 3. `src/ui/components/export_options_widget.py` (optional, can be inside `export_dialog.py`)
- `ReadingViewOptionsWidget`
- `NotesOptionsWidget`
- `OutlineOptionsWidget`

## Integration Points

### 1. `src/ui/main_window.py`
- Add "Export" submenu to "File".
- Bind `Ctrl+P` to `trigger_export_dialog()`.
- Identify the active panel to determine what to export by default.

### 2. `src/ui/components/note_editor.py`
- Add a three-dot menu button at the top right with an "Export" option.

### 3. `src/ui/components/outline_panel.py`
- Add an "Export" button or menu option.

## Testing Strategy
- **Unit Tests (`tests/utils/test_pdf_exporter.py`)**: Verify PDF generation with different content types.
- **UI Tests (`tests/ui/components/test_export_dialog.py`)**: Verify options are correctly displayed and buttons work.

## Development Steps
1.  **Add `python-docx` to `requirements.txt`.**
2.  **Implement `PDFExporter`.**
3.  **Implement `ExportDialog` UI.**
4.  **Connect `PDFExporter` to `ExportDialog`.**
5.  **Integrate with `MainWindow` and `NoteEditor`.**
6.  **Update `ARCHITECTURE.md`.**
