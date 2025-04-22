import os
import sys
import platform
import logging
import subprocess  # Import subprocess
import plistlib    # Import plistlib
from pathlib import Path

# Define a unique identifier for the launchd service
APP_NAME = "NeuroFeed"  # Or get dynamically if needed
BUNDLE_ID = f"com.yourcompany.{APP_NAME.lower()}"  # Replace 'yourcompany' or make dynamic

logger = logging.getLogger(__name__)

def get_app_path():
    """Get the path to the executable or the .app bundle."""
    if getattr(sys, 'frozen', False):
        # Packaged app
        if platform.system() == 'Darwin':
            # Find the .app bundle by walking up from the executable path
            current_path = os.path.dirname(sys.executable)
            while current_path != '/' and not current_path.endswith('.app'):
                parent_path = os.path.dirname(current_path)
                if parent_path == current_path: # Avoid infinite loop at root
                    break
                current_path = parent_path

            if current_path.endswith('.app'):
                logger.debug(f"Determined .app bundle path: {current_path}")
                return current_path
            else:
                logger.warning(f"Could not determine .app bundle path from executable {sys.executable}. Falling back to executable path.")
                return sys.executable # Fallback
        else:
            # Windows/Linux packaged app
            return sys.executable
    else:
        # Running from source
        main_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main.py"))
        python_executable = sys.executable
        return [python_executable, main_script]

def _get_plist_path():
    """Get the path for the launchd plist file."""
    return os.path.expanduser(f"~/Library/LaunchAgents/{BUNDLE_ID}.plist")

def enable_autostart():
    """Enable autostart based on the current operating system."""
    system = platform.system()
    logger.info(f"Attempting to enable autostart for {system}")
    success = False # Initialize success flag
    try:
        if system == "Windows":
            success = _enable_windows_autostart()
        elif system == "Darwin": # macOS
            success = _enable_autostart_macos()
        elif system == "Linux":
            success = _enable_linux_autostart()
        else:
            logger.warning(f"Autostart not supported on this OS: {system}")
            success = False

        # Log success/failure based on the result
        if success:
            logger.info(f"Successfully enabled autostart on {system}")
        else:
            # Error should have been logged in the specific function
            logger.warning(f"Failed to enable autostart on {system}")

    except Exception as e:
        logger.error(f"Unexpected error during enable_autostart for {system}: {e}", exc_info=True)
        success = False

    return success # Return the actual success status

def disable_autostart():
    """Disable autostart based on the current operating system."""
    system = platform.system()
    logger.info(f"Attempting to disable autostart for {system}")
    success = False # Initialize success flag
    try:
        if system == "Windows":
            success = _disable_windows_autostart()
        elif system == "Darwin": # macOS
            success = _disable_autostart_macos()
        elif system == "Linux":
            success = _disable_linux_autostart()
        else:
            logger.warning(f"Autostart not supported on this OS: {system}")
            success = False

        # Log success/failure based on the result
        if success:
            logger.info(f"Successfully disabled autostart on {system}")
        else:
            # Error should have been logged in the specific function
            logger.warning(f"Failed to disable autostart on {system}")

    except Exception as e:
        logger.error(f"Unexpected error during disable_autostart for {system}: {e}", exc_info=True)
        success = False

    return success # Return the actual success status

def _enable_windows_autostart():
    """在Windows上启用开机自启动"""
    import winreg as reg
    
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "NeuroFeed"
    
    # 打开注册表键
    key = reg.OpenKey(reg.HKEY_CURRENT_USER, key_path, 0, reg.KEY_WRITE)
    reg.SetValueEx(key, app_name, 0, reg.REG_SZ, get_app_path())
    reg.CloseKey(key)

def _disable_windows_autostart():
    """在Windows上禁用开机自启动"""
    import winreg as reg
    
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "NeuroFeed"
    
    try:
        key = reg.OpenKey(reg.HKEY_CURRENT_USER, key_path, 0, reg.KEY_WRITE)
        reg.DeleteValue(key, app_name)
        reg.CloseKey(key)
    except FileNotFoundError:
        # 值不存在，无需删除
        pass

