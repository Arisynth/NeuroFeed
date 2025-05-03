from PyQt6.QtWidgets import (QMainWindow, QLabel, QVBoxLayout, QHBoxLayout, 
                           QWidget, QPushButton, QTabWidget, QMessageBox,
                           QSystemTrayIcon)
from PyQt6.QtCore import Qt, pyqtSlot, QTimer # Import QTimer
from PyQt6.QtGui import QIcon
from core.scheduler import run_task_now, reload_scheduled_tasks
from gui.components.task_manager import TaskManager
from gui.components.feed_manager import FeedManager
from gui.components.recipient_manager import RecipientManager
from gui.components.scheduler_manager import SchedulerManager
from core.config_manager import save_task, get_general_settings, get_app_version
from core.localization import initialize as init_localization, get_text, get_formatted
from gui.tray_icon import TrayIcon
from utils.resource_path import get_resource_path  # Import the resource path utility
import platform
from gui.components.status_bar import CustomStatusBar
from core.status_manager import StatusManager
from core.task_status import TaskStatus  # 添加这个导入
from core.unsubscribe_handler import get_unsubscribe_handler  # Import handler getter
import logging  # Add logging

# Import macOS-specific utilities conditionally
if platform.system() == 'Darwin':  # macOS
    from utils.macos_utils import hide_dock_icon, show_dock_icon

