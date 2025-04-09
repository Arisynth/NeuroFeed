def TrayIcon(main_window):
    """
    托盘图标类
    """
    from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
    from PyQt6.QtGui import QIcon, QAction  # QAction now imported from QtGui, not QtWidgets
    from PyQt6.QtCore import Qt
    from core.localization import get_text  # 添加本地化导入
    from utils.resource_path import get_resource_path  # Import the resource path utility
    import platform
    
    # Import macOS-specific utilities conditionally
    if platform.system() == 'Darwin':  # macOS
        from utils.macos_utils import show_dock_icon

    class TrayIcon(QSystemTrayIcon):
        def __init__(self, main_window):
            super().__init__(main_window)
            self.main_window = main_window
            # Use the utility function to get the correct path to the icon
            icon_path = get_resource_path("resources/icon.png")
            self.setIcon(QIcon(icon_path))
            self.setVisible(True)

            # 创建右键菜单
            self.menu = QMenu()
            self.show_action = QAction(get_text("show_window"))
            self.exit_action = QAction(get_text("exit"))

            # 连接信号
            self.show_action.triggered.connect(self.show_main_window)
            self.exit_action.triggered.connect(self.exit_app)

            # 添加菜单项
            self.menu.addAction(self.show_action)
            self.menu.addAction(self.exit_action)

            # 设置菜单
            self.setContextMenu(self.menu)
            
            # 连接托盘图标的激活信号（例如点击）
            self.activated.connect(self.on_tray_icon_activated)
        
        def show_main_window(self):
            """显示主窗口"""
            # On macOS, show the dock icon when restoring window
            if platform.system() == 'Darwin':
                show_dock_icon()
                
            self.main_window.showNormal()  # 确保窗口正常显示（不是最小化状态）
            self.main_window.activateWindow()  # 激活窗口（使其成为前台窗口）
            self.main_window.raise_()  # 将窗口提升到前面
        
        def exit_app(self):
            """退出应用程序"""
            self.main_window.tray_icon = None  # 避免循环引用
            self.main_window.really_quit = True  # 设置标志，表示真的要退出
            self.main_window.close()  # 关闭主窗口，会触发closeEvent
        
        def on_tray_icon_activated(self, reason):
            """处理托盘图标激活事件"""
            # QSystemTrayIcon.ActivationReason.Trigger 表示单击
            if reason == QSystemTrayIcon.ActivationReason.Trigger:
                # 如果窗口可见，则隐藏；如果不可见，则显示
                if self.main_window.isVisible():
                    self.main_window.hide()
                else:
                    self.show_main_window()
    
    return TrayIcon(main_window)