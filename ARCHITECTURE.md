# Jehu-Reader Architecture
<!-- COMPRESSED CONTEXT — keep this file exhaustively current. Every new file, class, signal, or feature boundary must be recorded here. An agent reading only this file must know exactly which file(s) to open. -->

---

## Core Principles

1. **High Modularity:** Files must be short, focused, and represent a single logical entity.
   - **Soft Limit:** 300 lines. **Hard Limit:** 500 lines. Exceed this → split immediately.
2. **Domain-Driven Structure:** Code is organized into domain folders (`core`, `managers`, `scene`, `ui`, `utils`).
3. **Explicit Data Flow:** State flows deterministically. UI components use signals/methods, never direct engine state mutation.
4. **ReaderScene is a Facade:** Heavy logic belongs in specialized scene managers, not in `reader_scene.py`.
13. **Exporting:** Only Notes and Outlines are exportable. Reading View content extraction is unsupported to maintain UI simplicity.

---

## Domain Map

| Domain | Folder | Purpose |
|---|---|---|
| Foundation | `src/core/` | Constants, data parsing, app entry point |
| Data & Logic | `src/managers/` | State orchestration, persistence, domain algorithms |
| Graphics Engine | `src/scene/` | Virtual layout, rendering, overlays, input |
| Visual Shell | `src/ui/` | Top-level window, docks, sidebar widgets |
| Helpers | `src/utils/` | Pure utility functions with no Qt state |

---

## Full File Registry

### `src/` (Entry Point)

| File | Key Class / Contents | Responsibility |
|---|---|---|
| `app.py` | `main()` | Application entry point. Instantiates `QApplication` and `MainWindow` |

---

### `src/core/`

| File | Key Class / Contents | Responsibility |
|---|---|---|
| `constants.py` | — | Bible book list, section metadata, application version, and core layout parameters (non-styling) |
| `theme.py` | `Theme` | **Single source of truth for design tokens.** Centralizes colors, typography, and spacing; generates global application stylesheet |
| `verse_loader.py` | `VerseLoader` | Parses Bible JSON/XML. Supports multi-translation chapter loading with caching. |
| `search_engine.py` | `SearchEngine`, `SearchParser` | Logical-operator search parsing (`AND`, `OR`, `NOT`), scoped searches (verse/chapter/book), returns ranked result lists |

---

### `src/managers/`

| File | Key Class / Contents | Responsibility |
|---|---|---|
| `study_manager.py` | `StudyManager` | **Primary data orchestrator.** Saves/loads study JSON, undo/redo stack, manages marks, notes, symbols, indentation state |
| `outline_manager.py` | `OutlineManager` | Tree-based book outline CRUD, splitting verses into outline sections, merging, scrubbing metadata |
| `outline_tree_ops.py` | `OutlineTreeOps` | Static helpers for tree hierarchy manipulation, searching, and structural modifications |
| `outline_ref_utils.py` | `OutlineRefUtils` | Utilities for verse reference calculations, delta shifting, and bounds checking |
| `strongs_manager.py` | `StrongsManager` | Strong's number dictionary lookups, cross-reference indexing |
| `symbol_manager.py` | `SymbolManager` | Custom icon library registration, symbol-to-verse bindings |
| `release_note_manager.py` | `ReleaseNoteManager` | Tracks view counts for current version, manages seen state, loads markdown notes |
| `spellcheck_manager.py` | `SpellcheckManager` | Manages spellcheck engine, suggestions, and custom ignored-words dictionary |

**`StudyManager` key signals:** `marks_changed`, `notes_changed`, `symbols_changed`, `state_changed`

---

### `src/scene/`

