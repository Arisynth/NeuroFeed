from PyQt6.QtCore import QObject, pyqtSignal
from datetime import datetime
import uuid
from typing import Dict, List, Optional
from collections import deque
from pathlib import Path
from .task_status import TaskState, TaskStatus
from .log_manager import LogManager

class StatusManager(QObject):
    # 定义信号
    status_updated = pyqtSignal(TaskState)
    task_queue_updated = pyqtSignal(list)
    
    _instance = None
    
    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = StatusManager()
        return cls._instance
    
    def __init__(self):
        # 防止多次初始化 QObject
        if StatusManager._instance is not None:
            return
        
        # 确保只有第一个实例初始化父类
        super().__init__()
        self._active_tasks = {}
        self._task_queue = deque(maxlen=100)  # 保留最近100个任务的状态
        self._log_manager = LogManager()
        
        # 将自身设置为单例实例
        StatusManager._instance = self
            
    def create_task(self, name: str) -> str:
        """创建新任务并返回任务ID"""
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
        """更新任务状态"""
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
            
        # 记录日志
        self._log_manager.log_task_event(task)
        
        self.status_updated.emit(task)
        self.task_queue_updated.emit(list(self._task_queue))
        
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELED]:
            self._active_tasks.pop(task_id, None)
            
    def get_task_state(self, task_id: str) -> Optional[TaskState]:
        """获取任务状态"""
        return self._active_tasks.get(task_id)
        
    def get_task_queue(self) -> List[TaskState]:
        """获取任务队列"""
        return list(self._task_queue)
        
    def get_latest_log_file(self) -> Optional[Path]:
        """获取最新日志文件路径"""
        return self._log_manager.get_latest_log_file()
