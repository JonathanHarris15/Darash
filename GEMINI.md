# Jehu-Reader Project Directions

## Environment & Execution
- **Execution:** The agent MUST NOT attempt to start or run the project. Focus on code modification, analysis, and testing within the source structure.

## Architectural Mandates
- **Single Source of Truth (Architecture):** ALWAYS read `ARCHITECTURE.md` at the start of every session before touching any code. It is a compressed, exhaustive map of every file, class, signal, and feature boundary. Use the **Feature → File Lookup** table to identify target files instantly — do NOT scan the codebase when the answer is in that table.
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

## ARCHITECTURE.md Update Mandate
`ARCHITECTURE.md` is not optional documentation — it is the working memory of the project. It MUST be kept current at all times.

**You MUST update `ARCHITECTURE.md` whenever you:**
- Create a new file (add it to the Full File Registry table and Feature → File Lookup table).
- Delete a file (remove all references).
- Rename or move a file (update all references).
- Add a significant new class, key signal, or public method to an existing file (update that file's table row).
- Change where a feature is implemented (update the Feature → File Lookup table).

**When to update:** Update `ARCHITECTURE.md` **in the same commit/step** as the code change, not at the end of a session. Drift between the doc and the code is a critical failure.

## Testing Mandates
- **Test Coverage:** All features must have corresponding tests. Before adding a new feature or fixing a bug, write tests to define the expected behavior or reproduce the issue.
- **Regression Protection:** Ensure that new features do not break existing ones by running the entire test suite (`pytest`) frequently.
- **Test Maintenance:** When updating existing features or architecture, update the corresponding tests to reflect the new behavior or structure.
- **Directory Structure:** All tests must reside in the `tests/` directory, mirroring the structure of `src/` where applicable (e.g., `tests/core/test_verse_loader.py`). When adding a new test file, add it to the **Test Registry** in `ARCHITECTURE.md`.

## Workflow
1. **Locate:** Read `ARCHITECTURE.md` → use the **Feature → File Lookup** table to identify the exact file(s) to touch. Do not scan the codebase if the table already answers the question.
2. **Test First:** Write or update tests to cover the planned changes.
3. **Modularize:** If a feature is large, create a new file in the appropriate domain rather than bloating existing ones.
4. **Validate:** Run `pytest` to ensure all tests pass and no regressions were introduced.
5. **Update ARCHITECTURE.md:** Record every new file, class, signal, or feature mapping change before closing the task.

## Commands

### `/sync-arch`
Audit the live codebase against `ARCHITECTURE.md` and bring the document up to date.

**Steps:**
1. List all files in `src/` and `tests/` recursively.
2. For each file found, check whether it appears in the **Full File Registry** and **Test Registry** of `ARCHITECTURE.md`.
3. For any file that is present in the codebase but missing from the doc, add a row with the correct class name(s) and a one-line responsibility description.
4. For any file referenced in the doc but absent from the codebase, remove its row.
5. Cross-check the **Feature → File Lookup** table rows against the updated registry and correct any stale mappings.
6. Write the updated `ARCHITECTURE.md`.
