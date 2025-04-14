from PyQt6.QtCore import QObject, pyqtSignal
from datetime import datetime
import uuid
from typing import Dict, List, Optional
from collections import deque
from pathlib import Path
from .task_status import TaskState, TaskStatus
from .log_manager import LogManager

# Global instance reference - moved outside the class to avoid metaclass recursion
_status_manager_instance = None

class StatusManager(QObject):
    # Define signals (must be at class level)
    status_updated = pyqtSignal(TaskState)
    task_queue_updated = pyqtSignal(list)
    
    # Modified singleton implementation to avoid metaclass recursion issues
    @staticmethod
    def instance():
        global _status_manager_instance
        if _status_manager_instance is None:
            _status_manager_instance = StatusManager(create_singleton=True)
        return _status_manager_instance
    
    def __init__(self, create_singleton=False):
        # Always initialize the QObject properly
        super().__init__()
        
        # Create instance attributes
        self._active_tasks = {}
        self._task_queue = deque(maxlen=100)
        self._log_manager = LogManager()
        
        # Only proceed with full initialization if this is not the singleton instance
        # and a singleton already exists
        global _status_manager_instance
        if not create_singleton and _status_manager_instance is not None:
            # Instead of copying attributes (which can cause references to be lost),
            # make this instance redirect to the singleton for all operations
            return
            
        # Only set the global instance if we're explicitly creating the singleton
        # or if no singleton exists yet
        if create_singleton or _status_manager_instance is None:
            _status_manager_instance = self
            
    def create_task(self, name: str) -> str:
        """Create a new task and return its ID"""
        task_id = str(uuid.uuid4())
        task_state = TaskState(
            task_id=task_id,
            name=name,
            status=TaskStatus.PENDING
        )
        self._active_tasks[task_id] = task_state
        self._task_queue.append(task_state)
        self.task_queue_updated.emit(list(self._task_queue))
        return task_id
        
    def update_task(self, task_id: str, 
                    status: Optional[TaskStatus] = None,
                    progress: Optional[int] = None,
                    message: Optional[str] = None,
                    error: Optional[str] = None):
        """Update task status"""
        if task_id not in self._active_tasks:
            return
            
        task = self._active_tasks[task_id]
        
        if status:
            task.status = status
            if status == TaskStatus.RUNNING and not task.start_time:
                task.start_time = datetime.now()
            elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELED]:
                task.end_time = datetime.now()
                
        if progress is not None:
            task.progress = min(max(progress, 0), 100)
            
        if message:
            task.message = message
            
        if error:
            task.error = error
            
        # Log the event
        self._log_manager.log_task_event(task)
        
        self.status_updated.emit(task)
        self.task_queue_updated.emit(list(self._task_queue))
        
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELED]:
            self._active_tasks.pop(task_id, None)
            
    def get_task_state(self, task_id: str) -> Optional[TaskState]:
        """Get task state"""
        return self._active_tasks.get(task_id)
        
    def get_task_queue(self) -> List[TaskState]:
        """Get task queue"""
        return list(self._task_queue)
        
    def get_latest_log_file(self) -> Optional[Path]:
        """Get the latest log file path"""
        return self._log_manager.get_latest_log_file()
