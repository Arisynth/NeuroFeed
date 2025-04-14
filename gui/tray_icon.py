def TrayIcon(main_window):
    """
    托盘图标类
    """
    from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
    from PyQt6.QtGui import QIcon, QAction, QCursor  # Added QCursor import
    from PyQt6.QtCore import Qt, QTimer
    from core.localization import get_text
    from utils.resource_path import get_resource_path
    import platform
    import sys
    
    # Import macOS-specific utilities conditionally
    if platform.system() == 'Darwin':  # macOS
        from utils.macos_utils import show_dock_icon
        try:
            import AppKit
            import objc
            HAS_APPKIT = True
        except ImportError:
            HAS_APPKIT = False
            print("Warning: AppKit not available, tray icon menu might not work properly")

    class TrayIcon(QSystemTrayIcon):
        def __init__(self, main_window):
            super().__init__(main_window)
            self.main_window = main_window
            icon_path = get_resource_path("resources/icon.png")
            self.setIcon(QIcon(icon_path))
            self.setVisible(True)
            self.custom_menu = None  # Store reference to custom menu
            
            # Create custom menu - not connected to the tray icon yet
            self.custom_menu = QMenu()
            self.show_action = QAction(get_text("show_window"))
            self.exit_action = QAction(get_text("exit"))
            
            # Connect signals
            self.show_action.triggered.connect(self.show_main_window)
            self.exit_action.triggered.connect(self.exit_app)
            
            # Add menu items
            self.custom_menu.addAction(self.show_action)
            self.custom_menu.addAction(self.exit_action)
            
            # On macOS, we'll handle right-clicks manually
            if platform.system() == 'Darwin':
                # Connect the activation signal but don't set the context menu
                self.activated.connect(self.handle_activation)
            else:
                # On other platforms, use the standard approach
                self.setContextMenu(self.custom_menu)
                self.activated.connect(self.on_tray_icon_activated)
            
            print("Tray icon initialized")
        
        def show_main_window(self):
            """显示主窗口"""
            # On macOS, show the dock icon when restoring window
            if platform.system() == 'Darwin':
                show_dock_icon()
                
            self.main_window.showNormal()
            self.main_window.activateWindow()
            self.main_window.raise_()
        
        def exit_app(self):
            """退出应用程序"""
            self.main_window.tray_icon = None
            self.main_window.really_quit = True
            self.main_window.exit_application()
        
        def on_tray_icon_activated(self, reason):
            """处理托盘图标激活事件 (非macOS平台)"""
            if reason == QSystemTrayIcon.ActivationReason.Trigger:
                if self.main_window.isVisible():
                    self.main_window.hide()
                else:
                    self.show_main_window()
        
        def handle_activation(self, reason):
            """统一处理macOS上托盘图标的点击"""
            if reason == QSystemTrayIcon.ActivationReason.Trigger:
                # 单击: 切换窗口显示状态
                if self.main_window.isVisible():
                    self.main_window.hide()
                else:
                    self.show_main_window()
            elif reason == QSystemTrayIcon.ActivationReason.Context:
                # 右击: 显示自定义菜单
                self.show_custom_menu()
        
        def show_custom_menu(self):
            """在macOS上安全地显示自定义托盘菜单"""
            if platform.system() == 'Darwin' and HAS_APPKIT:
                try:
                    # 激活应用程序，使菜单项变为可点击状态
                    ns_app = AppKit.NSApplication.sharedApplication()
                    ns_app.activateIgnoringOtherApps_(True)
                    
                    # 给系统一点时间来处理应用程序激活
                    QTimer.singleShot(200, self._delayed_show_menu)
                except Exception as e:
                    print(f"Error activating app for menu: {e}")
                    self._fallback_show_menu()
            else:
                self._fallback_show_menu()
        
        def _delayed_show_menu(self):
            """延迟显示菜单，确保应用程序已经被激活"""
            # 在显示菜单前再次确认应用程序已激活
            if platform.system() == 'Darwin' and HAS_APPKIT:
                try:
                    # 获取当前光标位置并显示菜单
                    cursor_pos = QCursor.pos()
                    self.custom_menu.popup(cursor_pos)
                    print("Menu shown at cursor position after app activation")
                except Exception as e:
                    print(f"Error showing menu: {e}")
                    self._fallback_show_menu()
            else:
                self._fallback_show_menu()
        
        def _fallback_show_menu(self):
            """后备方法，简单地在当前光标位置显示菜单"""
            try:
                self.custom_menu.popup(QCursor.pos())
                print("Menu shown using fallback method")
            except Exception as e:
                print(f"Failed to show menu with fallback method: {e}")
    
    return TrayIcon(main_window)