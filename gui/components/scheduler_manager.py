from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
                           QComboBox, QTimeEdit, QLabel, QPushButton, QGroupBox,
                           QCheckBox, QGridLayout, QSpinBox, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QTime
from core.config_manager import save_task
from datetime import datetime, timedelta

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
        schedule_group = QGroupBox("Schedule Settings")
        self.schedule_layout = QFormLayout(schedule_group)
        
        # 频率设置 - 使用"每X周"的格式
        freq_layout = QHBoxLayout()
        freq_layout.addWidget(QLabel("Every"))
        
        self.weeks_spin = QSpinBox()
        self.weeks_spin.setRange(1, 52)  # 1-52周
        self.weeks_spin.setValue(1)
        self.weeks_spin.setFixedWidth(60)
        freq_layout.addWidget(self.weeks_spin)
        
        freq_layout.addWidget(QLabel("week(s)"))
        freq_layout.addStretch()
        
        self.schedule_layout.addRow("Frequency:", freq_layout)
        
        # 时间选择
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setTime(QTime(8, 0))  # 默认早上8点
        self.schedule_layout.addRow("Time:", self.time_edit)
        
        # 日期选择部分 - 始终可见
        days_group = QGroupBox("Run on these days:")
        days_layout = QVBoxLayout(days_group)
        
        # 快捷按钮行
        preset_layout = QHBoxLayout()
        self.weekday_btn = QPushButton("Weekdays")
        self.weekend_btn = QPushButton("Weekends")
        self.all_days_btn = QPushButton("All Days")
        self.no_days_btn = QPushButton("None")
        
        self.weekday_btn.clicked.connect(self.select_weekdays)
        self.weekend_btn.clicked.connect(self.select_weekends)
        self.all_days_btn.clicked.connect(self.select_all_days)
        self.no_days_btn.clicked.connect(self.select_no_days)
        
        preset_layout.addWidget(self.weekday_btn)
        preset_layout.addWidget(self.weekend_btn)
        preset_layout.addWidget(self.all_days_btn)
        preset_layout.addWidget(self.no_days_btn)
        
        days_layout.addLayout(preset_layout)
        
        # 日期复选框 - 改进布局使其更整齐
        days_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        # 创建一个更整齐的布局容器
        days_container = QWidget()
        days_grid = QGridLayout(days_container)
        days_grid.setContentsMargins(0, 10, 0, 0)  # 增加顶部间距
        days_grid.setHorizontalSpacing(20)  # 增加水平间距
        days_grid.setVerticalSpacing(10)  # 设置垂直间距
        days_grid.setAlignment(Qt.AlignmentFlag.AlignCenter)  # 居中对齐整个网格
        
        self.day_checkboxes = []
        
        # 将星期几放在单行，确保等间距
        for i, day in enumerate(days_names):
            checkbox = QCheckBox(day)
            checkbox.setChecked(True)  # 默认全选
            self.day_checkboxes.append(checkbox)
            
            # 设置固定宽度，确保所有复选框大小一致
            checkbox.setMinimumWidth(80)
            days_grid.addWidget(checkbox, 0, i)
        
        days_layout.addWidget(days_container)
        days_layout.addStretch()
        
        # 添加日期组到主布局
        self.schedule_layout.addRow(days_group)
        
        # 添加调度设置组到主布局
        layout.addWidget(schedule_group)
        
        # Last run information
        self.last_run_label = QLabel("Last run: Never")
        layout.addWidget(self.last_run_label)
        
        # Next run information
        self.next_run_label = QLabel("Next run: Not scheduled")
        layout.addWidget(self.next_run_label)
        
        # Control buttons
        buttons_layout = QHBoxLayout()
        self.save_schedule_btn = QPushButton("Save Schedule")
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
        
        # 获取调度信息
        schedule = self.current_task.schedule or {}
        
        # 设置周期
        weeks = schedule.get("weeks", 1)
        self.weeks_spin.setValue(weeks)
        
        # 设置时间
        time_str = schedule.get("time", "08:00")
        try:
            hours, minutes = map(int, time_str.split(":"))
            self.time_edit.setTime(QTime(hours, minutes))
        except (ValueError, AttributeError):
            self.time_edit.setTime(QTime(8, 0))  # 默认早上8点
        
        # 设置选中的天
        days = schedule.get("days", list(range(7)))  # 默认所有天
        for i, checkbox in enumerate(self.day_checkboxes):
            checkbox.setChecked(i in days)
        
        # 更新上次运行信息
        if self.current_task.last_run:
            try:
                last_run_datetime = datetime.fromisoformat(self.current_task.last_run)
                formatted_time = last_run_datetime.strftime("%Y-%m-%d %H:%M:%S")
                self.last_run_label.setText(f"Last run: {formatted_time}")
            except (ValueError, TypeError):
                self.last_run_label.setText("Last run: Unknown format")
        else:
            self.last_run_label.setText("Last run: Never")
        
        # 更新下次运行时间
        self.update_next_run_display()
    
    def update_next_run_display(self):
        """更新下次运行时间显示"""
        if not self.current_task:
            self.next_run_label.setText("Next run: Not scheduled")
            return
            
        try:
            schedule = self.current_task.schedule or {}
            time_str = schedule.get("time", "08:00")
            hours, minutes = map(int, time_str.split(":"))
            weeks = schedule.get("weeks", 1)
            days = schedule.get("days", list(range(7)))  # 默认所有天
            
            if not days:
                self.next_run_label.setText("Next run: No days selected")
                return
            
            now = datetime.now()
            base_time = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
            
            # 计算下一次运行时间 - 找到最近的日期
            current_weekday = now.weekday()  # 0-6, 周一到周日
            
            # 寻找下一个最近的运行日
            next_run = None
            days_until_next_run = float('inf')
            
            # 对于每个启用的日期，计算到下一次运行的天数
            for day in sorted(days):
                # 计算当前周到下一个该日期的天数
                days_diff = (day - current_weekday) % 7
                if days_diff == 0 and base_time <= now:
                    # 如果是今天但时间已过，算作7天后
                    days_diff = 7
                
                # 检查这是否是最近的一天
                if days_diff < days_until_next_run:
                    days_until_next_run = days_diff
                    next_run = base_time + timedelta(days=days_diff)
            
            # 如果配置为多周运行一次
            if weeks > 1:
                # 计算上次运行日期与预期运行周期的关系
                if self.current_task.last_run:
                    last_run = datetime.fromisoformat(self.current_task.last_run)
                    days_since_last_run = (now - last_run).days
                    
                    if days_since_last_run < weeks * 7:
                        # 如果距离上次运行未满配置的周数，调整下次运行时间
                        days_to_add = weeks * 7 - days_since_last_run
                        adjusted_run = next_run + timedelta(days=days_to_add)
                        
                        # 更新为调整后的运行时间
                        next_run = adjusted_run
            
            # 格式化显示
            formatted_time = next_run.strftime("%Y-%m-%d %H:%M:%S")
            time_diff = next_run - now
            
            days = time_diff.days
            hours = time_diff.seconds // 3600
            minutes = (time_diff.seconds % 3600) // 60
            
            # 添加倒计时信息
            if days > 0:
                time_format = f"{days} days, {hours} hours, {minutes} minutes from now"
            elif hours > 0:
                time_format = f"{hours} hours, {minutes} minutes from now"
            else:
                time_format = f"{minutes} minutes from now"
                
            self.next_run_label.setText(f"Next run: {formatted_time} ({time_format})")
        except Exception as e:
            import traceback
            print(f"计算下次运行时间出错: {str(e)}")
            print(traceback.format_exc())
            self.next_run_label.setText("Next run: Error calculating next run time")
    
    def save_schedule(self):
        """Save the schedule settings to the current task"""
        if not self.current_task:
            return
        
        # 获取周期
        weeks = self.weeks_spin.value()
        
        # 获取时间
        time_str = self.time_edit.time().toString("HH:mm")
        
        # 获取选中的天
        selected_days = []
        for i, checkbox in enumerate(self.day_checkboxes):
            if checkbox.isChecked():
                selected_days.append(i)
        
        # 警告用户如果没有选择任何天
        if not selected_days:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("No Days Selected")
            msg.setText("You haven't selected any days for this task.")
            msg.setInformativeText("The task will not run automatically. Is this what you want?")
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg.setDefaultButton(QMessageBox.StandardButton.No)
            
            if msg.exec() == QMessageBox.StandardButton.No:
                return  # 用户取消，不保存
            
            print("用户确认不选择任何天，任务将不会自动运行")
        
        # 创建调度字典
        schedule = {
            "weeks": weeks,
            "time": time_str,
            "days": selected_days
        }
        
        # 更新任务并保存
        self.current_task.schedule = schedule
        save_task(self.current_task)
        
        # 更新下次运行时间显示
        self.update_next_run_display()
        
        # 发出信号
        self.schedule_updated.emit()
    
    def update_after_run(self):
        """在任务运行结束后更新显示"""
        if not self.current_task:
            return
            
        # 更新Last Run显示
        if self.current_task.last_run:
            try:
                last_run_datetime = datetime.fromisoformat(self.current_task.last_run)
                formatted_time = last_run_datetime.strftime("%Y-%m-%d %H:%M:%S")
                self.last_run_label.setText(f"Last run: {formatted_time}")
            except (ValueError, TypeError):
                self.last_run_label.setText("Last run: Unknown format")
        else:
            self.last_run_label.setText("Last run: Never")
        
        # 更新Next Run显示
        self.update_next_run_display()
