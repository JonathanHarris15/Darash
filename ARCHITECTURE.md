# Jehu-Reader Architecture

## Core Principles

1.  **High Modularity:** Files must be short, focused, and represent a single logical entity.
    *   **Limits:** Aim for under 300 lines; never exceed 500 lines. The "God Object" anti-pattern is strictly forbidden.
2.  **Domain-Driven Structure:** Code is organized into folders representing architectural layers or features.
3.  **Explicit Data Flow:** State flows deterministically. UI components use signals/methods rather than direct engine state modification.

## Directory Structure

The application is broken into specific domains:

*   `src/core/`: Foundational logic, constants, and the entry point (`main.py`). Classes here do not depend on the UI.
*   `src/managers/`: Data controllers (`StudyManager`, `OutlineManager`, `StrongsManager`, `SymbolManager`). They load, parse, and mutate state before interacting with the UI.
*   `src/scene/`: The highly specialized graphics engine (`QGraphicsScene`).
    *   **Rule:** `ReaderScene` is only a facade. Heavy lifting is delegated to distinct engines:
        *   `layout_engine.py`: Responsible for calculating the `QTextDocument` block structures, pagination, and verse positions.
        *   `scene_input_handler.py`: Solely handles mouse, keyboard, and wheel events.
        *   `scene_overlay_manager.py`: Responsible for drawing dynamic graphical items (marks, symbols, outlines) on top of the text.
*   `src/ui/`: The structural user interface (built around PySide6 standard widgets).
    *   `main_window.py`: The `QMainWindow` assembly point.
    *   `reader_widget.py`: The container holding the GraphicsView and overlay HUDs.
    *   `jump_scrollbar.py`: The specialized track-bar.
    *   `components/`: Specific panels (Study, Outline, Appearance) and Dialogs.
*   `src/utils/`: Pure functions, helpers, and isolated algorithms (`snake_path_finder.py`).

## Refactoring Guidelines (For Future Developers/LLMs)

1.  **Do not bloat existing files:** If a new feature requires more than 50 lines of code, evaluate whether it belongs in a new module.
2.  **Scene Component Extraction:** When adding a new interactive or rendering feature to the `ReaderScene` (e.g., a new "Map View"), create a new `FeatureRenderer` or `FeatureHandler` class rather than adding methods directly to `ReaderScene`.
3.  **Imports:** Ensure relative or absolute imports (`from src.domain...`) remain consistent with the structured folders.

## State Management

The primary source of truth for the active study is the `StudyManager`. UI components read from it and trigger its mutations. The `ReaderScene` listens to changes (via direct calls or signals) and schedules a re-render through its specific overlay/layout sub-managers.
