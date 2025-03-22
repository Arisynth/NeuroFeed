from PyQt6.QtWidgets import (QMainWindow, QLabel, QVBoxLayout, QHBoxLayout, 
                            QListWidget, QPushButton, QWidget, QInputDialog, 
                            QMessageBox, QDialog, QComboBox, QFormLayout,
                            QTabWidget)
from PyQt6.QtCore import Qt
from core.config_manager import load_config, save_config, get_tasks, save_task, delete_task
from core.task_model import Task

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NewsDigest")
        self.setMinimumSize(800, 500)
        
        # Load tasks from config
        self.tasks = get_tasks()
        self.current_task = None
        if self.tasks:
            self.current_task = self.tasks[0]
        else:
            # Create default task if none exists
            self.current_task = Task(name="Default Task")
            save_task(self.current_task)
            self.tasks = [self.current_task]
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Add title label
        title_label = QLabel("NewsDigest - RSS Feed Aggregator")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 15px;")
        main_layout.addWidget(title_label)
        
        # Task selection section
        task_selection_layout = QHBoxLayout()
        task_selection_layout.addWidget(QLabel("Select Task:"))
        
        self.task_selector = QComboBox()
        self.update_task_list()
        self.task_selector.currentIndexChanged.connect(self.on_task_changed)
        task_selection_layout.addWidget(self.task_selector, 1)
        
        self.add_task_btn = QPushButton("Add Task")
        self.edit_task_btn = QPushButton("Edit Task")
        self.delete_task_btn = QPushButton("Delete Task")
        
        self.add_task_btn.clicked.connect(self.add_task)
        self.edit_task_btn.clicked.connect(self.edit_task)
        self.delete_task_btn.clicked.connect(self.delete_task)
        
        task_selection_layout.addWidget(self.add_task_btn)
        task_selection_layout.addWidget(self.edit_task_btn)
        task_selection_layout.addWidget(self.delete_task_btn)
        
        main_layout.addLayout(task_selection_layout)
        
        # Task details section with tabs
        self.tabs = QTabWidget()
        
        # Tab 1: RSS Feeds
        self.feeds_tab = QWidget()
        feeds_layout = QVBoxLayout(self.feeds_tab)
        
        feed_section_label = QLabel("RSS Feeds for this Task:")
        feed_section_label.setStyleSheet("font-weight: bold;")
        feeds_layout.addWidget(feed_section_label)
        
        # RSS feed list with add/remove buttons
        feed_list_layout = QHBoxLayout()
        
        # RSS List
        self.feed_list = QListWidget()
        self.update_feed_list()
        feed_list_layout.addWidget(self.feed_list, 3)
        
        # Feed control buttons
        feed_buttons_layout = QVBoxLayout()
        self.add_feed_btn = QPushButton("Add Feed")
        self.remove_feed_btn = QPushButton("Remove Feed")
        
        self.add_feed_btn.clicked.connect(self.add_feed)
        self.remove_feed_btn.clicked.connect(self.remove_feed)
        
        feed_buttons_layout.addWidget(self.add_feed_btn)
        feed_buttons_layout.addWidget(self.remove_feed_btn)
        feed_buttons_layout.addStretch()
        
        feed_list_layout.addLayout(feed_buttons_layout, 1)
        feeds_layout.addLayout(feed_list_layout)
        
        # Tab 2: Scheduling (placeholder)
        self.schedule_tab = QWidget()
        schedule_layout = QVBoxLayout(self.schedule_tab)
        schedule_layout.addWidget(QLabel("Schedule settings will be implemented here"))
        
        # Tab 3: Recipients (placeholder)
        self.recipients_tab = QWidget()
        recipients_layout = QVBoxLayout(self.recipients_tab)
        recipients_layout.addWidget(QLabel("Email recipients will be configured here"))
        
        # Add tabs to tab widget
        self.tabs.addTab(self.feeds_tab, "RSS Feeds")
        self.tabs.addTab(self.schedule_tab, "Schedule")
        self.tabs.addTab(self.recipients_tab, "Recipients")
        
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
    
    def update_task_list(self):
        """Update the task selector dropdown"""
        self.task_selector.clear()
        for task in self.tasks:
            self.task_selector.addItem(task.name, task.task_id)
    
    def on_task_changed(self, index):
        """Handle task selection change"""
        if index >= 0 and index < len(self.tasks):
            self.current_task = self.tasks[index]
            self.update_feed_list()
    
    def update_feed_list(self):
        """Update the RSS feed list with current task's feeds"""
        if not self.current_task:
            return
            
        self.feed_list.clear()
        for feed in self.current_task.rss_feeds:
            self.feed_list.addItem(feed)
    
    def add_feed(self):
        """Add a new RSS feed to the current task"""
        if not self.current_task:
            return
            
        feed_url, ok = QInputDialog.getText(self, "Add RSS Feed", 
                                           "Enter RSS feed URL:")
        if ok and feed_url:
            self.current_task.rss_feeds.append(feed_url)
            self.update_feed_list()
            save_task(self.current_task)
    
    def remove_feed(self):
        """Remove selected RSS feed from the current task"""
        if not self.current_task:
            return
            
        current_row = self.feed_list.currentRow()
        if current_row >= 0:
            del self.current_task.rss_feeds[current_row]
            self.update_feed_list()
            save_task(self.current_task)
    
    def add_task(self):
        """Add a new task"""
        task_name, ok = QInputDialog.getText(self, "Add Task", 
                                           "Enter task name:")
        if ok and task_name:
            new_task = Task(name=task_name)
            save_task(new_task)
            
            # Refresh tasks list
            self.tasks = get_tasks()
            self.update_task_list()
            
            # Select the new task
            self.task_selector.setCurrentIndex(len(self.tasks) - 1)
    
    def edit_task(self):
        """Edit the current task name"""
        if not self.current_task:
            return
            
        task_name, ok = QInputDialog.getText(self, "Edit Task", 
                                           "Enter new task name:", 
                                           text=self.current_task.name)
        if ok and task_name:
            self.current_task.name = task_name
            save_task(self.current_task)
            
            # Refresh the task list
            self.tasks = get_tasks()
            current_index = self.task_selector.currentIndex()
            self.update_task_list()
            self.task_selector.setCurrentIndex(current_index)
    
    def delete_task(self):
        """Delete the current task"""
        if not self.current_task or len(self.tasks) <= 1:
            QMessageBox.warning(self, "Cannot Delete", 
                              "Cannot delete the only task. At least one task must exist.")
            return
            
        reply = QMessageBox.question(self, "Confirm Delete", 
                                   f"Are you sure you want to delete task '{self.current_task.name}'?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                                   
        if reply == QMessageBox.StandardButton.Yes:
            current_index = self.task_selector.currentIndex()
            delete_task(self.current_task.task_id)
            
            # Refresh tasks and select another one
            self.tasks = get_tasks()
            self.update_task_list()
            self.task_selector.setCurrentIndex(max(0, current_index - 1))
    
    def run_task_now(self):
        """Execute the RSS fetching and processing task immediately"""
        if not self.current_task:
            return
            
        QMessageBox.information(self, "Task Started", 
                               f"The task '{self.current_task.name}' has started. Results will be emailed shortly.")
        # TODO: Implement actual task execution
    
    def open_settings(self):
        """Open the settings window"""
        # TODO: Import and show the settings window
        QMessageBox.information(self, "Settings", 
                               "Global settings window will be implemented soon.")