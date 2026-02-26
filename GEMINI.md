# Jehu-Reader Project Directions

## Environment & Execution
- **Virtual Environment:** This project runs in a dedicated virtual environment located outside the project directory.
- **Execution:** The agent MUST NOT attempt to start or run the project. Focus on code modification, analysis, and testing within the source structure.

## Architectural Mandates
- **Single Source of Truth (Architecture):** ALWAYS refer to `ARCHITECTURE.md` before implementing features. It defines the domain boundaries (core, managers, scene, ui, utils) and provides a **Project Map** of key file responsibilities.
- **Clean Code & Granularity:** Files must be short and focused.
    - **Soft Limit:** 300 lines.
    - **Hard Limit:** 500 lines. If a file exceeds this, it MUST be split into sub-modules.
- **The "ReaderScene" Rule:** `ReaderScene` is a facade. Never add heavy logic directly to it. Delegate rendering to `renderer.py`, layout to `layout_engine.py`, and input to `scene_input_handler.py`.
- **Domain Integrity:** Strictly adhere to the folder structure. 
    - `core/`: Foundation.
    - `managers/`: State and Data.
    - `scene/`: Graphics & Rendering Engine.
    - `ui/`: Standard Widgets & Layouts.
    - `utils/`: Pure helpers.

## Testing Mandates
- **Test Coverage:** All features must have corresponding tests. Before adding a new feature or fixing a bug, write tests to define the expected behavior or reproduce the issue.
- **Regression Protection:** Ensure that new features do not break existing ones by running the entire test suite (`pytest`) frequently.
- **Test Maintenance:** When updating existing features or architecture, update the corresponding tests to reflect the new behavior or structure.
- **Directory Structure:** All tests must reside in the `tests/` directory, mirroring the structure of `src/` where applicable (e.g., `tests/core/test_verse_loader.py`).

## Workflow
1. **Locate:** Use `ARCHITECTURE.md` to identify the target domain for your change.
2. **Test First:** Write or update tests to cover the planned changes.
3. **Modularize:** If a feature is large, create a new file in the appropriate domain rather than bloating existing ones.
4. **Validate:** Run `pytest` to ensure all tests pass and no regressions were introduced.
5. **Document:** If the architectural structure changes, update `ARCHITECTURE.md` immediately to keep future sessions efficient.
