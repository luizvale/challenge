# core/interfaces/task_repository.py
from abc import ABC, abstractmethod
from typing import List, Optional, Set

from ..entities.task import Task, TaskStatus


class TaskRepository(ABC):
    """Interface for task storage and retrieval."""

    @abstractmethod
    def add(self, task: Task) -> str:
        """Add a new task and return its ID."""
        pass

    @abstractmethod
    def get(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        pass

    @abstractmethod
    def update(self, task: Task) -> None:
        """Update an existing task."""
        pass

    @abstractmethod
    def get_all(self) -> List[Task]:
        """Get all tasks."""
        pass

    @abstractmethod
    def get_by_status(self, status: TaskStatus) -> List[Task]:
        """Get tasks by status."""
        pass

    @abstractmethod
    def get_pending_tasks(self, completed_task_ids: Set[str]) -> List[Task]:
        """Get pending tasks whose dependencies are satisfied."""
        pass

    @abstractmethod
    def get_timed_out_tasks(self) -> List[Task]:
        """Get tasks that have timed out."""
        pass
