# core/interfaces/task_queue.py
from abc import ABC, abstractmethod
from typing import Optional

from ..entities.task import Task


class TaskQueue(ABC):
    """Interface for task queuing and prioritization."""

    @abstractmethod
    def enqueue(self, task: Task) -> None:
        """Add a task to the queue."""
        pass

    @abstractmethod
    def dequeue(self) -> Optional[Task]:
        """Get the next task with highest priority."""
        pass

    @abstractmethod
    def remove(self, task_id: str) -> bool:
        """Remove a task from the queue."""
        pass

    @abstractmethod
    def is_empty(self) -> bool:
        """Check if the queue is empty."""
        pass

