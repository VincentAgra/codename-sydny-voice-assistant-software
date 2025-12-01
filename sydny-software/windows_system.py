"""
Windows System Control Module
Handles volume, power, and system controls for Windows
"""

import subprocess
import os
import shutil
from pathlib import Path
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

# SAFETY MODE - Set to False to enable actual execution
ANNOUNCE_ONLY = True
print(f"DEBUG: windows_system loaded with ANNOUNCE_ONLY = {ANNOUNCE_ONLY}")

def set_announce_mode(enabled):
    """Toggle announce-only mode on/off"""
    global ANNOUNCE_ONLY
    ANNOUNCE_ONLY = enabled

def get_volume_interface():
    """Get the Windows audio volume interface"""
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(
            IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        return volume
    except Exception as e:
        print(f"Error getting volume interface: {e}")
        return None

def set_volume(level):
    """Set system volume (0-100)"""
    if ANNOUNCE_ONLY:
        return f"Would set volume to {level}%"
    
    try:
        # Validate input
        if not isinstance(level, int):
            return "Volume level must be a number"
        
        if not 0 <= level <= 100:
            return "Volume must be between 0 and 100"
        
        volume = get_volume_interface()
        if volume is None:
            return "Error: Could not access volume control"
        
        scalar = level / 100.0
        volume.SetMasterVolumeLevelScalar(scalar, None)
        return f"Volume set to {level}%"
    except Exception as e:
        return f"Error setting volume: {e}"

def get_volume():
    """Get current system volume"""
    try:
        volume = get_volume_interface()
        if volume is None:
            return 0
        
        current_volume = volume.GetMasterVolumeLevelScalar()
        return int(current_volume * 100)
    except Exception as e:
        print(f"Error getting volume: {e}")
        return 0

def mute():
    """Mute system audio"""
    if ANNOUNCE_ONLY:
        return "Would mute audio"
    
    try:
        volume = get_volume_interface()
        if volume is None:
            return "Error: Could not access volume control"
        
        volume.SetMute(1, None)
        return "Audio muted"
    except Exception as e:
        return f"Error muting: {e}"

def unmute():
    """Unmute system audio"""
    if ANNOUNCE_ONLY:
        return "Would unmute audio"
    
    try:
        volume = get_volume_interface()
        if volume is None:
            return "Error: Could not access volume control"
        
        volume.SetMute(0, None)
        return "Audio unmuted"
    except Exception as e:
        return f"Error unmuting: {e}"
    
def shutdown_system():
    """
    Shutdown the computer
    Returns: Success message or action description
    """
    if ANNOUNCE_ONLY:
        return "Would shut down the system"
    
    try:
        subprocess.run(["shutdown", "/s", "/t", "0"], check=True)
        return "Shutting down system"
    except subprocess.CalledProcessError as e:
        return f"Error shutting down: {e}"
    except Exception as e:
        return f"Unexpected error during shutdown: {e}"

def restart_system():
    """
    Restart the computer
    Returns: Success message or action description
    """
    if ANNOUNCE_ONLY:
        return "Would restart the system"
    
    try:
        subprocess.run(["shutdown", "/r", "/t", "0"], check=True)
        return "Restarting system"
    except subprocess.CalledProcessError as e:
        return f"Error restarting: {e}"
    except Exception as e:
        return f"Unexpected error during restart: {e}"

def sleep_system():
    """
    Put the computer to sleep
    Returns: Success message or action description
    """
    if ANNOUNCE_ONLY:
        return "Would put the system to sleep"
    
    try:
        # Windows sleep command using rundll32
        subprocess.run([
            "rundll32.exe", 
            "powrprof.dll,SetSuspendState", 
            "0", "1", "0"
        ], check=True)
        return "Putting system to sleep"
    except subprocess.CalledProcessError as e:
        return f"Error sleeping system: {e}"
    except Exception as e:
        return f"Unexpected error during sleep: {e}"
    
# ============================================================================
# APP CONTROL FUNCTIONS
# ============================================================================

def open_app(app_name):
    """
    Open an application by name
    Args:
        app_name: Name of the application (e.g., 'notepad')
    Returns: Success message or error description
    """
    if ANNOUNCE_ONLY:
        return f"Would open {app_name}"
    
    try:
        # Validate input
        if not app_name or not isinstance(app_name, str):
            return "Invalid app name"
        
        # For now, we only support notepad
        if "notepad" in app_name.lower():
            subprocess.Popen("notepad.exe", shell=True)
            return f"Opening notepad"
        else:
            return f"I don't know how to open {app_name} yet"
            
    except FileNotFoundError:
        return f"Could not find {app_name}"
    except Exception as e:
        return f"Error opening {app_name}: {e}"

def close_app(app_name):
    """
    Close an application by name
    Args:
        app_name: Name of the application (e.g., 'notepad')
    Returns: Success message or error description
    """
    if ANNOUNCE_ONLY:
        return f"Would close {app_name}"
    
    try:
        # Validate input
        if not app_name or not isinstance(app_name, str):
            return "Invalid app name"
        
        # For now, we only support notepad
        if "notepad" in app_name.lower():
            # Use taskkill to close notepad
            result = subprocess.run(
                ["taskkill", "/F", "/IM", "notepad.exe"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return f"Closed notepad"
            else:
                # Check if notepad wasn't running
                if "not found" in result.stderr.lower():
                    return "Notepad is not running"
                else:
                    return f"Error closing notepad"
        else:
            return f"I don't know how to close {app_name} yet"
            
    except Exception as e:
        return f"Error closing {app_name}: {e}"
    
# ============================================================================
# FILE OPERATIONS
# ============================================================================

def get_search_paths():
    """
    Get common user folders to search for files
    Returns: List of Path objects
    """
    try:
        user_home = Path.home()
        paths = [
            user_home / "Desktop",
            user_home / "Documents",
            user_home / "Downloads",
            user_home,  # Home directory itself
        ]
        # Only return paths that exist
        return [p for p in paths if p.exists()]
    except Exception as e:
        print(f"Error getting search paths: {e}")
        return []

def search_file(filename):
    """
    Search for a file in common locations
    Args:
        filename: Name of file to search for (can be partial)
    Returns: List of matching file paths (up to 5 matches)
    """
    matches = []
    
    try:
        # Validate input
        if not filename or not isinstance(filename, str):
            return matches
        
        search_paths = get_search_paths()
        
        for search_path in search_paths:
            try:
                # Search in the directory (not recursive for now, to keep it simple)
                for item in search_path.glob(f"*{filename}*"):
                    if item.is_file():
                        matches.append(str(item))
                        
                # Limit to first 5 matches to avoid overwhelming results
                if len(matches) >= 5:
                    break
            except PermissionError:
                # Skip directories we don't have permission to access
                continue
            except Exception as e:
                print(f"Error searching in {search_path}: {e}")
                continue
                
    except Exception as e:
        print(f"Error searching for {filename}: {e}")
    
    return matches

def open_file(filepath):
    """
    Open a file with its default application
    Args:
        filepath: Full path to the file
    Returns: Success message or error description
    """
    if ANNOUNCE_ONLY:
        return f"Would open {Path(filepath).name}"
    
    try:
        # Validate file exists
        if not os.path.exists(filepath):
            return f"File not found: {filepath}"
        
        if not os.path.isfile(filepath):
            return f"Not a file: {filepath}"
        
        os.startfile(filepath)
        return f"Opening {Path(filepath).name}"
    except FileNotFoundError:
        return f"File not found: {filepath}"
    except PermissionError:
        return f"Permission denied: {filepath}"
    except Exception as e:
        return f"Error opening file: {e}"
    
def move_file(source, destination):
    """
    Move a file from source to destination
    Args:
        source: Source file path
        destination: Destination directory or file path
    Returns: Success message or error description
    """
    if ANNOUNCE_ONLY:
        return f"Would move {Path(source).name} to {destination}"
    
    try:
        # Validate source exists
        if not os.path.exists(source):
            return f"Source file not found: {source}"
        
        if not os.path.isfile(source):
            return f"Source is not a file: {source}"
        
        shutil.move(source, destination)
        return f"Moved {Path(source).name} to {destination}"
    except FileNotFoundError:
        return f"File not found: {source}"
    except PermissionError:
        return f"Permission denied"
    except Exception as e:
        return f"Error moving file: {e}"
    
def delete_file(filepath):
    """
    Delete a file (DESTRUCTIVE - should always use confirmation)
    Args:
        filepath: Path to file to delete
    Returns: Success message or error description
    """
    if ANNOUNCE_ONLY:
        return f"Would delete {Path(filepath).name}"
    
    try:
        # Validate file exists
        if not os.path.exists(filepath):
            return f"File not found: {filepath}"
        
        if not os.path.isfile(filepath):
            return f"Not a file: {filepath}"
        
        os.remove(filepath)
        return f"Deleted {Path(filepath).name}"
    except FileNotFoundError:
        return f"File not found: {filepath}"
    except PermissionError:
        return f"Permission denied: Cannot delete {Path(filepath).name}"
    except Exception as e:
        return f"Error deleting file: {e}"