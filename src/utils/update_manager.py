import sys
import os
import subprocess
import urllib.request
import json
import tempfile
import ssl
import certifi
from src.core.constants import APP_VERSION, GITHUB_API_LATEST_RELEASE

class UpdateManager:
    """Handles checking for and applying application updates from GitHub."""

    @staticmethod
    def get_latest_release_info():
        """Fetches the latest release metadata from the GitHub repository."""
        try:
            # GitHub API requires a User-Agent header
            req = urllib.request.Request(GITHUB_API_LATEST_RELEASE)
            req.add_header('User-Agent', 'Jehu-Reader-Updater')
            
            # Use certifi's CA bundle for SSL verification (critical for macOS)
            context = ssl.create_default_context(cafile=certifi.where())
            
            with urllib.request.urlopen(req, timeout=10, context=context) as response:
                if response.status == 200:
                    return json.loads(response.read().decode('utf-8')), None
        except Exception as e:
            error_msg = str(e)
            print(f"[UpdateManager] Failed to fetch release info: {error_msg}")
            return None, error_msg
        return None, "Unexpected response status"

    @staticmethod
    def check_for_updates():
        """
        Compares the local version with the latest GitHub release.
        Returns (relese_info, error_msg).
        """
        release_info, error_msg = UpdateManager.get_latest_release_info()
        if not release_info:
            return None, error_msg

        latest_tag = release_info.get('tag_name', '').lstrip('v')
        if not latest_tag:
            return None

        print(f"[UpdateManager] Local version: {APP_VERSION}, Latest on GitHub: {latest_tag}")

        try:
            # Simple semantic version comparison (major.minor.patch)
            def to_tuple(v):
                return tuple(map(int, (v.split('.'))))
            
            if to_tuple(latest_tag) > to_tuple(APP_VERSION):
                return release_info
        except (ValueError, IndexError):
            # Fallback to string comparison if versions aren't perfectly formatted
            if latest_tag > APP_VERSION:
                return release_info, None

        return None, None

    @staticmethod
    def start_update(release_info):
        """
        Downloads the latest executable/installer and handles replacement.
        """
        assets = release_info.get('assets', [])
        download_url = None
        
        # Detect platform asset
        extension = ".exe" if sys.platform == "win32" else ".dmg"
        for asset in assets:
            if asset['name'].lower().endswith(extension):
                download_url = asset['browser_download_url']
                break
        
        if not download_url:
            print(f"[UpdateManager] No {extension} asset found in latest release.")
            return False

        try:
            temp_dir = tempfile.gettempdir()
            filename = "JehuReader_update" + extension
            new_file_path = os.path.join(temp_dir, filename)

            print(f"[UpdateManager] Downloading update from {download_url}...")
            
            # Download new file
            req = urllib.request.Request(download_url)
            req.add_header('User-Agent', 'Jehu-Reader-Updater')
            
            # Use certifi's CA bundle for SSL verification
            context = ssl.create_default_context(cafile=certifi.where())
            
            with urllib.request.urlopen(req, context=context) as response, open(new_file_path, 'wb') as out_file:
                out_file.write(response.read())

            if sys.platform == "win32":
                return UpdateManager._apply_windows_update(new_file_path)
            elif sys.platform == "darwin":
                # On Mac, just open the DMG
                print("[UpdateManager] Opening DMG for manual installation.")
                subprocess.Popen(["open", new_file_path])
                return True
            
            return False
        except Exception as e:
            print(f"[UpdateManager] Critical error during update: {e}")
            return False

    @staticmethod
    def _apply_windows_update(new_exe_path):
        """Windows-specific self-replacement logic using a batch script."""
        current_exe = os.path.abspath(sys.executable)
        if not current_exe.lower().endswith('.exe'):
            print("[UpdateManager] Self-update only supported for compiled EXE.")
            return False

        temp_dir = tempfile.gettempdir()
        batch_script_path = os.path.join(temp_dir, "apply_jehu_update.bat")
        
        batch_content = f"""@echo off
echo Finalizing Jehu Reader update...
timeout /t 2 /nobreak > nul
del /f /q "{current_exe}"
move /y "{new_exe_path}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
"""
        with open(batch_script_path, 'w') as f:
            f.write(batch_content)

        subprocess.Popen(
            ["cmd.exe", "/c", batch_script_path],
            creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.DETACHED_PROCESS,
            shell=True
        )
        return True
