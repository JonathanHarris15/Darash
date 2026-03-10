# UI Component Lab Index

This document tracks all modular UI components in Jehu-Reader and the commands to launch them in isolation for rapid styling using the **Lab System**.

## Core Components & Panels

| Component Name | Source File | Class Name | Lab Command |
|---|---|---|---|
| **Bible Directory** | `src/ui/components/navigation.py` | `NavigationDock` | `python scripts/lab/run_navigation.py` |
| **Activity Bar** | `src/ui/components/activity_bar.py` | `ActivityBar` | *Not yet created* |
| **Appearance Panel** | `src/ui/components/appearance_panel.py` | `AppearancePanel` | *Not yet created* |
| **Bookmark Sidebar** | `src/ui/components/bookmark_ui.py` | `BookmarkSidebar` | *Not yet created* |
| **Center Split Manager** | `src/ui/components/center_split_manager.py` | `CenterSplitManager` | *Not yet created* |
| **Export Dialog** | `src/ui/components/export_dialog.py` | `ExportDialog` | *Not yet created* |
| **Jump Scrollbar** | `src/ui/components/jump_scrollbar.py` | `JumpScrollbar` | *Not yet created* |
| **Mark Popup** | `src/ui/components/mark_popup.py` | `MarkPopup` | *Not yet created* |
| **Note Editor** | `src/ui/components/note_editor.py` | `NoteEditor` | *Not yet created* |
| **Outline Dialog** | `src/ui/components/outline_dialog.py` | `OutlineDialog` | *Not yet created* |
| **Outline Panel** | `src/ui/components/outline_panel.py` | `OutlinePanel` | *Not yet created* |
| **Reading View Panel** | `src/ui/components/reading_view_panel.py` | `ReadingViewPanel` | *Not yet created* |
| **Search Bar** | `src/ui/components/search_bar.py` | `SearchBar` | *Not yet created* |
| **Strong's Panel** | `src/ui/components/strongs_ui.py` | `StrongsPanel` | *Not yet created* |
| **Study Panel** | `src/ui/components/study_panel.py` | `StudyPanel` | *Not yet created* |
| **Translation Selector** | `src/ui/components/translation_selector.py` | `TranslationSelector` | *Not yet created* |
| **Symbol Dialog** | `src/ui/components/symbol_dialog.py` | `SymbolDialog` | *Not yet created* |

## Utility / Helper Widgets

| Widget Name | Source File | Class Name | Notes |
|---|---|---|---|
| Clickable Label | `src/ui/components/clickable_label.py` | `ClickableLabel` | Used for links/buttons |
| Pseudo Tab Title Bar | `src/ui/components/pseudo_tab_title_bar.py` | `PseudoTabTitleBar` | Custom dock titles |
| Split Link Button | `src/ui/components/split_link_button.py` | `SplitLinkButton` | The link icon between views |
| Split Overlay | `src/ui/components/split_overlay.py` | `SplitOverlay` | Drag-target visual |

---

### Tips for Styling
1. Use the `/create-lab` command (e.g., `/create-lab for the Search Bar`) to have me generate the runner script for you.
2. The generated labs support **Hot-Reload**. Simply save the component's source file, and the lab window will refresh automatically.
