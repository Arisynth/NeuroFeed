from PyQt6.QtWidgets import QStatusBar, QLabel, QPushButton, QHBoxLayout, QWidget, QMessageBox
from PyQt6.QtCore import QTimer, Qt, QCoreApplication
from core.status_manager import StatusManager
from core.task_status import TaskStatus
from core.localization import get_text
import os
import logging

logger = logging.getLogger(__name__)

class CustomStatusBar(QStatusBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create layout and components
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(5, 0, 5, 0)
        
        # Status text label
        self.status_label = QLabel("")
        
        # Progress label
        self.progress_label = QLabel("")
        
        # Log button
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
        
        # Add to layout
        layout.addWidget(self.status_label, stretch=1)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.log_button)
        
        # Add to status bar
        self.addWidget(container, 1)
        
        # Animation timer
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._update_animation)
        self.animation_dots = 0
        
        # Connect log button
        self.log_button.clicked.connect(self._open_log_file)
        
        # Don't immediately connect to status_manager to prevent Qt metaclass recursion
        # Use a delayed connection via QTimer
        self.status_manager = None
        QTimer.singleShot(100, self._initialize_status_manager)
    
    def _initialize_status_manager(self):
        """Initialize the status manager with a delay to avoid recursion issues"""
        try:
            # Get the instance without creating a new one if possible
            self.status_manager = StatusManager.instance()
            self.status_manager.status_updated.connect(self.update_status)
            logger.info("Successfully connected to status manager signals")
        except Exception as e:
            logger.error(f"Error connecting to status_manager signals: {e}")
    
    def _update_animation(self):
        """Update loading animation"""
        self.animation_dots = (self.animation_dots + 1) % 4
        if hasattr(self, 'current_message'):
            base_message = self.current_message.rstrip('.')
            self.status_label.setText(f"{base_message}{'.' * self.animation_dots}")
    
    def update_status(self, task_state):
        """Update status display"""
        self.current_message = task_state.message
        
        # Handle animation and colors based on status
        if task_state.status == TaskStatus.RUNNING:
            if not self.animation_timer.isActive():
                self.animation_timer.start(500)
            self.status_label.setStyleSheet("color: #2980b9;")  # Blue for running
            self.progress_label.setStyleSheet("color: #2980b9; font-weight: bold;")
        elif task_state.status == TaskStatus.COMPLETED:
            self.animation_timer.stop()
            self.status_label.setStyleSheet("color: #27ae60;")  # Green for completion
        elif task_state.status == TaskStatus.FAILED:
            self.animation_timer.stop()
            self.status_label.setStyleSheet("color: #c0392b;")  # Red for failure
        else:
            self.animation_timer.stop()
            self.status_label.setStyleSheet("")
            
        # Update progress
        if task_state.progress > 0:
            self.progress_label.setText(f"{task_state.progress}%")
        else:
            self.progress_label.clear()
            
        # Update status text
        self.status_label.setText(task_state.message)
        
        # If task is complete or failed, stop animation
        if task_state.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELED]:
            self.animation_timer.stop()
            self.progress_label.clear()
    
    def _open_log_file(self):
        """Open the latest log file"""
        if not self.status_manager:
            QMessageBox.warning(
                self.parent(),
                get_text("error"),
                "Status manager not initialized"
            )
            return
            
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
    
    def handle_exit_action(self):
        """Handle exit action from menu or dock"""
        logger.info("Exit action triggered")
        # Use QCoreApplication to ensure proper application quit
        QCoreApplication.instance().quit()
