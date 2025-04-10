# core/interfaces/task_executor.py
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional

from ..entities.task import Task


class TaskExecutor(ABC):
    """Interface for executing tasks."""

    @abstractmethod
    def execute(self, task: Task) -> Dict[str, Any]:
        """Execute a task and return the result."""
        pass

    @abstractmethod
    def register_handler(self, task_name: str, handler: Callable[[Task], Any]) -> None:
        """Register a handler function for a specific task type."""
        pass