def _enable_autostart_macos():
    """Enable autostart on macOS using launchd and 'open -a'."""
    app_path = get_app_path()
    plist_path = _get_plist_path()

    # Check if running from source (list) or if it's not a .app bundle (string)
    if not isinstance(app_path, str) or not app_path.endswith(".app"):
        if isinstance(app_path, list):
            logger.error("Cannot enable autostart: Running from source. macOS autostart via launchd currently only supports packaged .app bundles.")
        else: # It's a string, but not ending in .app
            logger.error(f"Cannot enable autostart: Invalid app path for macOS bundle: {app_path}")
        return False # Explicitly return False on failure

    plist_content = {
        "Label": BUNDLE_ID,
        "ProgramArguments": ["/usr/bin/open", "-a", app_path],
        "RunAtLoad": True,
        "KeepAlive": False,
    }

    try:
        os.makedirs(os.path.dirname(plist_path), exist_ok=True)
        with open(plist_path, "wb") as fp:
            plistlib.dump(plist_content, fp)
        logger.info(f"Created launchd plist at {plist_path}")

        result = subprocess.run(["launchctl", "load", "-w", plist_path], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            if "already loaded" not in result.stderr.lower():
                 logger.error(f"Failed to load launchd service: {result.stderr}")
                 # Attempt to remove potentially corrupt plist before returning False
                 try:
                     if os.path.exists(plist_path): os.remove(plist_path)
                 except Exception as rm_err:
                     logger.error(f"Failed to remove plist after load error: {rm_err}")
                 return False # Return False on load failure
            else:
                 logger.info(f"Launchd service {BUNDLE_ID} already loaded.")
        else:
            logger.info(f"Successfully loaded launchd service {BUNDLE_ID}")
        return True # Return True on success

    except Exception as e:
        logger.error(f"Error enabling autostart on macOS: {e}", exc_info=True)
        # Attempt cleanup on exception
        try:
            if os.path.exists(plist_path): os.remove(plist_path)
        except Exception as rm_err:
            logger.error(f"Failed to remove plist after exception: {rm_err}")
        return False # Return False on exception

def _disable_autostart_macos():
    """Disable autostart on macOS using launchd."""
    plist_path = _get_plist_path()

    try:
        # Unload the service first using subprocess
        result = subprocess.run(["launchctl", "unload", "-w", plist_path], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            # Ignore 'Could not find specified service' error if already unloaded/removed
            if "could not find specified service" not in result.stderr.lower() and \
               "no such file or directory" not in result.stderr.lower():
                logger.warning(f"Could not unload launchd service (may already be unloaded): {result.stderr}")
        else:
            logger.info(f"Successfully unloaded launchd service {BUNDLE_ID}")

        # Remove the plist file
        if os.path.exists(plist_path):
            os.remove(plist_path)
            logger.info(f"Removed launchd plist at {plist_path}")
        return True

    except Exception as e:
        logger.error(f"Error disabling autostart on macOS: {e}", exc_info=True)
        return False

def _enable_linux_autostart():
    """在Linux上启用开机自启动"""
    desktop_file = '''[Desktop Entry]
Type=Application
Name=NeuroFeed
Exec={app_path}
Terminal=false
Hidden=false
X-GNOME-Autostart-enabled=true
'''.format(app_path=get_app_path())
    
    # 用户的自启动目录
    autostart_dir = os.path.expanduser("~/.config/autostart")
    os.makedirs(autostart_dir, exist_ok=True)
    
    desktop_path = os.path.join(autostart_dir, "neurofeed.desktop")
    
    # 写入桌面配置文件
    with open(desktop_path, 'w') as f:
        f.write(desktop_file)
    
    # 设置可执行权限
    os.chmod(desktop_path, 0o755)

def _disable_linux_autostart():
    """在Linux上禁用开机自启动"""
    desktop_path = os.path.expanduser("~/.config/autostart/neurofeed.desktop")
    
    if os.path.exists(desktop_path):
        os.remove(desktop_path)

def is_autostart_enabled():
    """检查是否已启用开机自启动"""
    system = platform.system()
    
    if system == "Windows":
        import winreg as reg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "NeuroFeed"
        
        try:
            key = reg.OpenKey(reg.HKEY_CURRENT_USER, key_path, 0, reg.KEY_READ)
            reg.QueryValueEx(key, app_name)
            reg.CloseKey(key)
            return True
        except:
            return False
            
    elif system == "Darwin":  # macOS
        plist_path = _get_plist_path()
        # Check if plist exists and potentially if service is loaded
        # A simple check for plist existence is often sufficient
        exists = os.path.exists(plist_path)
        logger.debug(f"Checking macOS autostart: plist exists at {plist_path}? {exists}")
        return exists
        # More robust check (optional):
        # try:
        #     result = subprocess.run(["launchctl", "list", BUNDLE_ID], capture_output=True, text=True, check=False)
        #     return result.returncode == 0
        # except Exception:
        #     return False
        
    elif system == "Linux":
        desktop_path = os.path.expanduser("~/.config/autostart/neurofeed.desktop")
        return os.path.exists(desktop_path)
        
    return False
