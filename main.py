from gui.main_window import MainWindow
from gui.tray_icon import TrayIcon
from core.scheduler import start_scheduler
from PyQt6.QtWidgets import QApplication
import sys

def main():
    app = QApplication(sys.argv)

    main_win = MainWindow()
    tray = TrayIcon(main_win)

    start_scheduler()  # 初始化定时任务（初期可放空或打印日志）

    tray.run()  # 启动托盘图标

if __name__ == "__main__":
    main()