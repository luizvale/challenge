# core/entities/worker.py
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class WorkerStatus(Enum):
    IDLE = "idle"
    BUSY = "busy"
    DOWN = "down"


@dataclass
class Worker:
    """Entity representing a worker process."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: WorkerStatus = WorkerStatus.IDLE
    current_task_id: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.now)
    last_heartbeat: datetime = field(default_factory=datetime.now)