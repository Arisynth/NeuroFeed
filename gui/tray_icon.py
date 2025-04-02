def TrayIcon(main_window):
    """
    托盘图标类
    """
    from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QAction
    from PyQt6.QtGui import QIcon
    from PyQt6.QtCore import Qt
    from core.localization import get_text  # 添加本地化导入

    class TrayIcon(QSystemTrayIcon):
        def __init__(self, main_window):
            super().__init__(main_window)
            self.main_window = main_window
            self.setIcon(QIcon("icon.png"))
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