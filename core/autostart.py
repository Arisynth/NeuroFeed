import os
import sys
import platform
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def get_app_path():
    """获取应用程序路径"""
    if getattr(sys, 'frozen', False):
        # 如果是打包后的应用
        return sys.executable
    else:
        # 如果是开发环境
        main_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main.py"))
        python_path = sys.executable
        return f'"{python_path}" "{main_path}"'

def enable_autostart():
    """启用开机自启动"""
    system = platform.system()
    
    try:
        if system == "Windows":
            _enable_windows_autostart()
        elif system == "Darwin":  # macOS
            _enable_macos_autostart()
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
            _disable_macos_autostart()
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

def _enable_macos_autostart():
    """在macOS上启用开机自启动"""
    from string import Template
    
    plist_template = Template('''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.neurofeed</string>
    <key>ProgramArguments</key>
    <array>
        <string>$app_path</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>''')
    
    # 用户的LaunchAgents目录
    launch_dir = os.path.expanduser("~/Library/LaunchAgents")
    os.makedirs(launch_dir, exist_ok=True)
    
    plist_path = os.path.join(launch_dir, "com.user.neurofeed.plist")
    
    # 写入plist文件
    with open(plist_path, 'w') as f:
        f.write(plist_template.substitute(app_path=get_app_path()))
    
    # 加载启动项
    os.system(f"launchctl load {plist_path}")

def _disable_macos_autostart():
    """在macOS上禁用开机自启动"""
    plist_path = os.path.expanduser("~/Library/LaunchAgents/com.user.neurofeed.plist")
    
    # 卸载启动项
    if os.path.exists(plist_path):
        os.system(f"launchctl unload {plist_path}")
        os.remove(plist_path)

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
        plist_path = os.path.expanduser("~/Library/LaunchAgents/com.user.neurofeed.plist")
        return os.path.exists(plist_path)
        
    elif system == "Linux":
        desktop_path = os.path.expanduser("~/.config/autostart/neurofeed.desktop")
        return os.path.exists(desktop_path)
        
    return False
