from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
                           QComboBox, QTimeEdit, QLabel, QPushButton, QGroupBox,
                           QCheckBox, QGridLayout, QSpinBox, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QTime
from core.config_manager import save_task
from datetime import datetime, timedelta
from core.localization import get_text, get_formatted

class SchedulerManager(QWidget):
    """Manages scheduling settings for a task"""
    
    schedule_updated = pyqtSignal()  # Signal emitted when schedule is modified
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_task = None
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the UI components"""
        layout = QVBoxLayout(self)
        
        # Schedule settings group
        schedule_group = QGroupBox(get_text("schedule_group"))
        self.schedule_layout = QFormLayout(schedule_group)
        
        # Frequency settings
        freq_layout = QHBoxLayout()
        freq_layout.addWidget(QLabel(get_text("every")))
        
        self.weeks_spin = QSpinBox()
        self.weeks_spin.setRange(1, 52)  # 1-52 weeks
        self.weeks_spin.setValue(1)
        self.weeks_spin.setFixedWidth(60)
        freq_layout.addWidget(self.weeks_spin)
        
        freq_layout.addWidget(QLabel(get_text("weeks")))
        freq_layout.addStretch()
        
        self.schedule_layout.addRow(f"{get_text('frequency')}:", freq_layout)
        
        # Time selection
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setTime(QTime(8, 0))  # Default 8:00 AM
        self.schedule_layout.addRow(f"{get_text('time')}:", self.time_edit)
        
        # Days selection
        days_group = QGroupBox(get_text("run_on_days"))
        days_layout = QVBoxLayout(days_group)
        
        # Quick selection buttons
        preset_layout = QHBoxLayout()
        self.weekday_btn = QPushButton(get_text("weekdays_btn"))
        self.weekend_btn = QPushButton(get_text("weekends_btn"))
        self.all_days_btn = QPushButton(get_text("all_days_btn"))
        self.no_days_btn = QPushButton(get_text("no_days_btn"))
        
        self.weekday_btn.clicked.connect(self.select_weekdays)
        self.weekend_btn.clicked.connect(self.select_weekends)
        self.all_days_btn.clicked.connect(self.select_all_days)
        self.no_days_btn.clicked.connect(self.select_no_days)
        
        preset_layout.addWidget(self.weekday_btn)
        preset_layout.addWidget(self.weekend_btn)
        preset_layout.addWidget(self.all_days_btn)
        preset_layout.addWidget(self.no_days_btn)
        
        days_layout.addLayout(preset_layout)
        
        # Days checkboxes
        days_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        
        days_container = QWidget()
        days_grid = QGridLayout(days_container)
        days_grid.setContentsMargins(0, 10, 0, 0)  # Add top margin
        days_grid.setHorizontalSpacing(20)  # Add horizontal spacing
        days_grid.setVerticalSpacing(10)  # Set vertical spacing
        days_grid.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center align the grid
        
        self.day_checkboxes = []
        
        for i, day in enumerate(days_names):
            checkbox = QCheckBox(get_text(day))
            checkbox.setChecked(True)  # Default all selected
            self.day_checkboxes.append(checkbox)
            
            checkbox.setMinimumWidth(80)  # Ensure all checkboxes have the same size
            days_grid.addWidget(checkbox, 0, i)
        
        days_layout.addWidget(days_container)
        days_layout.addStretch()
        
        # Add days group to main layout
        self.schedule_layout.addRow(days_group)
        
        # Add schedule settings group to main layout
        layout.addWidget(schedule_group)
        
        # Last run information
        self.last_run_label = QLabel(get_text("last_run_never"))
        layout.addWidget(self.last_run_label)
        
        # Next run information
        self.next_run_label = QLabel(get_text("next_run_not_scheduled"))
        layout.addWidget(self.next_run_label)
        
        # Control buttons
        buttons_layout = QHBoxLayout()
        self.save_schedule_btn = QPushButton(get_text("save_schedule"))
        self.save_schedule_btn.clicked.connect(self.save_schedule)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.save_schedule_btn)
        
        layout.addLayout(buttons_layout)
        layout.addStretch()
    
    def select_weekdays(self):
        """Select weekdays (Monday to Friday)"""
        for i, checkbox in enumerate(self.day_checkboxes):
            checkbox.setChecked(i < 5)  # Monday-Friday
    
    def select_weekends(self):
        """Select weekends (Saturday, Sunday)"""
        for i, checkbox in enumerate(self.day_checkboxes):
            checkbox.setChecked(i >= 5)  # Saturday-Sunday
    
    def select_all_days(self):
        """Select all days"""
        for checkbox in self.day_checkboxes:
            checkbox.setChecked(True)
    
    def select_no_days(self):
        """Deselect all days"""
        for checkbox in self.day_checkboxes:
            checkbox.setChecked(False)
    
    def set_task(self, task):
        """Set the current task and update the UI"""
        self.current_task = task
        self.update_scheduler_ui()
    
    def update_scheduler_ui(self):
        """Update the UI with the current task's schedule settings"""
        if not self.current_task:
            return
        
        # Get schedule information
        schedule = self.current_task.schedule or {}
        
        # Set frequency
        weeks = schedule.get("weeks", 1)
        self.weeks_spin.setValue(weeks)
        
        # Set time
        time_str = schedule.get("time", "08:00")
        try:
            hours, minutes = map(int, time_str.split(":"))
            self.time_edit.setTime(QTime(hours, minutes))
        except (ValueError, AttributeError):
            self.time_edit.setTime(QTime(8, 0))  # Default 8:00 AM
        
        # Set selected days
        days = schedule.get("days", list(range(7)))  # Default all days
        for i, checkbox in enumerate(self.day_checkboxes):
            checkbox.setChecked(i in days)
        
        # Update last run information
        if self.current_task.last_run:
            try:
                last_run_datetime = datetime.fromisoformat(self.current_task.last_run)
                formatted_time = last_run_datetime.strftime("%Y-%m-%d %H:%M:%S")
                self.last_run_label.setText(get_formatted("last_run_time", formatted_time))
            except (ValueError, TypeError):
                self.last_run_label.setText(get_text("last_run_unknown"))
        else:
            self.last_run_label.setText(get_text("last_run_never"))
        
        # Update next run time
        self.update_next_run_display()
    
    def update_next_run_display(self):
        """Update next run time display"""
        if not self.current_task:
            self.next_run_label.setText(get_text("next_run_not_scheduled"))
            return
            
        try:
            schedule = self.current_task.schedule or {}
            time_str = schedule.get("time", "08:00")
            hours, minutes = map(int, time_str.split(":"))
            weeks = schedule.get("weeks", 1)
            days = schedule.get("days", list(range(7)))  # Default all days
            
            if not days:
                self.next_run_label.setText(get_text("next_run_no_days"))
                return
            
            now = datetime.now()
            base_time = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
            
            # Calculate next run time - find the nearest date
            current_weekday = now.weekday()  # 0-6, Monday to Sunday
            
            # Find the next nearest run day
            next_run = None
            days_until_next_run = float('inf')
            
            for day in sorted(days):
                days_diff = (day - current_weekday) % 7
                if days_diff == 0 and base_time <= now:
                    days_diff = 7
                
                if days_diff < days_until_next_run:
                    days_until_next_run = days_diff
                    next_run = base_time + timedelta(days=days_diff)
            
            if weeks > 1:
                if self.current_task.last_run:
                    last_run = datetime.fromisoformat(self.current_task.last_run)
                    days_since_last_run = (now - last_run).days
                    
                    if days_since_last_run < weeks * 7:
                        days_to_add = weeks * 7 - days_since_last_run
                        adjusted_run = next_run + timedelta(days=days_to_add)
                        next_run = adjusted_run
            
            formatted_time = next_run.strftime("%Y-%m-%d %H:%M:%S")
            time_diff = next_run - now
            
            days = time_diff.days
            hours = time_diff.seconds // 3600
            minutes = (time_diff.seconds % 3600) // 60
            
            if days > 0:
                time_format = get_formatted("time_format_days", days, hours, minutes)
            elif hours > 0:
                time_format = get_formatted("time_format_hours", hours, minutes)
            else:
                time_format = get_formatted("time_format_minutes", minutes)
                
            self.next_run_label.setText(get_formatted("next_run_time", formatted_time, time_format))
        except Exception as e:
            import traceback
            print(f"Error calculating next run time: {str(e)}")
            print(traceback.format_exc())
            self.next_run_label.setText(get_text("next_run_error"))
    
    def save_schedule(self):
        """Save the schedule settings to the current task"""
        if not self.current_task:
            return
        
        weeks = self.weeks_spin.value()
        time_str = self.time_edit.time().toString("HH:mm")
        
        selected_days = []
        for i, checkbox in enumerate(self.day_checkboxes):
            if checkbox.isChecked():
                selected_days.append(i)
        
        if not selected_days:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle(get_text("no_days_selected"))
            msg.setText(get_text("no_days_selected_warning"))
            msg.setInformativeText(get_text("no_days_selected_confirm"))
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg.setDefaultButton(QMessageBox.StandardButton.No)
            
            if msg.exec() == QMessageBox.StandardButton.No:
                return
        
        schedule = {
            "weeks": weeks,
            "time": time_str,
            "days": selected_days
        }
        
        self.current_task.schedule = schedule
        save_task(self.current_task)
        
        self.update_next_run_display()
        self.schedule_updated.emit()
    
    def update_after_run(self):
        """Update display after task run"""
        if not self.current_task:
            return
            
        if self.current_task.last_run:
            try:
                last_run_datetime = datetime.fromisoformat(self.current_task.last_run)
                formatted_time = last_run_datetime.strftime("%Y-%m-%d %H:%M:%S")
                self.last_run_label.setText(get_formatted("last_run_time", formatted_time))
            except (ValueError, TypeError):
                self.last_run_label.setText(get_text("last_run_unknown"))
        else:
            self.last_run_label.setText(get_text("last_run_never"))
        
        self.update_next_run_display()
