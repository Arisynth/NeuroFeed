from PyQt6.QtWidgets import (QMainWindow, QLabel, QVBoxLayout, QHBoxLayout, 
                           QWidget, QPushButton, QTabWidget, QMessageBox)
from PyQt6.QtCore import Qt
from core.scheduler import run_task_now
from gui.components.task_manager import TaskManager
from gui.components.feed_manager import FeedManager
from gui.components.recipient_manager import RecipientManager
from gui.components.scheduler_manager import SchedulerManager
from core.config_manager import save_task

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NewsDigest")
        self.setMinimumSize(800, 500)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Add title label
        title_label = QLabel("NewsDigest - RSS Feed Aggregator")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 15px;")
        main_layout.addWidget(title_label)
        
        # Create task manager
        self.task_manager = TaskManager()
        self.task_manager.task_changed.connect(self.on_task_changed)
        main_layout.addWidget(self.task_manager)
        
        # Task details section with tabs
        self.tabs = QTabWidget()
        
        # Tab 1: RSS Feeds - using FeedManager
        self.feed_manager = FeedManager()
        self.tabs.addTab(self.feed_manager, "RSS Feeds")
        
        # Tab 2: Scheduling - using SchedulerManager
        self.scheduler_manager = SchedulerManager()
        self.tabs.addTab(self.scheduler_manager, "Schedule")
        
        # Tab 3: Recipients - using RecipientManager
        self.recipient_manager = RecipientManager()
        self.tabs.addTab(self.recipient_manager, "Recipients")
        
        main_layout.addWidget(self.tabs)
        
        # Action buttons section
        buttons_layout = QHBoxLayout()
        
        self.run_now_btn = QPushButton("Run Now")
        self.settings_btn = QPushButton("Settings")
        
        self.run_now_btn.clicked.connect(self.run_task_now)
        self.settings_btn.clicked.connect(self.open_settings)
        
        buttons_layout.addWidget(self.run_now_btn)
        buttons_layout.addWidget(self.settings_btn)
        
        main_layout.addLayout(buttons_layout)
        
        # 一定要初始化任务，否则组件不会显示任务信息
        if self.task_manager.current_task:
            self.on_task_changed(self.task_manager.current_task)
        
        # 打印日志确认主窗口已正确初始化
        print("主窗口初始化完成")
    
    def on_task_changed(self, task):
        """Handle task changes from task manager"""
        if not task:
            print("警告: 收到空任务对象")
            return
            
        print(f"任务已更改: {task.name} (ID: {task.task_id})")
        
        # Update all components with the new task
        self.feed_manager.set_task(task)
        self.scheduler_manager.set_task(task)
        self.recipient_manager.set_task(task)
    
    def run_task_now(self):
        """Execute the RSS fetching and processing task immediately"""
        task = self.task_manager.get_current_task()
        if not task:
            QMessageBox.warning(self, "No Task", "No task selected or available.")
            return
        
        # 更新按钮状态，防止重复点击
        self.run_now_btn.setEnabled(False)
        self.run_now_btn.setText("Running...")
        
        # 首先保存最新的任务状态到配置文件
        save_task(task)
        
        # 向用户显示任务已经开始的提示
        QMessageBox.information(self, "Task Started", 
                              f"The task '{task.name}' has started in background.\n\n"
                              f"This may take some time, especially if using AI filtering.\n"
                              f"You can continue using the application while the task runs.")
        
        try:
            # 记录任务ID用于调试
            task_id = task.task_id
            print(f"Running task with ID: {task_id}")
            
            # 调用scheduler中的方法立即执行任务
            run_task_now(task_id)
            
            # 由于任务在后台线程执行，这里只更新UI状态
            task.update_task_run()
            save_task(task)
            
            # 立即更新调度器UI以显示最新的运行时间和下次运行时间
            self.scheduler_manager.update_scheduler_ui()
            
            # 删除延时更新的代码，任务一旦开始，就已经知道下次何时运行了
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"任务执行错误: {error_details}")
            QMessageBox.critical(self, "Task Error", 
                               f"Error starting task: {str(e)}")
        finally:
            # 恢复按钮状态
            self.run_now_btn.setEnabled(True)
            self.run_now_btn.setText("Run Now")
    
    def open_settings(self):
        """Open the settings window"""
        from gui.setting_window import SettingsWindow
        try:
            settings_dialog = SettingsWindow(self)
            settings_dialog.exec()
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"打开设置窗口错误: {error_details}")
            QMessageBox.critical(self, "Settings Error", 
                               f"Error opening settings: {str(e)}")