# core/interfaces/monitoring.py
from abc import ABC, abstractmethod
from typing import Dict, Optional


class TaskMonitor(ABC):
    """Interface for task monitoring."""

    @abstractmethod
    def record_task_created(self, task_id: str, task_name: str) -> None:
        """Record a task creation event."""
        pass

    @abstractmethod
    def record_task_started(self, task_id: str, worker_id: str) -> None:
        """Record a task started event."""
        pass

    @abstractmethod
    def record_task_completed(self, task_id: str, success: bool, execution_time_ms: int) -> None:
        """Record a task completion event."""
        pass

    @abstractmethod
    def record_task_failed(self, task_id: str, error: str) -> None:
        """Record a task failure event."""
        pass

    @abstractmethod
    def record_task_canceled(self, task_id: str) -> None:
        """Record a task cancellation event."""
        pass

    @abstractmethod
    def get_task_stats(self, task_id: Optional[str] = None) -> Dict:
        """Get statistics for a specific task or all tasks."""
        pass

    @abstractmethod
    def get_worker_stats(self, worker_id: Optional[str] = None) -> Dict:
        """Get statistics for a specific worker or all workers."""
        pass

    @abstractmethod
    def get_system_metrics(self) -> Dict:
        """Get overall system metrics."""
        pass