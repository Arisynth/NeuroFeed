from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                           QTableWidgetItem, QHeaderView, QPushButton, QLabel,
                           QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon
from gui.dialogs.feed_config_dialog import FeedConfigDialog
from datetime import datetime
from core.localization import get_text

class FeedManager(QWidget):
    """Manages RSS feeds for a task"""
    
    feed_updated = pyqtSignal()  # Signal emitted when feeds are modified
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_task = None
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the UI components"""
        layout = QVBoxLayout(self)
        
        # Feed section header
        feed_section_label = QLabel(get_text("rss_feeds_for_task"))
        feed_section_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(feed_section_label)
        
        # Create container for table and order buttons
        table_container = QHBoxLayout()
        
        # Feed table
        self.feed_table = QTableWidget(0, 5)  # URL, Items Count, Labels, Status, Last Fetch Time
        self.feed_table.setHorizontalHeaderLabels([
            get_text("feed_url"),
            get_text("items"),
            get_text("labels"),
            get_text("status"),
            get_text("last_fetch_time")
        ])
        self.feed_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.feed_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.feed_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.feed_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.feed_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.feed_table.cellDoubleClicked.connect(self.on_feed_double_clicked)
        table_container.addWidget(self.feed_table)
        
        # Add order buttons in vertical layout
        order_buttons = QVBoxLayout()
        
        # Move up button
        self.move_up_btn = QPushButton("▲")
        self.move_up_btn.setToolTip(get_text("move_feed_up"))
        self.move_up_btn.clicked.connect(self.move_feed_up)
        order_buttons.addWidget(self.move_up_btn)
        
        # Move down button
        self.move_down_btn = QPushButton("▼")
        self.move_down_btn.setToolTip(get_text("move_feed_down"))
        self.move_down_btn.clicked.connect(self.move_feed_down)
        order_buttons.addWidget(self.move_down_btn)
        
        # Add spacing
        order_buttons.addStretch()
        
        # Add order buttons to container
        table_container.addLayout(order_buttons)
        
        # Add table container to main layout
        layout.addLayout(table_container)
        
        # Feed controls
        controls_layout = QHBoxLayout()
        self.add_feed_btn = QPushButton(get_text("add_feed"))
        self.edit_feed_btn = QPushButton(get_text("edit_feed"))
        self.remove_feed_btn = QPushButton(get_text("remove_feed"))
        self.test_feed_btn = QPushButton(get_text("test_feed"))
        
        self.add_feed_btn.clicked.connect(self.add_feed)
        self.edit_feed_btn.clicked.connect(self.edit_feed)
        self.remove_feed_btn.clicked.connect(self.remove_feed)
        self.test_feed_btn.clicked.connect(self.test_feed)
        
        controls_layout.addWidget(self.add_feed_btn)
        controls_layout.addWidget(self.edit_feed_btn)
        controls_layout.addWidget(self.remove_feed_btn)
        controls_layout.addWidget(self.test_feed_btn)
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
    
    def set_task(self, task):
        """Set the current task and update the UI"""
        if not task:
            print("FeedManager: 收到空任务对象")
            return
            
        print(f"FeedManager: 设置任务 - {task.name}")
        self.current_task = task
        self.update_feed_table()
    
    def update_feed_table(self):
        """Update the feed table with the current task's feeds"""
        if not self.current_task:
            print("FeedManager: 无法更新Feed表 - 未设置任务")
            return
        
        try:
            print(f"FeedManager: 更新Feed表 - {len(self.current_task.rss_feeds)} 个Feed")
            
            self.feed_table.setRowCount(0)  # Clear the table
            
            for row, feed_url in enumerate(self.current_task.rss_feeds):
                self.feed_table.insertRow(row)
                
                # Feed URL
                url_item = QTableWidgetItem(feed_url)
                url_item.setFlags(url_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.feed_table.setItem(row, 0, url_item)
                
                # Items count
                items_count = self.current_task.get_feed_items_count(feed_url)
                count_item = QTableWidgetItem(str(items_count))
                count_item.setFlags(count_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.feed_table.setItem(row, 1, count_item)
                
                # Labels - 限制显示数量
                labels = self.current_task.get_feed_labels(feed_url)
                labels_text = ""
                if labels:
                    if len(labels) <= 3:
                        labels_text = ", ".join(labels)
                    else:
                        labels_text = ", ".join(labels[:3]) + "..."
                
                labels_item = QTableWidgetItem(labels_text)
                labels_item.setFlags(labels_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.feed_table.setItem(row, 2, labels_item)
                
                # Status
                status_info = self.current_task.feeds_status.get(feed_url, {})
                status = status_info.get("status", "unknown")
                status_item = QTableWidgetItem(status)
                status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                
                # Set color based on status
                if status == "success":
                    status_item.setForeground(QColor("green"))
                elif status == "fail":
                    status_item.setForeground(QColor("red"))
                
                self.feed_table.setItem(row, 3, status_item)
                
                # Last fetch time
                last_fetch = status_info.get("last_fetch", get_text("never"))
                if last_fetch != get_text("never"):
                    try:
                        fetch_datetime = datetime.fromisoformat(last_fetch)
                        last_fetch = fetch_datetime.strftime("%Y-%m-%d %H:%M:%S")
                    except (ValueError, TypeError):
                        last_fetch = "Invalid format"
                
                time_item = QTableWidgetItem(last_fetch)
                time_item.setFlags(time_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.feed_table.setItem(row, 4, time_item)
        except Exception as e:
            import traceback
            print(f"更新Feed表出错: {str(e)}")
            print(traceback.format_exc())
    
    def on_feed_double_clicked(self, row, column):
        """Handle double-click on feed table"""
        self.edit_feed()
    
    def add_feed(self):
        """Add a new feed to the current task"""
        if not self.current_task:
            return
        
        # 获取用户默认标签
        from core.config_manager import load_config
        config = load_config()
        default_labels = config.get("global_settings", {}).get("user_interests", [])
        
        dialog = FeedConfigDialog(self, labels=default_labels)
        if dialog.exec():
            feed_url = dialog.get_feed_url()
            items_count = dialog.get_items_count()
            labels = dialog.get_labels()
            
            if feed_url:
                self.current_task.rss_feeds.append(feed_url)
                self.current_task.set_feed_items_count(feed_url, items_count)
                self.current_task.set_feed_labels(feed_url, labels)
                from core.config_manager import save_task
                save_task(self.current_task)
                self.update_feed_table()
                self.feed_updated.emit()
    
    def edit_feed(self):
        """Edit the selected feed"""
        if not self.current_task:
            return
        
        current_row = self.feed_table.currentRow()
        if current_row >= 0:
            feed_url = self.current_task.rss_feeds[current_row]
            items_count = self.current_task.get_feed_items_count(feed_url)
            labels = self.current_task.get_feed_labels(feed_url)
            
            dialog = FeedConfigDialog(self, feed_url, items_count, labels)
            if dialog.exec():
                new_url = dialog.get_feed_url()
                new_count = dialog.get_items_count()
                new_labels = dialog.get_labels()
                
                # Keep feed status if URL doesn't change
                if new_url != feed_url:
                    self.current_task.rss_feeds[current_row] = new_url
                    
                    # If URL changed, update config with new URL
                    if feed_url in self.current_task.feed_config:
                        config = self.current_task.feed_config.pop(feed_url)
                        self.current_task.feed_config[new_url] = config
                
                # Update items count and labels
                self.current_task.set_feed_items_count(new_url, new_count)
                self.current_task.set_feed_labels(new_url, new_labels)
                from core.config_manager import save_task
                save_task(self.current_task)
                self.update_feed_table()
                self.feed_updated.emit()
    
    def remove_feed(self):
        """Remove the selected feed"""
        if not self.current_task:
            return
        
        current_row = self.feed_table.currentRow()
        if current_row >= 0:
            del self.current_task.rss_feeds[current_row]
            from core.config_manager import save_task
            save_task(self.current_task)
            self.update_feed_table()
            self.feed_updated.emit()
    
    def test_feed(self):
        """Test the selected feed"""
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
            from core.config_manager import save_task
            save_task(self.current_task)
            self.update_feed_table()
            
            if status == "success":
                QMessageBox.information(self, get_text("feed_test"), 
                    get_text("feed_test_success").format(feed_url))
            else:
                QMessageBox.warning(self, get_text("feed_test"), 
                    get_text("feed_test_failed").format(feed_url))
    
    def move_feed_up(self):
        """Move the selected feed up in the list"""
        if not self.current_task:
            return
            
        current_row = self.feed_table.currentRow()
        if current_row > 0:
            # Swap items in the task's rss_feeds list
            self.current_task.rss_feeds[current_row], self.current_task.rss_feeds[current_row-1] = \
                self.current_task.rss_feeds[current_row-1], self.current_task.rss_feeds[current_row]
            
            # Save task to update config.json
            from core.config_manager import save_task
            save_task(self.current_task)
            
            # Update the table display
            self.update_feed_table()
            
            # Keep the moved item selected
            self.feed_table.selectRow(current_row - 1)
            
            # Emit signal that feeds have been updated
            self.feed_updated.emit()
    
    def move_feed_down(self):
        """Move the selected feed down in the list"""
        if not self.current_task:
            return
            
        current_row = self.feed_table.currentRow()
        if current_row >= 0 and current_row < len(self.current_task.rss_feeds) - 1:
            # Swap items in the task's rss_feeds list
            self.current_task.rss_feeds[current_row], self.current_task.rss_feeds[current_row+1] = \
                self.current_task.rss_feeds[current_row+1], self.current_task.rss_feeds[current_row]
            
            # Save task to update config.json
            from core.config_manager import save_task
            save_task(self.current_task)
            
            # Update the table display
            self.update_feed_table()
            
            # Keep the moved item selected
            self.feed_table.selectRow(current_row + 1)
            
            # Emit signal that feeds have been updated
            self.feed_updated.emit()