| File | Key Class / Contents | Responsibility |
|---|---|---|
| `reader_scene.py` | `ReaderScene` | **Facade coordinator only.** Owns all scene managers, routes events, exposes top-level API to `ReaderWidget`. Delegates scroll/chunk logic to `SceneStateManager` and search to `SceneSearchManager`. |
| `scene_state_manager.py` | `SceneStateManager` | Manages virtual scroll position, physical scroll synchronization, and visible chunk boundaries. |
| `layout_engine.py` | `LayoutEngine` | **Heart of the reader.** Computes `QTextDocument` word-wrap, virtual↔physical mapping, and multi-translation verse stacking. Provides geometric helpers for hit-testing and reference finding. |
| `renderer.py` | `OverlayRenderer` | **Rendering facade.** Orchestrates specialized renderers for verse numbers, interlinear dividers, and visible chunk highlights. |
| `outline_renderer.py` | `OutlineRenderer` | Paints hierarchical outline bands, draggable boundaries, and section summaries on the scene. |
| `study_renderer.py` | `StudyRenderer` | Paints Strong's overlays, search highlights, symbols, and verse flash animations. |
| `scene_input_handler.py` | `SceneInputHandler` | Centralised mouse & keyboard event dispatch. Delegates to specialized handlers. |
| `scene_study_input_handler.py` | `SceneStudyInputHandler` | Handles specialized study interactions: arrows, strongs, and study-item deletions. |
| `scene_interaction_manager.py` | `SceneInteractionManager` | Click logic: word selection, right-click context menu, mark application, symbol placement, arrow initiation |
| `scene_indentation_manager.py` | `SceneIndentationManager` | Live drag logic for adjusting verse/sentence indentation handles |
| `scene_overlay_manager.py` | `SceneOverlayManager` | Draws dynamic `QGraphicsItem` overlays: marks, symbols, arrows (including ghost arrows), hover highlights |
| `scene_outline_manager.py` | `SceneOutlineManager` | Interactive outline creation (`create_outline`), splitting, and visual feedback within the scene |
| `scene_search_manager.py` | `SceneSearchManager` | Applies/clears search highlight items, manages navigation state within the visible chunk |
| `scene_settings_manager.py` | `SceneSettingsManager` | Reads/writes appearance settings (fonts, spacing, colors), syncs font changes across the scene |
| `components/reader_items.py` | — | Re-exports all graphics items for the reader scene |
| `components/text_items.py` | `NoFocusTextItem`, `TranslationIndicatorItem` | Text-based graphics items with custom painting |
| `components/note_icon.py` | `NoteIcon` | Interactive icon for verse-linked notes |
| `components/logical_mark.py` | `LogicalMarkItem` | Visual indicators for logical operations/relations |
| `components/arrow_items.py` | `ArrowItem`, `SnakeArrowItem`, `GhostArrowIconItem` | All arrow-based visual connections |
| `components/verse_items.py` | `VerseNumberItem`, `SentenceHandleItem` | Interactive verse numbers and sentence drag handles |
| `components/outline_divider.py` | `OutlineDividerItem` | Draggable boundaries for outline sections |

---

### `src/ui/`

