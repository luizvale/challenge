# core/entities/task.py
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Set
import uuid


class TaskStatus(Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
    TIMEOUT = "timeout"


class TaskPriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Task:
    """Entity representing a task to be executed."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    timeout_seconds: int = 3600
    max_retries: int = 3
    retry_count: int = 0
    dependency_ids: Set[str] = field(default_factory=set)
    result: Optional[Any] = None
    error: Optional[str] = None
    worker_id: Optional[str] = None

    def is_ready(self, completed_task_ids: Set[str]) -> bool:
        """Check if all dependencies are satisfied."""
        return self.dependency_ids.issubset(completed_task_ids)
