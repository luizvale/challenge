# core/interfaces/worker_registry.py
from abc import ABC, abstractmethod
from typing import List, Optional

from ..entities.worker import Worker


class WorkerRegistry(ABC):
    """Interface for worker management."""

    @abstractmethod
    def register(self, worker: Worker) -> str:
        """Register a new worker and return its ID."""
        pass

    @abstractmethod
    def unregister(self, worker_id: str) -> None:
        """Unregister a worker by ID."""
        pass

    @abstractmethod
    def get(self, worker_id: str) -> Optional[Worker]:
        """Get a worker by ID."""
        pass

    @abstractmethod
    def update(self, worker: Worker) -> None:
        """Update worker information."""
        pass

    @abstractmethod
    def get_all(self) -> List[Worker]:
        """Get information about all workers."""
        pass

    @abstractmethod
    def get_available_workers(self) -> List[Worker]:
        """Get available workers for task assignment."""
        pass

    @abstractmethod
    def update_heartbeat(self, worker_id: str) -> None:
        """Update worker heartbeat timestamp."""
        pass

    @abstractmethod
    def get_dead_workers(self, heartbeat_timeout_seconds: int) -> List[Worker]:
        """Get workers that haven't sent heartbeats recently."""
        pass