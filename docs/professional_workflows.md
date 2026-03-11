# Professional Development Roadmap

This document outlines high-impact technical workflows to professionalize the Jehu-Reader development process, maintain code quality, and accelerate UI/UX iteration.

## 1. Design Tokens & Theme Engine
**Concept:** Move hardcoded hex colors and font sizes into a central "Single Source of Truth."

- **Current State:** Styles are scattered across `setStyleSheet` calls in individual components.
- **Workflow:** Create `src/ui/theme.py` containing a `Theme` class with constants (e.g., `Theme.ACCENT_PRIMARY = "#64c8ff"`).
- **Benefit:** Enables instant global rebranding and trivial implementation of "Dark/Light Mode."

## 2. Architecture "Guard Dog" (Linting)
**Concept:** Automate the enforcement of architectural boundaries and clean code rules.

- **Status:** [ACTIVE] - Run `/check-health`
- **Workflow:** A script (e.g., `/check-health`) that validates:
    - **File Length:** Flag any file exceeding 500 lines.
    - **Domain Integrity:** Ensure `src/core` never imports from `src/ui`.
    - **Dead Code:** Identify unused imports or signals.
- **Benefit:** Prevents technical debt from accumulating silently.

## 3. Visual Regression Testing (Snapshot Lab)
**Concept:** Ensure styling changes in one component don't accidentally break another.

- **Workflow:** A script that launches all established Labs, captures a screenshot of the window, and saves it to `docs/snapshots/`.
- **Benefit:** Provides a "visual history" of the app and makes it easy to spot accidental layout shifts after a big CSS refactor.

## 4. UI REPL & Inspector
**Concept:** Interact with live UI components via a terminal.

- **Workflow:** Add an interactive Python prompt (using `code.InteractiveConsole`) to the Lab harness.
- **Benefit:** Allows you to test logic and states in real-time (e.g., `component.show_loading()`) without modifying code or restarting.

## 5. Lab System (Implemented)
**Concept:** Isolated component development for rapid styling.

- **Status:** [ACTIVE]
- **Usage:** Run scripts in `scripts/lab/` to style components in isolation with Hot-Reload support.
