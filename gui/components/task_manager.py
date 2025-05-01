from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox, 
                            QPushButton, QLabel, QInputDialog, QMessageBox,
                            QApplication)
from PyQt6.QtCore import Qt, pyqtSignal, QEvent
from PyQt6.QtGui import QPalette, QColor
from core.config_manager import get_tasks, save_task, delete_task, load_config
from core.task_model import Task
from core.localization import get_text, get_formatted
import logging # Add logging import

# Logger setup
logger = logging.getLogger(__name__) # Create logger instance

class TaskManager(QWidget):
    """Manages tasks selection and basic operations"""
    
    task_changed = pyqtSignal(object)  # Signal emitted when current task changes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tasks = []
        self.current_task = None
        self.setup_ui()
        self.load_tasks()
        
        # Install an event filter to detect system theme changes
        app = QApplication.instance()
        if app:
            app.installEventFilter(self)
    
    def setup_ui(self):
        """Setup the UI components"""
        layout = QVBoxLayout(self)
        
        # Task selection section
        task_selection_layout = QHBoxLayout()
        task_selection_layout.addWidget(QLabel(get_text("select_task")))
        
        self.task_selector = QComboBox()
        self.task_selector.currentIndexChanged.connect(self.on_task_changed)
        # 确保下拉列表的字体大小一致 - 保持原有样式
        self.task_selector.setStyleSheet("""
            QComboBox {
                font-size: 12px;
            }
            QComboBox QAbstractItemView {
                font-size: 12px;
            }
        """)
        # Reduce width of task selector to make room for buttons
        task_selection_layout.addWidget(self.task_selector, 1)
        
        self.add_task_btn = QPushButton(get_text("add_task"))
        self.edit_task_btn = QPushButton(get_text("edit_task"))
        self.duplicate_task_btn = QPushButton(get_text("duplicate_task"))
        self.delete_task_btn = QPushButton(get_text("remove_task"))  # Changed from delete_task to remove_task
        
        # Set fixed width to ensure buttons have consistent size
        button_width = 100
        self.add_task_btn.setFixedWidth(button_width)
        self.edit_task_btn.setFixedWidth(button_width)
        self.duplicate_task_btn.setFixedWidth(button_width)
        self.delete_task_btn.setFixedWidth(button_width)
        
        self.add_task_btn.clicked.connect(self.add_task)
        self.edit_task_btn.clicked.connect(self.edit_task)
        self.duplicate_task_btn.clicked.connect(self.duplicate_task)
        self.delete_task_btn.clicked.connect(self.delete_task)
        
        task_selection_layout.addWidget(self.add_task_btn)
        task_selection_layout.addWidget(self.edit_task_btn)
        task_selection_layout.addWidget(self.duplicate_task_btn)
        task_selection_layout.addWidget(self.delete_task_btn)
        
        layout.addLayout(task_selection_layout)
    
    def load_tasks(self):
        """Load tasks from configuration"""
        try:
            self.tasks = get_tasks()
            print(get_formatted("loaded_tasks", len(self.tasks)))
            
            self.update_task_list()
            
            if self.tasks:
                self.current_task = self.tasks[0]
                print(get_formatted("selected_first_task", self.current_task.name))
                self.task_changed.emit(self.current_task)
            else:
                print(get_text("no_tasks_found"))
                # Create default task if none exists
                self.current_task = Task(name=get_text("default_task"))
                save_task(self.current_task)
                self.tasks = [self.current_task]
                self.update_task_list()
                self.task_changed.emit(self.current_task)
        except Exception as e:
            import traceback
            print(get_formatted("error_loading_tasks", str(e)))
            print(traceback.format_exc())
            
            # Ensure at least one task is available
            self.current_task = Task(name=get_text("default_task"))
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
                    # If current task is not found but there are other tasks, select the first one
                    self.current_task = self.tasks[0]
                    self.task_selector.setCurrentIndex(0)
            
            self.task_selector.blockSignals(False)
        except Exception as e:
            import traceback
            print(get_text("error_updating_task_list").format(str(e)))
            print(traceback.format_exc())
    
    def on_task_changed(self, index):
        """Handle task selection change"""
        if index >= 0 and index < len(self.tasks):
            self.current_task = self.tasks[index]
            self.task_changed.emit(self.current_task)
    
    def add_task(self):
        """Add a new task"""
        task_name, ok = QInputDialog.getText(self, get_text("add_task"), get_text("enter_task_name"))
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
        
        task_name, ok = QInputDialog.getText(self, get_text("edit_task"), 
                                           get_text("enter_new_task_name"), 
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
            QMessageBox.warning(
                self, 
                get_text("cannot_delete"),
                get_text("cannot_delete_only_task")
            )
            return
        
        reply = QMessageBox.question(self, get_text("confirm_delete"), 
                                   get_text("confirm_delete_task").format(self.current_task.name),
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
    
    def duplicate_task(self):
        """Duplicate the current task"""
        if not self.current_task:
            return
        
        # Get a name for the duplicate task
        task_name, ok = QInputDialog.getText(
            self, 
            get_text("duplicate_task"),
            get_text("enter_duplicate_task_name"),
            text=f"{self.current_task.name} ({get_text('copy')})"
        )
        
        if ok and task_name:
            # Create a new task as a copy of the current one
            task_dict = self.current_task.to_dict()
            
            # Remove the ID and last run info (these should be new)
            task_dict.pop("id", None)
            task_dict["name"] = task_name
            task_dict["last_run"] = None
            
            # Reset status tracking for the new task
            task_dict["feeds_status"] = {}
            task_dict["recipients_status"] = {}
            
            # Create and save the new task
            new_task = Task.from_dict(task_dict)
            save_task(new_task)
            
            # Refresh tasks list
            self.tasks = get_tasks()
            self.update_task_list()
            
            # Find and select the new task
            for i, task in enumerate(self.tasks):
                if task.task_id == new_task.task_id:
                    self.task_selector.setCurrentIndex(i)
                    break
            
            QMessageBox.information(
                self, 
                get_text("task_duplicated"),
                get_formatted("task_duplicated_message", task_name)
            )

    def reload_task(self, task_id: str):
        """Reloads a specific task from the configuration file and updates the UI."""
        logger.info(f"Reloading task with ID: {task_id}")
        config = load_config()
        task_data = next((t for t in config.get("tasks", []) if t.get("id") == task_id), None)

        if task_data:
            updated_task = Task.from_dict(task_data)
            # Find the index of the task in the combo box and internal list
            index_to_update = -1
            # --- FIX: Use self.task_selector instead of self.task_combo ---
            for i in range(self.task_selector.count()):
                if self.task_selector.itemData(i) == task_id:
                    index_to_update = i
                    break
            # --- END FIX ---

            if index_to_update != -1:
                # Update the internal list
                self.tasks[index_to_update] = updated_task
                # Update the combo box text (if name changed, though unlikely for unsubscribe)
                # --- FIX: Use self.task_selector instead of self.task_combo ---
                self.task_selector.setItemText(index_to_update, updated_task.name)
                # --- END FIX ---
                logger.info(f"Task '{updated_task.name}' (ID: {task_id}) reloaded.")

                # If this is the currently selected task, emit the change signal
                # --- FIX: Use self.task_selector instead of self.task_combo ---
                if self.task_selector.currentIndex() == index_to_update:
                # --- END FIX ---
                    logger.info(f"Emitting task_changed signal for reloaded task: {task_id}")
                    self.task_changed.emit(updated_task)
                else:
                     logger.info(f"Reloaded task {task_id} is not the currently selected task. Signal not emitted now.")

            else:
                logger.warning(f"Could not find task with ID {task_id} in the UI list after reloading.")
        else:
            logger.warning(f"Could not find task data for ID {task_id} in config during reload.")
    
    def eventFilter(self, obj, event):
        """Event filter to catch palette change events"""
        if event.type() == QEvent.Type.PaletteChange:
            # System theme has changed, need to refresh the QComboBox
            self.refresh_combo_display()
            return False  # Continue event propagation
        return super().eventFilter(obj, event)
    
    def refresh_combo_display(self):
        """Force a refresh of the QComboBox to update its colors based on current theme"""
        # This trick forces the QComboBox to refresh its appearance
        # 1. Store current text/index
        current_index = self.task_selector.currentIndex()
        
        # 2. Briefly disable and re-enable to force a repaint
        self.task_selector.setEnabled(False)
        self.task_selector.setEnabled(True)
        
        # 3. Force style update by setting the same style again
        style = self.task_selector.styleSheet()
        self.task_selector.setStyleSheet("")
        self.task_selector.setStyleSheet(style)
        
        # 4. Ensure selection remains the same
        if current_index >= 0:
            self.task_selector.setCurrentIndex(current_index)
