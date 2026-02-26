# Jehu-Reader Architecture

## Core Principles

1.  **High Modularity:** Files must be short, focused, and represent a single logical entity.
    *   **Limits:** Aim for under 300 lines; never exceed 500 lines. The "God Object" anti-pattern is strictly forbidden.
2.  **Domain-Driven Structure:** Code is organized into folders representing architectural layers or features.
3.  **Explicit Data Flow:** State flows deterministically. UI components use signals/methods rather than direct engine state modification.

## Project Map

### `src/core/` (The Foundation)
*   `constants.py`: Global styling, layout constants, and Bible metadata (Books, Sections).
*   `verse_loader.py`: Bible data parser. Handles JSON ingestion and provides the `flat_verses` index used by the virtual coordinate system.
*   `main.py`: Application entry point.

### `src/managers/` (Data & Logic Controllers)
*   `study_manager.py`: The primary data orchestrator. Handles saving/loading study files (JSON), undo/redo, and manages marks, notes, and symbols.
*   `outline_manager.py`: Specialized logic for tree-based book outlines, splitting, and merging.
*   `strongs_manager.py`: Dictionary and usage indexing for Strong's numbers.
*   `symbol_manager.py`: Handles custom icon libraries and bindings.

### `src/scene/` (The Graphics Engine)
*   `reader_scene.py`: A facade class that coordinates all scene-specific engines.
*   `layout_engine.py`: **The Heart of the Reader.** Calculates `QTextDocument` structures, word-wrap, sentence-breaking, and mapping between document positions and verse references.
*   `renderer.py`: Viewport-aware rendering logic for verse numbers, outlines, and highlights.
*   `scene_indentation_manager.py`: Manages real-time dragging logic for verse and sentence indents.
*   `scene_input_handler.py`: Centralized event handling for mouse and keyboard.
*   `scene_overlay_manager.py`: Draws dynamic graphical items (marks, symbols, arrows).
*   `scene_outline_manager.py`: Interactive logic for creating and splitting outlines.
*   `scene_search_manager.py`: Logic for search highlights and navigation.
*   `scene_settings_manager.py`: Handles persistent appearance settings and font synchronization.
*   `components/reader_items.py`: Individual `QGraphicsItem` definitions (VerseNumberItem, SentenceHandleItem, ArrowItem, etc.).

### `src/ui/` (The Visual Shell)
*   `main_window.py`: Top-level assembly. Coordinates the sidebar and the reader view.
*   `reader_widget.py`: The container for the GraphicsView, housing HUD overlays like the search bar and navigation labels.
*   `components/`: Standard PySide6 widgets for specific tasks (AppearancePanel, NoteEditor, OutlinePanel, etc.).

### `src/utils/` (Helpers)
*   `reader_utils.py`: Geometric and text-layout utilities (calculating text bounding rects, word indexing).
*   `snake_path_finder.py`: Algorithm for drawing snaking arrows that avoid text overlap.

## State Management & Coordinate Systems

### 1. The Virtual Coordinate System
Instead of a global pixel-based coordinate system (which would be unstable due to variable verse lengths and window resizing), Jehu-Reader uses a **Virtual Verse Index**:
*   `virtual_scroll_y` ranges from `0.0` to `len(total_verses)`.
*   The `LayoutEngine` generates a local "chunk" of physical geometry around the current focus.
*   Vertical boundaries for every verse (and sentence) are mapped in `verse_y_map`, enabling physical-to-virtual translation.

### 2. Sentence-Breaking & Sub-References
When "Break at Sentences" is enabled, verses are split into multiple text blocks.
*   **Sub-Ref System**: Data is stored using a `|sIndex` suffix (e.g., `Genesis 1:1|0`, `Genesis 1:1|1`).
*   **Independent Indentation**: Each sub-reference maintains its own indent level in the `StudyManager`.
*   **Hanging Indents**: All lines within a sentence block share the same left margin, while verse numbers and sentence ticks sit in the reserved margin.

## Refactoring Guidelines

1.  **Do not bloat existing files:** If a new feature requires more than 50 lines of code, evaluate whether it belongs in a new module in `src/scene/` or `src/ui/components/`.
2.  **ReaderScene Facade:** `ReaderScene` should strictly be a coordinator. Add heavy logic to specialized managers.
3.  **Validation**: Always ensure `pytest` passes after architectural changes. Use `tests/` structure that mirrors `src/`.