| File | Key Class / Contents | Responsibility |
|---|---|---|
| `main_window.py` | `MainWindow` | Top-level `QMainWindow`. Assembles all docks/panels, handles menu bar, layout presets, dock visibility |
| `main_window_layout.py` | `MainWindowLayoutMixin` | Mixin for `MainWindow` handling layout state saving, restoring, and presets |
| `main_window_panels.py` | `MainWindowPanelsMixin` | Mixin for `MainWindow` handling high-level panel creation and orchestration. Delegates dock operations and panel tracking to `MainWindowDockManager`. |
| `main_window_dock_manager.py` | `MainWindowDockManager` | Handles low-level dock widget addition, tab management, dock cleanups, and dock event routing. |
| `reader_widget.py` | `ReaderWidget` | Container for `QGraphicsView` + `ReaderScene`. Houses HUD overlays (search bar, navigation label, jump scrollbar) |
| `export_manager.py` | `ExportManager` | Orchestrates content extraction (Notes/Outlines) and export dialog flow |
| `components/activity_bar.py` | `ActivityBar` | Left-edge icon bar that toggles panel visibility (similar to VS Code sidebar icons) |
| `components/appearance_panel.py` | `AppearancePanel` | Dock widget for font, spacing, color, and display settings |
| `components/bookmark_ui.py` | `BookmarkPanel`, `BookmarkItem` | Displays, creates, and navigates bookmarks; integrates with `StudyManager` |
| `components/center_split_manager.py` | `CenterSplitManager` | Manages the central `QSplitter` containing multiple `ReaderWidget` instances; handles add/remove/reorder |
| `components/clickable_label.py` | `ClickableLabel` | `QLabel` subclass that emits `clicked` signal |
| `components/jump_scrollbar.py` | `JumpScrollbar` | Custom scrollbar that shows search result positions and chapter tick marks |
| `components/mark_popup.py` | `MarkPopup` | Floating popup for selecting mark colors and styles |
| `components/navigation.py` | `NavigationBar` | Book/chapter/verse navigation controls (dropdowns + prev/next buttons) |
| `components/note_editor.py` | `NoteEditor` | Rich-text note editor container, handles saving and window management |
| `components/rich_text_edit.py` | `RichTextEdit` | Extended `QTextEdit` with list support, markdown conversion, and link handling |
| `components/formatting_toolbar.py` | `FormattingToolBar` | Markdown-style action buttons for `RichTextEdit` |
| `components/outline_dialog.py` | `OutlineDialog` | Modal dialog for creating/naming a new outline |
| `components/outline_panel.py` | `OutlinePanel` | Central-area panel displaying and editing a single book outline tree |
| `components/outline_cell.py` | `OutlineCell`, `DraggableLabel` | Individual row components for the cell-based outline editor |
| `components/placeholder_panel.py` | `PlaceholderPanel` | Empty dock used as a layout anchor when no panel is active |
| `components/pseudo_tab_title_bar.py` | `PseudoTabTitleBar` | Custom title bar for docks that mimics a tabbed interface |
| `components/reading_view_link_manager.py` | `ReadingViewLinkManager` | Manages scroll synchronization between linked `ReaderWidget` instances |
| `components/reading_view_panel.py` | `ReadingViewPanel` | Thin wrapper panel that houses a `ReaderWidget` inside the central splitter |
| `components/search_bar.py` | `SearchBar` | Floating HUD search input, operator buttons, scope toggles |
| `components/split_link_button.py` | `SplitLinkButton` | Toggle button shown between split views to enable/disable scroll linking |
| `components/split_overlay.py` | `SplitOverlay` | Transparent drag target overlay shown when dragging a panel to split the view |
| `components/strongs_ui.py` | `StrongsPanel` | Dock widget displaying Strong's dictionary entries and cross-references |
| `components/study_panel.py` | `StudyPanel` | **Primary sidebar.** Layout container for the study overview tree |
| `components/study_tree.py` | `StudyTreeWidget` | Hierarchical tree of study data. Delegates population to `StudyTreePopulator`. |
| `components/study_tree_populator.py` | `StudyTreePopulator` | Logic for building and refreshing the study tree hierarchy from `StudyManager` data. |
| `components/suggested_symbols_dialog.py` | `SuggestedSymbolsDialog` | Dialog that shows AI/rule-based suggested symbols for a selection |
| `components/symbol_dialog.py` | `SymbolDialog` | Full symbol library browser and picker dialog |
| `components/translation_selector.py` | `TranslationSelector` | Dropdown for toggling and reordering translations via drag-and-drop |
| `components/release_note_dialog.py` | `ReleaseNoteDialog` | Styled markdown viewer for version updates |
| `components/styling_playground.py` | `StylingPlaygroundPanel` | Developer-only styling tool; showcases all theme tokens and component styles for rapid iteration via Lab runner |
| `components/spellcheck_highlighter.py` | `SpellcheckHighlighter` | `QSyntaxHighlighter` that underlines misspelled words for `RichTextEdit` |
| `components/spellcheck_title_edit.py` | `SpellcheckTitleEdit` | Single-line text input with spellcheck support for titles |
| `components/export_dialog.py` | `ExportDialog` | Modal dialog for export options (font, spacing, orientation, format) with a live PDF/DOCX preview panel |

---

### `src/utils/`

| File | Key Class / Contents | Responsibility |
|---|---|---|
| `exporter.py` | `Exporter` | Static helper for PDF (QPrinter) and DOCX (python-docx) generation |
| `reader_utils.py` | — | Geometric helpers: text bounding-rect calculation, word index mapping, hit-testing utilities |
| `snake_path_finder.py` | `SnakePathFinder` | Algorithm for computing snaking arrow paths that navigate around text blocks |
| `menu_utils.py` | — | Helpers for building and styling `QMenu` instances consistently |
| `path_utils.py` | — | Centralized cross-platform path resolution for resources and user data |
| `update_manager.py` | `UpdateManager` | Handles version checking via GitHub API, downloads updates, and performs self-replacement on Windows |

---

### `docs/`

| File | Key Class / Contents | Responsibility |
|---|---|---|
| `features_guide.md` | — | Comprehensive guide for end-users explaining all project features and usage. |

---

## Test Registry (`tests/`)

Mirrors `src/` structure. Add new test files here as features are built.

