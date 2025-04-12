from PyQt6.QtWidgets import QStatusBar, QLabel, QPushButton, QHBoxLayout, QWidget, QMessageBox
from PyQt6.QtCore import QTimer, Qt
from core.status_manager import StatusManager
from core.task_status import TaskStatus
from core.localization import get_text
import os

class CustomStatusBar(QStatusBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 创建布局和组件
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(5, 0, 5, 0)
        
        # 状态文本标签
        self.status_label = QLabel("")
        
        # 进度标签
        self.progress_label = QLabel("")
        
        # 日志按钮
        self.log_button = QPushButton(get_text("view_log"))
        self.log_button.setStyleSheet("""
            QPushButton { 
                border: none; 
                color: #3498db; 
                text-decoration: underline;
                background: transparent;
                padding: 3px;
            }
            QPushButton:hover {
                color: #2980b9;
            }
        """)
        self.log_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # 添加到布局
        layout.addWidget(self.status_label, stretch=1)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.log_button)
        
        # 添加到状态栏
        self.addWidget(container, 1)
        
        # 动画计时器
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._update_animation)
        self.animation_dots = 0
        
        # 连接日志按钮
        self.log_button.clicked.connect(self._open_log_file)
        
        # 连接状态管理器 - 使用更安全的实例获取方法
        self.status_manager = StatusManager.instance()
        self.status_manager.status_updated.connect(self.update_status)
    
    def _update_animation(self):
        """更新加载动画"""
        self.animation_dots = (self.animation_dots + 1) % 4
        if hasattr(self, 'current_message'):
            base_message = self.current_message.rstrip('.')
            self.status_label.setText(f"{base_message}{'.' * self.animation_dots}")
    
    def update_status(self, task_state):
        """更新状态显示"""
        self.current_message = task_state.message
        
        # 根据状态处理动画和颜色
        if task_state.status == TaskStatus.RUNNING:
            if not self.animation_timer.isActive():
                self.animation_timer.start(500)
            self.status_label.setStyleSheet("color: #2980b9;")  # 蓝色表示运行中
            self.progress_label.setStyleSheet("color: #2980b9; font-weight: bold;")
        elif task_state.status == TaskStatus.COMPLETED:
            self.animation_timer.stop()
            self.status_label.setStyleSheet("color: #27ae60;")  # 绿色表示完成
        elif task_state.status == TaskStatus.FAILED:
            self.animation_timer.stop()
            self.status_label.setStyleSheet("color: #c0392b;")  # 红色表示失败
        else:
            self.animation_timer.stop()
            self.status_label.setStyleSheet("")
            
        # 更新进度
        if task_state.progress > 0:
            self.progress_label.setText(f"{task_state.progress}%")
        else:
            self.progress_label.clear()
            
        # 更新状态文本
        self.status_label.setText(task_state.message)
        
        # 如果任务完成或失败，停止动画
        if task_state.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELED]:
            self.animation_timer.stop()
            self.progress_label.clear()
    
    def _open_log_file(self):
        """打开最新的日志文件"""
        log_file = self.status_manager.get_latest_log_file()
        if not log_file:
            QMessageBox.information(
                self.parent(),
                get_text("info"),
                get_text("no_log_file")
            )
            return
            
        if not log_file.exists():
            QMessageBox.warning(
                self.parent(),
                get_text("error"),
                get_text("log_file_not_found")
            )
            return
            
        import sys
        import subprocess
        
        try:
            if sys.platform == 'darwin':  # macOS
                subprocess.run(['open', str(log_file)])
            elif sys.platform == 'win32':  # Windows
                subprocess.run(['start', str(log_file)], shell=True)
            else:  # Linux
                subprocess.run(['xdg-open', str(log_file)])
        except Exception as e:
            QMessageBox.warning(
                self.parent(),
                get_text("error"),
                f"{get_text('error_opening_log')}: {str(e)}"
            )