# Logger setup
logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Initialize localization
        init_localization()
        
        # Get application name and version
        self.app_name = get_text("app_name")  # Use localized app name
        self.app_version = get_app_version()
        
        # Set window title with version
        self.setWindowTitle(f"{self.app_name} v{self.app_version}")
        
        self.setMinimumSize(800, 500)
        
        # Set application window icon using the correct resource path
        icon_path = get_resource_path("resources/icon.png")
        self.setWindowIcon(QIcon(icon_path))
        
        # 添加全局样式表，确保字体一致性
        self.setStyleSheet("""
            QComboBox {
                font-size: 12px;
            }
            QComboBox QAbstractItemView {
                font-size: 12px;
            }
        """)
        
        # 添加托盘图标和控制是否真正退出的标志
        self.really_quit = False
        self.tray_icon = TrayIcon(self)
        
        # 初始化状态管理器 - 在其他组件创建之前初始化
        self.status_manager = StatusManager.instance()
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Add some top margin to improve spacing
        main_layout.setContentsMargins(10, 15, 10, 10)
        
        # Create task manager with improved top spacing
        self.task_manager = TaskManager()
        self.task_manager.task_changed.connect(self.on_task_changed)
        main_layout.addWidget(self.task_manager)
        
        # Task details section with tabs
        self.tabs = QTabWidget()
        
        # Tab 1: RSS Feeds - using FeedManager
        self.feed_manager = FeedManager()
        self.tabs.addTab(self.feed_manager, get_text("rss_feeds"))
        
        # Tab 2: Scheduling - using SchedulerManager
        self.scheduler_manager = SchedulerManager()
        self.scheduler_manager.schedule_updated.connect(self.reload_tasks)
        self.tabs.addTab(self.scheduler_manager, get_text("schedule"))
        
        # Tab 3: Recipients - using RecipientManager
        self.recipient_manager = RecipientManager()
        self.tabs.addTab(self.recipient_manager, get_text("recipients"))
        
        main_layout.addWidget(self.tabs)
        
        # Action buttons section
        buttons_layout = QHBoxLayout()
        
        self.run_now_btn = QPushButton(get_text("run_now"))
        self.settings_btn = QPushButton(get_text("settings"))
        
        self.run_now_btn.clicked.connect(self.run_task_now)
        self.settings_btn.clicked.connect(self.open_settings)
        
        buttons_layout.addWidget(self.run_now_btn)
        buttons_layout.addWidget(self.settings_btn)
        
        main_layout.addLayout(buttons_layout)
        
        # 添加自定义状态栏 (在main_layout.addLayout(buttons_layout)之后)
        self.status_bar = CustomStatusBar()
        self.setStatusBar(self.status_bar)
        
        # --- Remove previous connections ---
        # try:
        #     unsubscribe_handler = get_unsubscribe_handler()
        #     # self.recipient_manager.connect_signals(unsubscribe_handler) # REMOVED
        #     # self.tabs.currentChanged.connect(self.handle_tab_changed) # REMOVED
        #     # logger.info("Connected tab change signal to handle_tab_changed.") # REMOVED
        # except Exception as e:
        #     logger.error(f"Error connecting unsubscribe handler or tab signals: {e}", exc_info=True)
        #
        # try:
        #     unsubscribe_handler = get_unsubscribe_handler()
        #     # unsubscribe_handler.unsubscribe_processed.connect(self.recipient_manager.refresh_for_unsubscribe) # REMOVED
        #     # logger.info("Connected unsubscribe_processed signal to RecipientManager refresh slot.") # REMOVED
        # except Exception as e:
        #     logger.error(f"Failed to connect unsubscribe signal: {e}")
        # --- End Removal ---

        # --- Add new connection for task reload ---
        try:
            unsubscribe_handler = get_unsubscribe_handler()
            unsubscribe_handler.unsubscribe_processed.connect(self._handle_task_updated_by_unsubscribe)
            logger.info("Connected unsubscribe_processed signal to MainWindow._handle_task_updated_by_unsubscribe slot.")
        except Exception as e:
            logger.error(f"Failed to connect unsubscribe_processed signal to MainWindow slot: {e}", exc_info=True)
        # --- End New Connection ---

        # 一定要初始化任务，否则组件不会显示任务信息
        if self.task_manager.current_task:
            self.on_task_changed(self.task_manager.current_task)
        
        # 显示初始状态
        initial_task_id = self.status_manager.create_task("系统状态")
        self.status_manager.update_task(
            initial_task_id,
            status=TaskStatus.COMPLETED,
            message=get_text("ready")
        )
        
        # 打印日志确认主窗口已正确初始化
        logger.info("主窗口初始化完成")
    
    @pyqtSlot(str, str)
    def _handle_task_updated_by_unsubscribe(self, task_id: str, email: str):
        """Slot to handle task updates triggered by the unsubscribe handler."""
        logger.info(f"Received notification that task {task_id} was updated (unsubscribe: {email}). Triggering reload.")
        # Defer the reload slightly to avoid potential conflicts
        QTimer.singleShot(0, lambda: self.task_manager.reload_task(task_id))

    def on_task_changed(self, task):
        """Handle task changes from task manager, deferring UI updates slightly."""
        if not task:
            logger.warning("Received null task object in on_task_changed")
            return

        logger.info(f"Task changed signal received for: {task.name} (ID: {task.task_id}). Scheduling UI update.")
        # Use QTimer.singleShot to defer the update slightly.
        # This allows the QComboBox event handling to complete before updating other widgets.
        QTimer.singleShot(0, lambda t=task: self._update_components_for_task(t))

    def _update_components_for_task(self, task):
        """Updates UI components with the new task data."""
        if not task:
            logger.warning("Attempted to update components with null task in _update_components_for_task")
            return

        logger.info(f"Updating components for task: {task.name} (ID: {task.task_id})")
        try:
            # Update all components with the new task
            self.feed_manager.set_task(task)
            self.scheduler_manager.set_task(task)
            self.recipient_manager.set_task(task) # This calls update_recipient_table

            # No need for explicit refresh here, set_task handles it.
            # if self.tabs.currentWidget() == self.recipient_manager:
            #     logger.debug("Recipient tab is active, set_task already updated it.")
        except Exception as e:
            logger.error(f"Error updating components for task {task.name}: {e}", exc_info=True)

    def run_task_now(self):
        """Execute the RSS fetching and processing task immediately"""
        task = self.task_manager.get_current_task()
        if not task:
            QMessageBox.warning(self, get_text("no_task"), get_text("no_task_selected"))
            return
        
        # 更新按钮状态，防止重复点击
        self.run_now_btn.setEnabled(False)
        self.run_now_btn.setText(get_text("running"))
        
        # 首先保存最新的任务状态到配置文件
        save_task(task)
        
        # 创建一个初始状态更新，这样即使在任务进入队列前也有状态显示
        status_task_id = self.status_manager.create_task(f"执行任务: {task.name}")
        self.status_manager.update_task(
            status_task_id,
            status=TaskStatus.PENDING,
            message=f"准备执行任务: {task.name}..."
        )
        
        try:
            # 记录任务ID用于调试
            task_id = task.task_id
            print(f"Running task with ID: {task_id}")
            
            # 调用scheduler中的方法立即执行任务
            task_result = run_task_now(task_id)
            
            # 如果返回了状态任务ID，可以用于后续跟踪
            if isinstance(task_result, dict) and 'status_task_id' in task_result:
                status_task_id = task_result['status_task_id']
                print(f"Task queued with status tracking ID: {status_task_id}")
            
            # 使用托盘图标显示非阻塞通知，替代弹窗
            if self.tray_icon and self.tray_icon.isSystemTrayAvailable():
                self.tray_icon.showMessage(
                    get_text("task_started"),
                    f"{get_text('task_started_message')} '{task.name}'",
                    QSystemTrayIcon.MessageIcon.Information,
                    3000  # 显示3秒
                )
            
            # 由于任务在后台线程执行，这里只更新UI状态
            task.update_task_run()
            save_task(task)
            
            # 立即更新调度器UI以显示最新的运行时间和下次运行时间
            self.scheduler_manager.update_scheduler_ui()
            
            # 确保状态栏显示已经开始的任务状态 - 移到这里，避免被弹窗阻断
            self.status_manager.update_task(
                status_task_id,
                status=TaskStatus.RUNNING,
                message=f"正在执行任务: {task.name}...",
                progress=5
            )
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"任务执行错误: {error_details}")
            # 更新状态管理器以显示错误
            self.status_manager.update_task(
                status_task_id,
                status=TaskStatus.FAILED,
                message=f"任务执行失败: {str(e)}",
                error=str(e)
            )
            QMessageBox.critical(self, get_text("task_error"), 
                               f"{get_text('error_starting_task')}: {str(e)}")
        finally:
            # 恢复按钮状态
            self.run_now_btn.setEnabled(True)
            self.run_now_btn.setText(get_text("run_now"))
    
    def reload_tasks(self):
        """重新加载任务调度，响应调度更新信号"""
        print("调度设置已更新，正在重新加载任务...")
        try:
            status = reload_scheduled_tasks()
            # 显示确认消息
            job_count = status.get('active_jobs', 0)
            QMessageBox.information(self, get_text("schedule_updated"), 
                                  f"{get_text('schedule_updated_message')}\n\n"
                                  f"{job_count} {get_text('tasks_scheduled')}")
            
            # 刷新调度管理器的显示
            self.scheduler_manager.update_next_run_display()
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"重新加载任务出错: {error_details}")
            QMessageBox.critical(self, get_text("schedule_error"), 
                              f"{get_text('error_reloading_tasks')}: {str(e)}")
    
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
            QMessageBox.critical(self, get_text("settings_error"), 
                               f"{get_text('error_opening_settings')}: {str(e)}")
    
    def closeEvent(self, event):
        """重写关闭事件，实现最小化到托盘功能"""
        # 检查是否应该最小化到托盘而不是退出
        # Reload settings here to get the current value
        general_settings = get_general_settings()
        minimize_to_tray = general_settings.get("minimize_to_tray", True)  # Default True if missing

        if not self.really_quit and minimize_to_tray and self.tray_icon:
            # 显示气泡提示消息
            self.tray_icon.showMessage(
                "NeuroFeed",
                get_text("app_minimized_to_tray"),
                QSystemTrayIcon.MessageIcon.Information,
                2000  # 显示2秒
            )
            self.hide()  # 隐藏窗口

            # On macOS, hide the dock icon when minimizing to tray
            if platform.system() == 'Darwin':
                hide_dock_icon()

            event.ignore()  # 忽略关闭事件
        else:
            # 真正退出
            logger.info("Close event accepted, proceeding with application exit.")
            self.really_quit = True # Ensure flag is set for exit_application
            self.exit_application() # Call the exit method
            event.accept() # Accept the event if quitting

    def exit_application(self):
        """Properly exit the application"""
        import logging
        import platform
        import sys
        from PyQt6.QtCore import QCoreApplication
        
        logger = logging.getLogger(__name__)
        logger.info("Exit application requested")
        
        # Ensure tray icon is hidden/removed before quitting
        if self.tray_icon:
            self.tray_icon.hide()
            # Optionally set to None, though Qt should handle cleanup
            # self.tray_icon = None

        # Try platform-specific exit if available (less common now, Qt handles most)
        # if platform.system() == 'Darwin':
        #     try:
        #         from utils.macos_utils import force_quit_application
        #         if force_quit_application():
        #             return # Exit if platform-specific method succeeded
        #     except ImportError:
        #         pass # Continue with standard Qt exit

        # Force application to quit using Qt's recommended method
        logger.info("Calling QCoreApplication.instance().quit()")
        QCoreApplication.instance().quit()

        # Fallback if quit() doesn't exit immediately (should not be needed often)
        # logger.info("Forcing exit with sys.exit(0)")
        # sys.exit(0)