| Test File | Covers |
|---|---|
| `tests/unit/core/test_verse_loader.py` | `VerseLoader` parsing, flat index, lookups |
| `tests/unit/core/test_search_engine.py` | `SearchEngine` query parsing, logical ops, scoped search |
| `tests/unit/core/test_multi_translation_loader.py` | `VerseLoader` multi-format and interlinear loading |
| `tests/unit/managers/test_study_manager.py` | Mark/note save-load, undo/redo |
| `tests/unit/managers/test_strongs_manager.py` | Strong's number indexing and top-word extraction |
| `tests/unit/managers/test_outline_manager_scrubbing.py` | Outline split, merge, scrub operations |
| `tests/unit/scene/test_layout_engine.py` | `LayoutEngine` geometry calculation, hit-testing, ref-finding |
| `tests/integration/scene/test_scene_interactions.py` | `SceneInteractionManager` click/select logic |
| `tests/integration/scene/test_scene_overlay.py` | `SceneOverlayManager` arrow/mark item creation |
| `tests/unit/scene/test_mac_delete_key.py` | Cross-platform Delete/Backspace key handling |
| `tests/e2e/ui/test_layout_and_movement.py` | Dock layout, panel movement |
| `tests/e2e/ui/test_main_window_layout.py` | Layout preset percentages |
| `tests/e2e/ui/test_main_window_placeholder.py` | Placeholder dock positioning |
| `tests/e2e/ui/test_restore_layout_fallback.py` | Layout restore / fallback logic |
| `tests/component/ui/test_widget_resize.py` | Widget resize behaviour |
| `tests/component/ui/components/test_note_editor.py` | `NoteEditor` link handling, indentation, list cycling |
| `tests/unit/utils/test_reader_utils.py` | Bounding rect calculations, coordinate mapping |
| `tests/unit/utils/test_snake_path_finder.py` | `SnakePathFinder` path algorithm validation |
| `tests/unit/utils/test_exporter.py` | PDF and DOCX generation with various options |
| `tests/component/ui/test_export_manager.py` | `ExportManager` dialog triggering and content extraction logic |
| `tests/unit/utils/test_update_manager.py` | `UpdateManager` version comparison and parsing logic |
| `tests/unit/managers/test_release_note_manager.py` | `ReleaseNoteManager` | View tracking, version detection, file discovery |
| `tests/unit/managers/test_spellcheck_manager.py` | `SpellcheckManager` | Basic spellcheck, suggestions, and custom dictionary persistence |
| `tests/integration/scene/test_scene_outline_manager.py` | `SceneOutlineManager` | Creation delegation and UI refresh signals |
| `tests/component/scene/test_scene_regression.py` | `ReaderScene` | **Foolproof event delegation protection** (wheel/key events) |
| `tests/integration/test_reader_pipeline.py` | `VerseLoader` -> `LayoutEngine` | **End-to-End Pipeline Verification** (Fixes packing regressions) |
| `tests/component/test_scene_input_handler.py` | `SceneInputHandler` | Key/wheel delegation and accumulator logic |
| `tests/component/test_study_tree_populator.py` | `StudyTreePopulator` | Tree hierarchy population and section validation |
| `tests/e2e/test_app_startup.py` | `MainWindow` | Full app import and window initialization smoke test |
| `tests/integration/scene/test_ghost_arrows.py` | `SceneOverlayManager`, `SceneInputHandler` | Ghost arrow rendering, hover coordination, and deletion logic |
| `tests/unit/scene/test_layout_engine_boundary_fixes.py` | `LayoutEngine` | y-top/y-bottom boundary calculations with headings and interlinear blocks |
| `tests/unit/utils/test_qt_images.py` | — | Manual exploratory script for Qt image rendering (not collected by pytest) |

**Final Verification Results (v0.1.5):**
- **Code Coverage:** 52%+ (Enforced by `check_tests.ps1`)
- **Layers:** Unit, Component, Integration, End-to-End (E2E) confirmed stable.

---

## Packaging & Distribution

| Folder / File | Type | Responsibility |
|---|---|---|
| `jehu_reader.spec` | PyInstaller | Cross-platform build config (Windows EXE & Mac APP) |
| `installer/windows_setup.iss` | Inno Setup | Windows professional installer (Setup.exe) generation |
| `.github/workflows/release.yml` | GitHub Action | Multi-OS build matrix (Windows/Mac), installer creation, and GitHub Release automation |
| `gh-release-tag/` | Gemini Skill | Custom command to automate version bumping, tagging, and pushing to GitHub |
| `scripts/lab/` | `HotReloadHarness` | Standalone runners with integrated UI REPL and Hot-Reload support |
| `scripts/visual_regression.py` | — | Automated UI snapshot capture for all Lab runners |

---

## Virtual Coordinate System

