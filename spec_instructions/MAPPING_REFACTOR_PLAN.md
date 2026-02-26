# Mapping System Refactor Plan

## 1. Executive Summary

**Objective**: Transition the `LayoutEngine` and mapping system from a globally pre-computed, static layout (processing 31,000+ verses up front) to a hyper-fast, localized, "windowed" coordinate system.

**Why**: To lay the foundation for real-time text resizing, split-screen reading, and complex interlinear/multi-translation rendering without imposing massive lag during layout recalculations. The reading scene must be robust, lightweight, and capable of rendering only what is needed on-demand.

## 2. Architecture Paradigm Shift

Currently, the `LayoutEngine` dumps the entire Bible into a single `QTextDocument` (within `main_text_item`) and stores global character positions in `verse_pos_map` and `pos_verse_map`. This dictates the `QGraphicsScene`'s total height.

**The New Paradigm (Virtual/Windowed Layout)**:
*   **Chunk-Based Loading**: The `QTextDocument` will only contain a "window" or "chunk" of verses (e.g., the current chapter, plus one chapter above and below).
*   **Virtual Coordinates**: The `QGraphicsScene` will no longer represent the literal pixel height of the entire Bible. Instead, scrolling will be decoupled from the physical `sceneRect`. We will use a virtual coordinate system where the scrollbar maps to a linear progression through the Bible's verses, not absolute pixels.
*   **Dynamic Mapping Cache**: `verse_pos_map` and `pos_verse_map` will become localized caches. They will only map references to positions *currently loaded in the chunk*.
*   **Jump vs. Scroll Thresholds**:
    *   *Normal Scroll*: Dynamically append/prepend verses to the `QTextDocument` and adjust the viewport scroll to maintain continuity.
    *   *Fast Scroll/Jump*: Clear the `QTextDocument`, calculate the target reference based on scroll percentage or explicit jump, and render a fresh chunk around that target.

## 3. Core Components to Modify

1.  **`src/scene/layout_engine.py`**:
    *   Remove the loop that iterates over *all* `flat_verses`.
    *   Implement `load_chunk(start_ref, end_ref)` or `load_around(center_ref)`.
    *   Manage prepending/appending text blocks to the document dynamically.
2.  **`src/scene/reader_scene.py`**:
    *   Decouple physical scroll `Y` from the virtual Bible progress.
    *   Handle scroll events to trigger dynamic chunk loading when approaching the edges of the loaded document.
    *   Update the `jump_to` logic to load a new chunk instead of scrolling down a massive physical scene.
3.  **`src/scene/renderer.py` & `src/scene/scene_overlay_manager.py`**:
    *   Ensure they correctly interface with the localized `verse_pos_map`. If a mark/symbol is outside the loaded chunk, it should naturally be ignored (saving processing time).
4.  **`src/utils/reader_utils.py`** (if applicable) and **Mapping API**:
    *   Replace raw dicts with a `MappingManager` or facade to abstract away whether a verse is currently mapped in pixels or just exists abstractly in the database.

## 4. Step-by-Step Implementation Plan

### Phase 1: Virtual State & Scroll Decoupling
*   **Task**: Introduce a "Virtual Position" concept (e.g., 0.0 to 1.0, or absolute verse index 0 to 31102).
*   **Action**: Modify `ReaderScene.wheelEvent` and `scroll_timer` to track virtual progress rather than absolute pixel `scroll_y`.
*   **Action**: Update the external `jump_scrollbar.py` (if it drives the scene) to communicate in verse indices rather than pixels.

### Phase 2: The Chunk-Based Layout Engine
*   **Task**: Refactor `recalculate_layout` to take a target reference or verse index.
*   **Action**: Instead of loading `scene.loader.flat_verses`, load a slice (e.g., `target_index - 50` to `target_index + 100`).
*   **Action**: Build the local `verse_pos_map` and `pos_verse_map` for *only* these loaded verses.

### Phase 3: Dynamic Scrolling (Prepend/Append)
*   **Task**: Implement the illusion of infinite scrolling.
*   **Action**: When the pixel scroll approaches the top/bottom of the loaded `QTextDocument`, trigger an append/prepend layout action.
*   **Critical Math**: When prepending text, the absolute pixel positions of all existing text will shift down. The scene's `scroll_y` must be instantly offset by the exact pixel height of the prepended text to prevent visual stuttering.

### Phase 4: Refactoring Overlays & Queries
*   **Task**: Adapt all overlay layers (Marks, Symbols, Outlines, Strongs).
*   **Action**: Update `OverlayRenderer` and `SceneOverlayManager` to only iterate over `study_manager` data that falls within the `[chunk_start_ref, chunk_end_ref]` bounds.
*   **Action**: Fix outline divider dragging. Since outlines span multiple chapters, a divider might exist even if the start/end bounds are off-screen.

### Phase 5: Search & Global Interactions
*   **Task**: Fix search.
*   **Action**: `QTextDocument.find()` will only search the local chunk. We must implement a global search using `VerseLoader` (which is fast in memory), and only highlight the results that fall within the actively rendered chunk.

## 5. Forward-Thinking Considerations

*   **Multi-Translation Ready**: By rendering small chunks, adding a second text column (interlinear or parallel) simply means the chunk loader fetches and layouts two strings per verse block instead of one. The performance hit will be negligible compared to trying to double the size of a 31,000-verse document.
*   **Split-Pane Ready**: Because the layout is chunk-based, multiple `ReaderScene` instances can easily exist in memory simultaneously, each managing its own small `QTextDocument` and local coordinate cache.
*   **Memory Efficiency**: The `pixmap_cache` and `QGraphicsItem` instances will be aggressively garbage collected as verses scroll out of the loaded chunk.