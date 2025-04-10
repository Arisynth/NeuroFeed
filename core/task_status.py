from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"

@dataclass
class TaskState:
    task_id: str
    name: str
    status: TaskStatus
    progress: int = 0
    message: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error: Optional[str] = None
