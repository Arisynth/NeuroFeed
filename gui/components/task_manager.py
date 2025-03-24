from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox, 
                            QPushButton, QLabel, QInputDialog, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal
from core.config_manager import get_tasks, save_task, delete_task
from core.task_model import Task

class TaskManager(QWidget):
    """Manages tasks selection and basic operations"""
    
    task_changed = pyqtSignal(object)  # Signal emitted when current task changes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tasks = []
        self.current_task = None
        self.setup_ui()
        self.load_tasks()
    
    def setup_ui(self):
        """Setup the UI components"""
        layout = QVBoxLayout(self)
        
        # Task selection section
        task_selection_layout = QHBoxLayout()
        task_selection_layout.addWidget(QLabel("Select Task:"))
        
        self.task_selector = QComboBox()
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
        
        layout.addLayout(task_selection_layout)
    
    def load_tasks(self):
        """Load tasks from configuration"""
        try:
            self.tasks = get_tasks()
            print(f"从配置加载了 {len(self.tasks)} 个任务")
            
            self.update_task_list()
            
            if self.tasks:
                self.current_task = self.tasks[0]
                print(f"选择了第一个任务: {self.current_task.name}")
                self.task_changed.emit(self.current_task)
            else:
                print("没有找到任务，创建默认任务")
                # Create default task if none exists
                self.current_task = Task(name="Default Task")
                save_task(self.current_task)
                self.tasks = [self.current_task]
                self.update_task_list()
                self.task_changed.emit(self.current_task)
        except Exception as e:
            import traceback
            print(f"加载任务出错: {str(e)}")
            print(traceback.format_exc())
            
            # 确保至少有一个任务可用
            self.current_task = Task(name="Default Task")
            self.tasks = [self.current_task]
            self.update_task_list()
            self.task_changed.emit(self.current_task)
    
    def update_task_list(self):
        """Update the task selector dropdown"""
        try:
            self.task_selector.blockSignals(True)
            self.task_selector.clear()
            
            for task in self.tasks:
                self.task_selector.addItem(task.name, task.task_id)
            
            # Set the current task
            if self.current_task:
                found = False
                for i, task in enumerate(self.tasks):
                    if task.task_id == self.current_task.task_id:
                        self.task_selector.setCurrentIndex(i)
                        found = True
                        break
                
                if not found and self.tasks:
                    # 如果找不到当前任务但有其他任务，选择第一个
                    self.current_task = self.tasks[0]
                    self.task_selector.setCurrentIndex(0)
            
            self.task_selector.blockSignals(False)
        except Exception as e:
            import traceback
            print(f"更新任务列表出错: {str(e)}")
            print(traceback.format_exc())
    
    def on_task_changed(self, index):
        """Handle task selection change"""
        if index >= 0 and index < len(self.tasks):
            self.current_task = self.tasks[index]
            self.task_changed.emit(self.current_task)
    
    def add_task(self):
        """Add a new task"""
        task_name, ok = QInputDialog.getText(self, "Add Task", "Enter task name:")
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
    
    def get_current_task(self):
        """Get the currently selected task"""
        return self.current_task
