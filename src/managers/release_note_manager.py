import os
from PySide6.QtCore import QSettings, QObject
from src.core.constants import APP_VERSION
from src.utils.path_utils import get_resource_path

class ReleaseNoteManager(QObject):
    """
    Manages release notes, tracking view counts and seen status across versions.
    """
    def __init__(self):
        super().__init__()
        # Use QSettings to track seen version and view count
        self.settings = QSettings("JonathanHarris", "JehuReader")
        self.version = APP_VERSION
        self.notes_dir = get_resource_path(os.path.join("resources", "release_notes"))
        
    def should_show_release_note(self) -> bool:
        """
        Returns True if the release note for the current version should be shown.
        Shows the note for the first 5 times after a version update.
        """
        last_seen_version = self.settings.value("release_notes/last_seen_version", "")
        
        if last_seen_version != self.version:
            # New version detected or first run, reset counter
            self.settings.setValue("release_notes/last_seen_version", self.version)
            self.settings.setValue("release_notes/view_count", 0)
            return True
        
        view_count = int(self.settings.value("release_notes/view_count", 0))
        return view_count < 5

    def increment_view_count(self):
        """
        Increments the view count for the current version.
        """
        view_count = int(self.settings.value("release_notes/view_count", 0))
        self.settings.setValue("release_notes/view_count", view_count + 1)

    def get_current_release_note(self) -> str:
        """
        Reads the markdown content for the current version.
        """
        return self.get_note_content(self.version)

    def get_all_release_notes(self) -> list:
        """
        Returns a list of all available release note versions, sorted descending.
        """
        if not os.path.exists(self.notes_dir):
            return []
        
        notes = []
        for f in os.listdir(self.notes_dir):
            if f.startswith("v") and f.endswith(".md"):
                version = f[1:-3] # Strip 'v' and '.md'
                notes.append(version)
        
        # Simple version sort (reverse alphabetical usually works for padded versions, 
        # but let's assume standard versioning for now)
        return sorted(notes, key=lambda x: [int(p) for p in x.split('.')], reverse=True)

    def get_note_content(self, version: str) -> str:
        """
        Reads the markdown content for a specific version.
        """
        note_path = os.path.join(self.notes_dir, f"v{version}.md")
        if os.path.exists(note_path):
            try:
                with open(note_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                return f"# Error\n\nFailed to read release note for v{version}: {e}"
        return f"# Release Notes - v{version}\n\nNo release notes available for this version."
