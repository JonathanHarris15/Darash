---
description: Create a new release note for the application
---

1.  Identify the new version number (e.g., `0.1.3`).
2.  Update `src/core/constants.py` with the new `APP_VERSION`.
3.  Create a new file `resources/release_notes/v[version].md`.
4.  Populate it with a template:
    ```markdown
    # Release Notes - v[version]

    ## Key Changes
    - [Change 1]
    - [Change 2]

    ## Coming Soon
    - [Future Feature]
    ```
5.  Notify the user that the new release note is ready for editing.
