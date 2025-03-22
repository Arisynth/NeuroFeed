from PyQt6.QtWidgets import (QMainWindow, QLabel, QVBoxLayout, QHBoxLayout, 
                            QListWidget, QPushButton, QWidget, QInputDialog, 
                            QMessageBox, QDialog, QComboBox, QFormLayout,
                            QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from core.config_manager import load_config, save_config, get_tasks, save_task, delete_task
from core.task_model import Task
from datetime import datetime

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
        
        # RSS feed table with status
        self.feed_table = QTableWidget(0, 3)  # Rows will be added dynamically, 3 columns
        self.feed_table.setHorizontalHeaderLabels(["Feed URL", "Status", "Last Fetch Time"])
        self.feed_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.feed_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.feed_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        
        # Feed control buttons
        feed_controls_layout = QHBoxLayout()
        self.add_feed_btn = QPushButton("Add Feed")
        self.remove_feed_btn = QPushButton("Remove Feed")
        self.test_feed_btn = QPushButton("Test Feed")  # Added test feed button
        
        self.add_feed_btn.clicked.connect(self.add_feed)
        self.remove_feed_btn.clicked.connect(self.remove_feed)
        self.test_feed_btn.clicked.connect(self.test_feed)
        
        feed_controls_layout.addWidget(self.add_feed_btn)
        feed_controls_layout.addWidget(self.remove_feed_btn)
        feed_controls_layout.addWidget(self.test_feed_btn)
        feed_controls_layout.addStretch()
        
        feeds_layout.addWidget(self.feed_table)
        feeds_layout.addLayout(feed_controls_layout)
        
        # Tab 2: Scheduling (placeholder)
        self.schedule_tab = QWidget()
        schedule_layout = QVBoxLayout(self.schedule_tab)
        schedule_layout.addWidget(QLabel("Schedule settings will be implemented here"))
        
        # Tab 3: Recipients
        self.recipients_tab = QWidget()
        recipients_layout = QVBoxLayout(self.recipients_tab)
        
        recipient_section_label = QLabel("Email Recipients:")
        recipient_section_label.setStyleSheet("font-weight: bold;")
        recipients_layout.addWidget(recipient_section_label)
        
        # Recipients table with status
        self.recipient_table = QTableWidget(0, 3)  # Rows will be added dynamically, 3 columns
        self.recipient_table.setHorizontalHeaderLabels(["Email Address", "Status", "Last Sent Time"])
        self.recipient_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.recipient_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.recipient_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        
        # Recipient control buttons
        recipient_controls_layout = QHBoxLayout()
        self.add_recipient_btn = QPushButton("Add Recipient")
        self.remove_recipient_btn = QPushButton("Remove Recipient")
        self.test_recipient_btn = QPushButton("Test Email")  # Added test email button
        
        self.add_recipient_btn.clicked.connect(self.add_recipient)
        self.remove_recipient_btn.clicked.connect(self.remove_recipient)
        self.test_recipient_btn.clicked.connect(self.test_recipient)
        
        recipient_controls_layout.addWidget(self.add_recipient_btn)
        recipient_controls_layout.addWidget(self.remove_recipient_btn)
        recipient_controls_layout.addWidget(self.test_recipient_btn)
        recipient_controls_layout.addStretch()
        
        recipients_layout.addWidget(self.recipient_table)
        recipients_layout.addLayout(recipient_controls_layout)
        
        # Add tabs to tab widget
        self.tabs.addTab(self.feeds_tab, "RSS Feeds")
        self.tabs.addTab(self.schedule_tab, "Schedule")
        self.tabs.addTab(self.recipients_tab, "Recipients")
        
        main_layout.addWidget(self.tabs)
        
        # Last run status
        self.last_run_label = QLabel("Last run: Never")
        main_layout.addWidget(self.last_run_label)
        
        # Action buttons section
        buttons_layout = QHBoxLayout()
        
        self.run_now_btn = QPushButton("Run Now")
        self.settings_btn = QPushButton("Settings")
        
        self.run_now_btn.clicked.connect(self.run_task_now)
        self.settings_btn.clicked.connect(self.open_settings)
        
        buttons_layout.addWidget(self.run_now_btn)
        buttons_layout.addWidget(self.settings_btn)
        
        main_layout.addLayout(buttons_layout)
        
        # Update UI with current task
        self.update_ui_from_task()
    
    def update_task_list(self):
        """Update the task selector dropdown"""
        self.task_selector.clear()
        for task in self.tasks:
            self.task_selector.addItem(task.name, task.task_id)
    
    def on_task_changed(self, index):
        """Handle task selection change"""
        if index >= 0 and index < len(self.tasks):
            self.current_task = self.tasks[index]
            self.update_ui_from_task()
    
    def update_ui_from_task(self):
        """Update all UI elements from the current task"""
        if not self.current_task:
            return
            
        # Update feed table
        self.update_feed_table()
        
        # Update recipient table
        self.update_recipient_table()
        
        # Update last run label
        if self.current_task.last_run:
            try:
                last_run_datetime = datetime.fromisoformat(self.current_task.last_run)
                formatted_time = last_run_datetime.strftime("%Y-%m-%d %H:%M:%S")
                self.last_run_label.setText(f"Last run: {formatted_time}")
            except (ValueError, TypeError):
                self.last_run_label.setText("Last run: Unknown format")
        else:
            self.last_run_label.setText("Last run: Never")
    
    def update_feed_table(self):
        """Update the RSS feed table with current task's feeds and their status"""
        if not self.current_task:
            return
            
        self.feed_table.setRowCount(0)  # Clear existing rows
        
        for row, feed_url in enumerate(self.current_task.rss_feeds):
            self.feed_table.insertRow(row)
            
            # Feed URL
            url_item = QTableWidgetItem(feed_url)
            self.feed_table.setItem(row, 0, url_item)
            
            # Status
            status_info = self.current_task.feeds_status.get(feed_url, {})
            status = status_info.get("status", "unknown")
            status_item = QTableWidgetItem(status)
            
            # Set color based on status
            if status == "success":
                status_item.setForeground(QColor("green"))
            elif status == "fail":
                status_item.setForeground(QColor("red"))
                
            self.feed_table.setItem(row, 1, status_item)
            
            # Last fetch time
            last_fetch = status_info.get("last_fetch", "Never")
            if last_fetch != "Never":
                try:
                    fetch_datetime = datetime.fromisoformat(last_fetch)
                    last_fetch = fetch_datetime.strftime("%Y-%m-%d %H:%M:%S")
                except (ValueError, TypeError):
                    last_fetch = "Invalid format"
                    
            time_item = QTableWidgetItem(last_fetch)
            self.feed_table.setItem(row, 2, time_item)
    
    def update_recipient_table(self):
        """Update the recipients table with current task's recipients and their status"""
        if not self.current_task:
            return
            
        self.recipient_table.setRowCount(0)  # Clear existing rows
        
        for row, email in enumerate(self.current_task.recipients):
            self.recipient_table.insertRow(row)
            
            # Email address
            email_item = QTableWidgetItem(email)
            self.recipient_table.setItem(row, 0, email_item)
            
            # Status
            status_info = self.current_task.recipients_status.get(email, {})
            status = status_info.get("status", "unknown")
            status_item = QTableWidgetItem(status)
            
            # Set color based on status
            if status == "success":
                status_item.setForeground(QColor("green"))
            elif status == "fail":
                status_item.setForeground(QColor("red"))
                
            self.recipient_table.setItem(row, 1, status_item)
            
            # Last sent time
            last_sent = status_info.get("last_sent", "Never")
            if last_sent != "Never":
                try:
                    sent_datetime = datetime.fromisoformat(last_sent)
                    last_sent = sent_datetime.strftime("%Y-%m-%d %H:%M:%S")
                except (ValueError, TypeError):
                    last_sent = "Invalid format"
                    
            time_item = QTableWidgetItem(last_sent)
            self.recipient_table.setItem(row, 2, time_item)
    
    def add_feed(self):
        """Add a new RSS feed to the current task"""
        if not self.current_task:
            return
            
        feed_url, ok = QInputDialog.getText(self, "Add RSS Feed", 
                                           "Enter RSS feed URL:")
        if ok and feed_url:
            self.current_task.rss_feeds.append(feed_url)
            save_task(self.current_task)
            self.update_feed_table()
    
    def remove_feed(self):
        """Remove selected RSS feed from the current task"""
        if not self.current_task:
            return
            
        current_row = self.feed_table.currentRow()
        if current_row >= 0:
            del self.current_task.rss_feeds[current_row]
            save_task(self.current_task)
            self.update_feed_table()
    
    def test_feed(self):
        """Test the selected RSS feed"""
        if not self.current_task:
            return
            
        current_row = self.feed_table.currentRow()
        if current_row >= 0:
            feed_url = self.current_task.rss_feeds[current_row]
            
            # TODO: Implement actual RSS feed testing
            # For now, just simulate success/failure randomly
            import random
            status = "success" if random.random() > 0.3 else "fail"
            
            self.current_task.update_feed_status(feed_url, status)
            save_task(self.current_task)
            self.update_feed_table()
            
            if status == "success":
                QMessageBox.information(self, "Feed Test", f"Successfully fetched feed: {feed_url}")
            else:
                QMessageBox.warning(self, "Feed Test", f"Failed to fetch feed: {feed_url}")
    
    def add_recipient(self):
        """Add a new email recipient to the current task"""
        if not self.current_task:
            return
            
        email, ok = QInputDialog.getText(self, "Add Recipient", 
                                        "Enter email address:")
        if ok and email:
            self.current_task.recipients.append(email)
            save_task(self.current_task)
            self.update_recipient_table()
    
    def remove_recipient(self):
        """Remove selected email recipient from the current task"""
        if not self.current_task:
            return
            
        current_row = self.recipient_table.currentRow()
        if current_row >= 0:
            del self.current_task.recipients[current_row]
            save_task(self.current_task)
            self.update_recipient_table()
    
    def test_recipient(self):
        """Test sending email to the selected recipient"""
        if not self.current_task:
            return
            
        current_row = self.recipient_table.currentRow()
        if current_row >= 0:
            email = self.current_task.recipients[current_row]
            
            # TODO: Implement actual email sending test
            # For now, just simulate success/failure randomly
            import random
            status = "success" if random.random() > 0.2 else "fail"
            
            self.current_task.update_recipient_status(email, status)
            save_task(self.current_task)
            self.update_recipient_table()
            
            if status == "success":
                QMessageBox.information(self, "Email Test", f"Successfully sent test email to: {email}")
            else:
                QMessageBox.warning(self, "Email Test", f"Failed to send test email to: {email}")
    
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
            
        # TODO: Implement actual task execution
        # For now, just update the last run time
        self.current_task.update_task_run()
        save_task(self.current_task)
        self.update_ui_from_task()
        
        QMessageBox.information(self, "Task Started", 
                               f"The task '{self.current_task.name}' has started. Results will be emailed shortly.")
    
    def open_settings(self):
        """Open the settings window"""
        # TODO: Import and show the settings window
        QMessageBox.information(self, "Settings", 
                               "Global settings window will be implemented soon.")