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
            # Path to the .app bundle
            # sys.executable is often /path/to/YourApp.app/Contents/MacOS/YourApp
            # Go up three levels to get the .app path
            bundle_path = os.path.abspath(os.path.join(os.path.dirname(sys.executable), "..", "..", ".."))
            if bundle_path.endswith(".app"):
                logger.debug(f"Detected packaged app bundle path: {bundle_path}")
                return bundle_path
            else:
                # Fallback or alternative structure? Log a warning.
                logger.warning(f"Could not determine .app bundle path from {sys.executable}. Falling back to executable.")
                return sys.executable  # Fallback to executable path if structure is unexpected
        else:
            # Windows/Linux packaged app
            return sys.executable
    else:
        # Running from source
        # Assuming main script is in the root or a known location relative to this file
        main_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main.py"))  # Adjust if main.py is elsewhere
        python_executable = sys.executable
        # Return command parts for subprocess
        return [python_executable, main_script]

def _get_plist_path():
    """Get the path for the launchd plist file."""
    return os.path.expanduser(f"~/Library/LaunchAgents/{BUNDLE_ID}.plist")

def enable_autostart():
    """启用开机自启动"""
    system = platform.system()
    
    try:
        if system == "Windows":
            _enable_windows_autostart()
        elif system == "Darwin":  # macOS
            _enable_autostart_macos()
        elif system == "Linux":
            _enable_linux_autostart()
        else:
            logger.warning(f"不支持在 {system} 系统上设置开机自启动")
            return False
            
        logger.info(f"已在 {system} 系统上设置开机自启动")
        return True
    except Exception as e:
        logger.error(f"设置开机自启动失败: {str(e)}")
        return False

def disable_autostart():
    """禁用开机自启动"""
    system = platform.system()
    
    try:
        if system == "Windows":
            _disable_windows_autostart()
        elif system == "Darwin":  # macOS
            _disable_autostart_macos()
        elif system == "Linux":
            _disable_linux_autostart()
        else:
            logger.warning(f"不支持在 {system} 系统上禁用开机自启动")
            return False
            
        logger.info(f"已在 {system} 系统上禁用开机自启动")
        return True
    except Exception as e:
        logger.error(f"禁用开机自启动失败: {str(e)}")
        return False

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
        # If it's a list (running from source) or not a .app bundle string
        if isinstance(app_path, list):
            logger.error("Cannot enable autostart: Running from source. macOS autostart via launchd currently only supports packaged .app bundles.")
        else: # It's a string, but not ending in .app
            logger.error(f"Cannot enable autostart: Invalid app path for macOS bundle: {app_path}")
        return False

    plist_content = {
        "Label": BUNDLE_ID,
        "ProgramArguments": ["/usr/bin/open", "-a", app_path],  # Use open -a
        "RunAtLoad": True,
        "KeepAlive": False,  # Don't restart if it quits
        # "StandardOutPath": os.path.expanduser(f"~/Library/Logs/{APP_NAME}.log"), # Optional logging
        # "StandardErrorPath": os.path.expanduser(f"~/Library/Logs/{APP_NAME}.err"), # Optional logging
    }

    try:
        os.makedirs(os.path.dirname(plist_path), exist_ok=True)
        with open(plist_path, "wb") as fp:
            plistlib.dump(plist_content, fp)
        logger.info(f"Created launchd plist at {plist_path}")

        # Load the service using subprocess
        result = subprocess.run(["launchctl", "load", "-w", plist_path], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            # Check if it's already loaded (common 'error')
            if "already loaded" not in result.stderr.lower():
                logger.error(f"Failed to load launchd service: {result.stderr}")
                return False
            else:
                logger.info(f"Launchd service {BUNDLE_ID} already loaded.")
        else:
            logger.info(f"Successfully loaded launchd service {BUNDLE_ID}")
        return True

    except Exception as e:
        logger.error(f"Error enabling autostart on macOS: {e}", exc_info=True)
        return False

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
