---
name: gh-release-tag
description: Bumps the application version, updates ARCHITECTURE.md, creates a git tag, and pushes to GitHub to trigger a release. Use when a new build/release of Jehu-Reader is needed.
---

# GitHub Release & Tagging Workflow

This skill automates the version bump and release process.

## Steps

1. **Check Current Version**: Read `src/core/constants.py` to find `APP_VERSION`.
2. **Determine New Version**:
   - Suggest a patch bump (e.g., `0.1.1` -> `0.1.2`).
   - Ask the user for a new version (major/minor/patch).
3. **Apply Version Bump**:
   - Update `APP_VERSION` in `src/core/constants.py`.
   - Update `ARCHITECTURE.md` in the "Auto-Update / Versioning" row (e.g., `(Current: v0.1.2)`).
4. **Git Operations**:
   - `git add src/core/constants.py ARCHITECTURE.md`
   - `git commit -m "chore: release vX.Y.Z"`
   - `git tag vX.Y.Z`
   - `git push origin [current_branch]`
   - `git push origin vX.Y.Z`
5. **Verify**: Confirm the tag push was successful.

## Safety Rules
- Ensure all tests pass (`pytest`) BEFORE starting the release process.
- Do not push if there are uncommitted changes other than the version bump unless confirmed by the user.