- `virtual_scroll_y ∈ [0.0, len(flat_verses)]` — stable identifier for scroll position independent of zoom/font.
- `LayoutEngine` computes a physical "chunk" of geometry around the current virtual position.
- `verse_y_map`: `{ref → (top_px, bottom_px)}` — physical boundary of every verse/sentence in the current chunk.
- Use `LayoutEngine.virtual_to_physical()` / `physical_to_virtual()` for all coordinate conversions.

## Sentence-Breaking & Sub-References

- When "Break at Sentences" is on, verses split into multiple `QTextDocument` blocks.
- Data stored with `|sIndex` suffix: `"Genesis 1:1|0"`, `"Genesis 1:1|1"`.
- Each sub-ref has an independent indent stored in `StudyManager`.

---

## Feature → File Lookup (Quick Reference)

| Feature / Symptom | Primary File(s) |
|---|---|
| App won't start / entry point | `src/app.py` |
| Bible data missing / wrong | `core/verse_loader.py` |
| Search logic / operators | `core/search_engine.py` |
| Mark/note persistence or undo | `managers/study_manager.py` |
| Outline tree operations | `managers/outline_manager.py` |
| Strong's data | `managers/strongs_manager.py` |
| Symbol library | `managers/symbol_manager.py` |
| Word layout / line breaks | `scene/layout_engine.py` |
| Interlinear / Translations | `ui/components/translation_selector.py`, `core/verse_loader.py` |
| Verse numbers / interlinear dividers | `scene/renderer.py` |
| Outline visual bands in scene | `scene/outline_renderer.py` |
| Strong's / search highlights / symbols | `scene/study_renderer.py` |
| Mouse clicks / keyboard shortcuts | `scene/scene_input_handler.py` |
| Right-click menu / word selection | `scene/scene_interaction_manager.py` |
| Indent drag handles | `scene/scene_indentation_manager.py` |
| Arrows / marks / symbols on scene | `scene/scene_overlay_manager.py` |
| Interactive outline creation | `scene/scene_outline_manager.py` |
| Search highlight items | `scene/scene_search_manager.py` |
| Font / color / spacing settings | `ui/theme.py`, `scene/scene_settings_manager.py` |
| `QGraphicsItem` definitions | `scene/components/reader_items.py` |
| Auto-Update / Versioning | `utils/update_manager.py`, `core/constants.py` (Current: v0.1.4) |
| **Release Notes** | `managers/release_note_manager.py`, `ui/components/release_note_dialog.py` |
| **Spellcheck** | `managers/spellcheck_manager.py`, `ui/components/spellcheck_highlighter.py` |
| **Styling / Theme Iteration** | `ui/components/styling_playground.py`, `ui/theme.py` |
| Release Tagging / Build | `gh-release-tag/SKILL.md` (Gemini Skill) |
| Top-level window / docks / menu | `ui/main_window.py` |
| GraphicsView container / HUD | `ui/reader_widget.py` |
| Multiple reading views / splits | `ui/components/center_split_manager.py` |
| Scroll sync between views | `ui/components/reading_view_link_manager.py` |
| Navigation bar dropdowns | ui/components/navigation.py |
| Export (Notes/Outlines) | `ui/export_manager.py`, `ui/components/export_dialog.py` |
| Note editor (rich text) | ui/components/note_editor.py |
185: | User Guide / Features | docs/features_guide.md |
| **Create Lab / Styling** | **(Workflow)** `/create-lab` |

| Outline tree panel (central) | `ui/components/outline_panel.py` |
| Study overview sidebar | `ui/components/study_panel.py` |
| Strong's panel | `ui/components/strongs_ui.py` |
| Appearance settings panel | `ui/components/appearance_panel.py` |
| Bookmarks panel | `ui/components/bookmark_ui.py` |
| Symbol picker | `ui/components/symbol_dialog.py` |
| Mark color picker | `ui/components/mark_popup.py` |
| Custom scrollbar | `ui/components/jump_scrollbar.py` |
| Geometry / hit-test helpers | `utils/reader_utils.py` |
| Arrow path algorithm | `utils/snake_path_finder.py` |
| Menu styling helpers | `utils/menu_utils.py` |

---

## Refactoring Rules

1. **File too large?** If a file exceeds 500 lines, split it. Create the new module in the same domain folder and update this file's registry immediately.
2. **New feature?** Add it to the domain folder that matches its concern. Record the new file in the registry above and the Feature Lookup table.
3. **New `QGraphicsItem`?** Add the class to `scene/components/reader_items.py` unless it has significant standalone logic.
4. **`ReaderScene`** must never grow. Route new logic to a new or existing scene manager.
5. After every structural change, run `pytest` and update this document before closing the session.
