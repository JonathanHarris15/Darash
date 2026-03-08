import sys
import os
import subprocess
import urllib.request
import json
import tempfile
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
            
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            print(f"[UpdateManager] Failed to fetch release info: {e}")
        return None

    @staticmethod
    def check_for_updates():
        """
        Compares the local version with the latest GitHub release.
        Returns the release info dictionary if a newer version is available, else None.
        """
        release_info = UpdateManager.get_latest_release_info()
        if not release_info:
            return None

        latest_tag = release_info.get('tag_name', '').lstrip('v')
        if not latest_tag:
            return None

        try:
            # Simple semantic version comparison (major.minor.patch)
            def to_tuple(v):
                return tuple(map(int, (v.split('.'))))
            
            if to_tuple(latest_tag) > to_tuple(APP_VERSION):
                return release_info
        except (ValueError, IndexError):
            # Fallback to string comparison if versions aren't perfectly formatted
            if latest_tag > APP_VERSION:
                return release_info

        return None

    @staticmethod
    def start_update(release_info):
        """
        Downloads the latest executable and launches a detached batch script 
        to replace the current running file.
        """
        assets = release_info.get('assets', [])
        download_url = None
        
        # Look for the first .exe asset
        for asset in assets:
            if asset['name'].lower().endswith('.exe'):
                download_url = asset['browser_download_url']
                break
        
        if not download_url:
            print("[UpdateManager] No executable asset found in latest release.")
            return False

        try:
            current_exe = os.path.abspath(sys.executable)
            if not current_exe.lower().endswith('.exe'):
                print("[UpdateManager] Self-update is only supported when running as a compiled EXE.")
                return False

            # Prepare paths
            temp_dir = tempfile.gettempdir()
            new_exe_path = os.path.join(temp_dir, "JehuReader_update.exe")
            batch_script_path = os.path.join(temp_dir, "apply_jehu_update.bat")

            print(f"[UpdateManager] Downloading update from {download_url}...")
            
            # Download new EXE
            req = urllib.request.Request(download_url)
            req.add_header('User-Agent', 'Jehu-Reader-Updater')
            with urllib.request.urlopen(req) as response, open(new_exe_path, 'wb') as out_file:
                out_file.write(response.read())

            print(f"[UpdateManager] Update downloaded to {new_exe_path}. Preparing replacement.")

            # Create the Windows batch script to handle replacement after this process exits
            # Using 'timeout' to wait for the current process to close
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

            # Launch the batch script detached
            print("[UpdateManager] Launching updater script and exiting...")
            subprocess.Popen(
                ["cmd.exe", "/c", batch_script_path],
                creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.DETACHED_PROCESS,
                shell=True
            )
            
            return True
        except Exception as e:
            print(f"[UpdateManager] Critical error during update: {e}")
            return False
