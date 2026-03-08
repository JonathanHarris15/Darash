import os
import sys
from pathlib import Path

def get_resource_path(rel_path: str) -> str:
    """
    Resolves an absolute path to a resource, handling both development
    and packaged (frozen) environments.
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    else:
        # In development, the root is the parent of the 'src' directory
        # Assuming path_utils.py is in src/utils/
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    return os.path.join(base_path, rel_path)

def get_user_data_path(rel_path: str) -> str:
    """
    Returns a platform-appropriate path for storing user data.
    Windows: %APPDATA%/JehuReader/
    macOS: ~/Library/Application Support/JehuReader/
    Linux: ~/.local/share/JehuReader/
    """
    app_name = "JehuReader"
    
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~\\AppData\\Roaming"))
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        # Linux/Unix following XDG Base Directory Specification
        base = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    
    user_app_dir = os.path.join(base, app_name)
    
    # Ensure the directory exists
    if not os.path.exists(user_app_dir):
        os.makedirs(user_app_dir, exist_ok=True)
        
    return os.path.join(user_app_dir, rel_path)
