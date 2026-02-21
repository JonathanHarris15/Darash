# Jehu-Reader Project Directions

## Environment & Execution
- **Virtual Environment:** This project runs in a dedicated virtual environment located outside the project directory (to avoid OneDrive synchronization issues). 
- **Execution:** The agent MUST NOT attempt to start or run the project, as the environment is managed externally. Focus on code modification, analysis, and testing within the source structure.

## Architectural Principles
- **File Granularity:** Prioritize a larger number of short, focused files over fewer long files.
- **Logical Partitioning:** Functionality must be strictly partitioned into logical modules. Each file should have a single, clear responsibility.
- **Modularity:** When adding new features or refactoring, always look for opportunities to extract logic into new files rather than expanding existing ones.
