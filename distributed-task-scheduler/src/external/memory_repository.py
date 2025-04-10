# external/memory_repositories.py
from datetime import datetime
from typing import Dict, List, Optional, Set
import threading

from ..core.entities.task import Task, TaskStatus
from ..core.entities.worker import Worker, WorkerStatus
from ..core.interfaces.task_repository import TaskRepository
from ..core.interfaces.worker_registry import WorkerRegistry


class MemoryTaskRepository(TaskRepository):
    """In-memory implementation of TaskRepository."""

    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self._lock = threading.Lock()

    def add(self, task: Task) -> str:
        with self._lock:
            self.tasks[task.id] = task
            return task.id

    def get(self, task_id: str) -> Optional[Task]:
        with self._lock:
            return self.tasks.get(task_id)

    def update(self, task: Task) -> None:
        with self._lock:
            self.tasks[task.id] = task

    def get_all(self) -> List[Task]:
        with self._lock:
            return list(self.tasks.values())

    def get_by_status(self, status: TaskStatus) -> List[Task]:
        with self._lock:
            return [task for task in self.tasks.values() if task.status == status]

    def get_pending_tasks(self, completed_task_ids: Set[str]) -> List[Task]:
        with self._lock:
            return [
                task for task in self.tasks.values()
                if task.status == TaskStatus.PENDING and task.is_ready(completed_task_ids)
            ]

    def get_timed_out_tasks(self) -> List[Task]:
        with self._lock:
            now = datetime.now()
            return [
                task for task in self.tasks.values()
                if task.status == TaskStatus.RUNNING
                   and task.started_at is not None
                   and (now - task.started_at).total_seconds() > task.timeout_seconds
            ]


class MemoryWorkerRegistry(WorkerRegistry):
    """In-memory implementation of WorkerRegistry."""

    def __init__(self):
        self.workers: Dict[str, Worker] = {}
        self._lock = threading.Lock()

    def register(self, worker: Worker) -> str:
        with self._lock:
            self.workers[worker.id] = worker
            return worker.id

    def unregister(self, worker_id: str) -> None:
        with self._lock:
            if worker_id in self.workers:
                del self.workers[worker_id]

    def get(self, worker_id: str) -> Optional[Worker]:
        with self._lock:
            return self.workers.get(worker_id)

    def update(self, worker: Worker) -> None:
        with self._lock:
            self.workers[worker.id] = worker

    def get_all(self) -> List[Worker]:
        with self._lock:
            return list(self.workers.values())

    def get_available_workers(self) -> List[Worker]:
        with self._lock:
            return [
                worker for worker in self.workers.values()
                if worker.status == WorkerStatus.IDLE
            ]

    def update_heartbeat(self, worker_id: str) -> None:
        with self._lock:
            if worker_id in self.workers:
                self.workers[worker_id].last_heartbeat = datetime.now()

    def get_dead_workers(self, heartbeat_timeout_seconds: int) -> List[Worker]:
        with self._lock:
            now = datetime.now()
            return [
                worker for worker in self.workers.values()
                if (now - worker.last_heartbeat).total_seconds() > heartbeat_timeout_seconds
            ]

