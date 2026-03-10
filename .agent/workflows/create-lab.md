---
description: Create a standalone runner (Lab) for a UI component
---

1.  Identify the target UI component class and its file path (e.g., `src/ui/components/navigation.py`).
2.  Create the `scripts/lab/` directory if it does not exist.
3.  Create a new file `scripts/lab/run_[component_name].py`.
4.  Implement the runner script with the following template:
    ```python
    import sys
    import os
    # Add project root to path
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

    from PySide6.QtWidgets import QApplication
    from src.core.verse_loader import VerseLoader
    from src.managers.study_manager import StudyManager
    from scripts.lab.harness import HotReloadHarness

    def main():
        app = QApplication(sys.argv)
        # Mock dependencies (add as needed)
        loader = VerseLoader()
        
        def factory(cls):
            return cls(loader)

        # Hot-reload harness
        harness = HotReloadHarness(
            module_name="[module_import_path]",
            class_name="[ComponentClass]",
            factory_func=factory
        )
        harness.show()
        
        sys.exit(app.exec())

    if __name__ == "__main__":
        main()
    ```

5.  Notify the user that the lab script is ready and provides the command to run it.
