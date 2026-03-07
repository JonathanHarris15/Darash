# Multi-Translation Interlinear System Plan

## 1. Executive Summary
**Objective**: Implement a multi-translation interlinear system in the reading view. Users can select a primary version, toggle additional interlinear rows, and reorder them via a drag-and-drop dropdown menu. Each split reading view maintains its own independent translation settings.

## 2. Data Strategy
We will aggregate data from three main sources:
*   **Standard Translations (XML)**: Located in `data/BibleTranslations/bible-master/bible-master/bible/translations/*.xml`. These provide the base text for versions like NIV, ESV, KJV, etc.
*   **Strong's Data (JSON)**: Located in `data/mdbible-main/mdbible-main/json/ESV.json`. Used for linking English words to Strong's numbers.
*   **Interlinear/Morphological Data (JSON)**: Located in `data/BibleTranslations/interlinear_bibledata-master/.../src/[book]/[chapter].json`. This provides the Hebrew/Greek text, glosses, and Strong's alignments.

## 3. Architecture & Component Updates

### `src/core/verse_loader.py`
*   **New Method**: `load_chapter_multi(book, chapter, translations: list[str])`.
*   **Logic**: 
    1. Load the primary translation text.
    2. Iteratively load secondary translations (XML or JSON).
    3. Aggregate into a structured dictionary: `dict[verse_num, dict[translation_id, verse_data]]`.
    4. Ensure alignment across versions (handling versification differences if necessary, though mostly standard for now).

### `src/scene/scene_settings_manager.py`
*   **New Properties**: 
    - `primary_translation: str` (e.g., "ESV")
    - `enabled_interlinear: list[str]` (Ordered list of active versions, e.g., ["NIV", "Hebrew"])
*   **Sync Logic**: Ensure changes trigger a `LayoutEngine` recalculation.

### `src/managers/study_manager.py`
*   **Persistence**: Update `study.json` schema to store translation preferences per "view" or globally as a default.

### `src/ui/components/translation_selector.py` (New File)
*   **UI**: A dropdown panel triggered by a button in the `ReaderWidget` HUD (top-left).
*   **Interaction**: 
    - `QListWidget` with `InternalMove` drag-drop.
    - Checkboxes to toggle visibility of secondary translations.
    - Dragging a version to the top slot sets it as `primary_translation`.

### `src/scene/layout_engine.py`
*   **Refactor**: `recalculate_layout` must now iterate through verses and then through the ordered list of `active_translations` for each verse.
*   **Stacking**: Instead of one `QTextDocument` block per verse, render a "stack" of blocks:
    ```
    [v1 ESV]
    [v1 NIV]
    [v1 Hebrew]
    [v2 ESV]
    ...
    ```
*   **Styling**: Apply distinct styles (color/font/size) to interlinear rows to distinguish them from the primary text.

## 4. Implementation Phases

1.  **Phase 1: Multi-Format Loader**: Update `VerseLoader` to handle XML and the specific Interlinear JSON schema.
2.  **Phase 2: State & Persistence**: Implement settings in `SceneSettingsManager` and `StudyManager`.
3.  **Phase 3: Interleaved Layout**: Modify `LayoutEngine` to support the "verse stack" rendering model.
4.  **Phase 4: UI Selector**: Build the drag-and-drop `TranslationSelector` widget and integrate it into `ReaderWidget`.
5.  **Phase 5: Refinement**: Visual styling, hover effects for interlinear alignments, and performance optimization for large chapters.
