from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                           QTableWidgetItem, QHeaderView, QPushButton, QLabel,
                           QMessageBox, QInputDialog)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor
from datetime import datetime
from core.localization import get_text, get_formatted
from core.unsubscribe_handler import UnsubscribeHandler
import logging

# Logger setup
logger = logging.getLogger(__name__)

class RecipientManager(QWidget):
    """Manages email recipients for a task"""
    
    recipient_updated = pyqtSignal()  # Signal emitted when recipients are modified
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_task = None
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the UI components"""
        layout = QVBoxLayout(self)
        
        # Recipient section header
        recipient_section_label = QLabel(get_text("email_recipients") + ":")
        recipient_section_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(recipient_section_label)
        
        # Recipient table
        self.recipient_table = QTableWidget(0, 3)  # Email, Status, Last Sent
        self.recipient_table.setHorizontalHeaderLabels([
            get_text("email_address"),
            get_text("status"),
            get_text("last_sent_time")
        ])
        self.recipient_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.recipient_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.recipient_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.recipient_table)
        
        # Recipient controls
        controls_layout = QHBoxLayout()
        self.add_recipient_btn = QPushButton(get_text("add_recipient"))
        self.remove_recipient_btn = QPushButton(get_text("remove_recipient"))
        self.test_recipient_btn = QPushButton(get_text("test_email"))
        
        self.add_recipient_btn.clicked.connect(self.add_recipient)
        self.remove_recipient_btn.clicked.connect(self.remove_recipient)
        self.test_recipient_btn.clicked.connect(self.test_recipient)
        
        controls_layout.addWidget(self.add_recipient_btn)
        controls_layout.addWidget(self.remove_recipient_btn)
        controls_layout.addWidget(self.test_recipient_btn)
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
    
    def set_task(self, task):
        """Set the current task and update the UI"""
        self.current_task = task
        self.update_recipient_table()
    
    def update_recipient_table(self):
        """Update the recipient table with the current task's recipients"""
        if not self.current_task:
            self.recipient_table.setRowCount(0) # Clear if no task
            return
        
        self.recipient_table.setRowCount(0)  # Clear the table
        
        for row, email in enumerate(self.current_task.recipients):
            self.recipient_table.insertRow(row)
            
            # Email address
            email_item = QTableWidgetItem(email)
            email_item.setFlags(email_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.recipient_table.setItem(row, 0, email_item)
            
            # Status
            status_info = self.current_task.recipients_status.get(email, {})
            status = status_info.get("status", "unknown")
            status_item = QTableWidgetItem(status)
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            # Set color based on status
            if status == "success":
                status_item.setForeground(QColor("green"))
            elif status == "fail":
                status_item.setForeground(QColor("red"))
            
            self.recipient_table.setItem(row, 1, status_item)
            
            # Last sent time
            last_sent = status_info.get("last_sent", get_text("never"))
            if last_sent != get_text("never"):
                try:
                    sent_datetime = datetime.fromisoformat(last_sent)
                    last_sent = sent_datetime.strftime("%Y-%m-%d %H:%M:%S")
                except (ValueError, TypeError):
                    last_sent = get_text("invalid_format")
            
            time_item = QTableWidgetItem(last_sent)
            time_item.setFlags(time_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.recipient_table.setItem(row, 2, time_item)
    
    def add_recipient(self):
        """Add a new recipient to the current task"""
        if not self.current_task:
            return
        
        email, ok = QInputDialog.getText(
            self, 
            get_text("add_recipient"),
            get_text("enter_email_address")
        )
        if ok and email:
            self.current_task.recipients.append(email)
            from core.config_manager import save_task
            save_task(self.current_task)
            self.update_recipient_table()
            self.recipient_updated.emit()
    
    def remove_recipient(self):
        """Remove the selected recipient"""
        if not self.current_task:
            return
        
        current_row = self.recipient_table.currentRow()
        if current_row >= 0:
            del self.current_task.recipients[current_row]
            from core.config_manager import save_task
            save_task(self.current_task)
            self.update_recipient_table()
            self.recipient_updated.emit()
    
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
            from core.config_manager import save_task
            save_task(self.current_task)
            self.update_recipient_table()
            
            if status == "success":
                QMessageBox.information(
                    self,
                    get_text("email_test"),
                    get_text("test_email_success").format(email)
                )
            else:
                QMessageBox.warning(
                    self,
                    get_text("email_test"),
                    get_text("test_email_failed").format(email)
                )

    def connect_signals(self, unsubscribe_handler: UnsubscribeHandler):
         """Connects signals from the unsubscribe handler."""
         unsubscribe_handler.unsubscribe_processed.connect(self.handle_unsubscribe)
         logger.info("RecipientManager connected to UnsubscribeHandler signals.")

    def handle_unsubscribe(self, task_id: str, unsubscribed_email: str):
        """Slot to handle the unsubscribe signal, logs only."""
        # This slot is now primarily for logging or potential future real-time actions.
        # The actual UI refresh happens when the tab is selected.
        if self.current_task and self.current_task.task_id == task_id:
            logger.info(get_formatted("recipient_unsubscribed_log_only", unsubscribed_email, task_id))
        else:
             logger.debug(f"RecipientManager: Received unsubscribe signal for non-current task {task_id}. Logging only.")

    def refresh_recipients(self):
        """Refreshes the recipient list display."""
        logger.debug(f"Refreshing recipient table for task: {self.current_task.name if self.current_task else 'None'}")
        self.update_recipient_table()

    @pyqtSlot(str, str)
    def refresh_for_unsubscribe(self, task_id: str, email: str):
        """Slot to refresh the recipient list if the unsubscribe affects the current task."""
        logger.info(f"RecipientManager received unsubscribe signal for task {task_id}, email {email}")
        if self.current_task and self.current_task.task_id == task_id:
            logger.info(f"Unsubscribe affects current task ({task_id}). Refreshing recipient list.")
            self.update_recipient_table()
        else:
            logger.info(f"Unsubscribe does not affect current task ({self.current_task.task_id if self.current_task else 'None'}). No UI refresh needed now.")
