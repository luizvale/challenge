import threading
from datetime import datetime
from typing import Dict, List, Optional, Set
import logging
from collections import defaultdict, deque

from ..core.entities.worker import WorkerStatus
from ..core.interfaces.monitoring import TaskMonitor
from ..core.interfaces.task_repository import TaskRepository
from ..core.interfaces.worker_registry import WorkerRegistry
from ..core.entities.task import TaskStatus


class SystemMonitor(TaskMonitor):
    """Implementation of task and system monitoring."""

    def __init__(
            self,
            task_repository: TaskRepository,
            worker_registry: WorkerRegistry,
            history_size: int = 100,
            logger=None
    ):
        self.task_repository = task_repository
        self.worker_registry = worker_registry
        self.history_size = history_size
        self.logger = logger or logging.getLogger(__name__)

        # Locks for thread safety
        self._lock = threading.Lock()

        # Task metrics
        self.task_creation_times: Dict[str, datetime] = {}
        self.task_start_times: Dict[str, datetime] = {}
        self.task_execution_times: Dict[str, int] = {}  # in milliseconds
        self.task_histories: Dict[str, List[Dict]] = defaultdict(list)

        # Worker metrics
        self.worker_task_counts: Dict[str, int] = defaultdict(int)
        self.worker_success_counts: Dict[str, int] = defaultdict(int)
        self.worker_failure_counts: Dict[str, int] = defaultdict(int)
        self.worker_execution_times: Dict[str, List[int]] = defaultdict(list)

        # System metrics
        self.task_type_counts: Dict[str, int] = defaultdict(int)
        self.status_counts: Dict[str, int] = defaultdict(int)
        self.recent_executions = deque(maxlen=history_size)

        # Start time for uptime calculation
        self.start_time = datetime.now()

    def record_task_created(self, task_id: str, task_name: str) -> None:
        """Record a task creation event."""
        with self._lock:
            now = datetime.now()
            self.task_creation_times[task_id] = now
            self.task_type_counts[task_name] += 1
            self.status_counts[TaskStatus.PENDING.value] += 1

            self.task_histories[task_id].append({
                "event": "created",
                "timestamp": now,
                "task_name": task_name
            })

            self.logger.debug(f"Task {task_id} ({task_name}) created")

    def record_task_started(self, task_id: str, worker_id: str) -> None:
        """Record a task started event."""
        with self._lock:
            now = datetime.now()
            self.task_start_times[task_id] = now
            self.worker_task_counts[worker_id] += 1

            # Update status counts
            self.status_counts[TaskStatus.PENDING.value] -= 1
            self.status_counts[TaskStatus.RUNNING.value] += 1

            self.task_histories[task_id].append({
                "event": "started",
                "timestamp": now,
                "worker_id": worker_id
            })

            self.logger.debug(f"Task {task_id} started by worker {worker_id}")

    def record_task_completed(self, task_id: str, success: bool, execution_time_ms: int) -> None:
        """Record a task completion event."""
        with self._lock:
            now = datetime.now()
            self.task_execution_times[task_id] = execution_time_ms

            # Get worker id from history
            worker_id = None
            for event in reversed(self.task_histories[task_id]):
                if event["event"] == "started":
                    worker_id = event.get("worker_id")
                    break

            if worker_id:
                if success:
                    self.worker_success_counts[worker_id] += 1
                else:
                    self.worker_failure_counts[worker_id] += 1

                self.worker_execution_times[worker_id].append(execution_time_ms)

            # Update status counts
            self.status_counts[TaskStatus.RUNNING.value] -= 1
            if success:
                self.status_counts[TaskStatus.COMPLETED.value] += 1
            else:
                self.status_counts[TaskStatus.FAILED.value] += 1

            # Record in recent executions
            self.recent_executions.append({
                "task_id": task_id,
                "success": success,
                "execution_time_ms": execution_time_ms,
                "timestamp": now,
                "worker_id": worker_id
            })

            self.task_histories[task_id].append({
                "event": "completed" if success else "failed",
                "timestamp": now,
                "execution_time_ms": execution_time_ms
            })

            self.logger.debug(
                f"Task {task_id} {'completed successfully' if success else 'failed'} "
                f"in {execution_time_ms}ms"
            )

    def record_task_failed(self, task_id: str, error: str) -> None:
        """Record a task failure event."""
        with self._lock:
            now = datetime.now()

            # Calculate execution time if we have start time
            execution_time_ms = 0
            if task_id in self.task_start_times:
                start_time = self.task_start_times[task_id]
                execution_time_ms = int((now - start_time).total_seconds() * 1000)
                self.task_execution_times[task_id] = execution_time_ms

            # Update status counts
            self.status_counts[TaskStatus.RUNNING.value] -= 1
            self.status_counts[TaskStatus.FAILED.value] += 1

            self.task_histories[task_id].append({
                "event": "failed",
                "timestamp": now,
                "error": error,
                "execution_time_ms": execution_time_ms
            })

            self.logger.debug(f"Task {task_id} failed with error: {error}")

    def record_task_canceled(self, task_id: str) -> None:
        """Record a task cancellation event."""
        with self._lock:
            now = datetime.now()

            # Find current status in repo to decrement the right counter
            task = self.task_repository.get(task_id)
            if task and task.status != TaskStatus.CANCELED:
                self.status_counts[task.status.value] -= 1
                self.status_counts[TaskStatus.CANCELED.value] += 1

            self.task_histories[task_id].append({
                "event": "canceled",
                "timestamp": now
            })

            self.logger.debug(f"Task {task_id} canceled")

    def get_task_stats(self, task_id: Optional[str] = None) -> Dict:
        """Get statistics for a specific task or all tasks."""
        with self._lock:
            if task_id:
                # Statistics for a specific task
                task = self.task_repository.get(task_id)
                if not task:
                    return {"error": "Task not found"}

                result = {
                    "id": task_id,
                    "name": task.name,
                    "status": task.status.value,
                    "creation_time": self.task_creation_times.get(task_id),
                    "execution_time_ms": self.task_execution_times.get(task_id),
                    "history": self.task_histories.get(task_id, [])
                }

                # Calculate wait time if applicable
                if task_id in self.task_creation_times and task_id in self.task_start_times:
                    wait_time = (self.task_start_times[task_id] - self.task_creation_times[task_id]).total_seconds()
                    result["wait_time_seconds"] = wait_time

                return result
            else:
                # Aggregated statistics for all tasks
                all_tasks = self.task_repository.get_all()

                # Calculate average execution times by task type
                type_execution_times = defaultdict(list)
                for task in all_tasks:
                    if task.id in self.task_execution_times:
                        type_execution_times[task.name].append(self.task_execution_times[task.id])

                avg_execution_times = {}
                for task_type, times in type_execution_times.items():
                    if times:
                        avg_execution_times[task_type] = sum(times) / len(times)

                return {
                    "total_tasks": len(all_tasks),
                    "task_type_counts": dict(self.task_type_counts),
                    "status_counts": dict(self.status_counts),
                    "avg_execution_times_ms": avg_execution_times
                }

    def get_worker_stats(self, worker_id: Optional[str] = None) -> Dict:
        """Get statistics for a specific worker or all workers."""
        with self._lock:
            if worker_id:
                # Statistics for a specific worker
                worker = self.worker_registry.get(worker_id)
                if not worker:
                    return {"error": "Worker not found"}

                total_tasks = self.worker_task_counts.get(worker_id, 0)
                success_count = self.worker_success_counts.get(worker_id, 0)
                failure_count = self.worker_failure_counts.get(worker_id, 0)
                execution_times = self.worker_execution_times.get(worker_id, [])

                result = {
                    "id": worker_id,
                    "status": worker.status.value,
                    "current_task_id": worker.current_task_id,
                    "started_at": worker.started_at,
                    "last_heartbeat": worker.last_heartbeat,
                    "total_tasks_processed": total_tasks,
                    "successful_tasks": success_count,
                    "failed_tasks": failure_count,
                    "success_rate": success_count / total_tasks if total_tasks > 0 else 0
                }

                if execution_times:
                    result["avg_execution_time_ms"] = sum(execution_times) / len(execution_times)
                    result["min_execution_time_ms"] = min(execution_times)
                    result["max_execution_time_ms"] = max(execution_times)

                return result
            else:
                # Aggregated statistics for all workers
                all_workers = self.worker_registry.get_all()

                busy_count = sum(1 for w in all_workers if w.status == WorkerStatus.BUSY)
                idle_count = sum(1 for w in all_workers if w.status == WorkerStatus.IDLE)
                down_count = sum(1 for w in all_workers if w.status == WorkerStatus.DOWN)

                total_success = sum(self.worker_success_counts.values())
                total_failure = sum(self.worker_failure_counts.values())
                total_tasks = total_success + total_failure

                result = {
                    "total_workers": len(all_workers),
                    "busy_workers": busy_count,
                    "idle_workers": idle_count,
                    "down_workers": down_count,
                    "utilization_rate": busy_count / len(all_workers) if all_workers else 0,
                    "total_tasks_processed": total_tasks,
                    "successful_tasks": total_success,
                    "failed_tasks": total_failure,
                    "success_rate": total_success / total_tasks if total_tasks > 0 else 0
                }

                # Get most productive worker
                if self.worker_task_counts:
                    most_productive_id = max(self.worker_task_counts.items(), key=lambda x: x[1])[0]
                    result["most_productive_worker"] = most_productive_id
                    result["most_productive_worker_tasks"] = self.worker_task_counts[most_productive_id]

                return result

    def get_system_metrics(self) -> Dict:
        """Get overall system metrics."""
        with self._lock:
            now = datetime.now()
            uptime_seconds = (now - self.start_time).total_seconds()

            all_tasks = self.task_repository.get_all()
            all_workers = self.worker_registry.get_all()

            # Calculate throughput
            completed_tasks = sum(1 for task in all_tasks if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED))
            throughput = completed_tasks / uptime_seconds if uptime_seconds > 0 else 0

            # Get recent execution statistics
            recent_exec_list = list(self.recent_executions)
            avg_recent_time = 0
            success_rate = 0

            if recent_exec_list:
                recent_times = [e["execution_time_ms"] for e in recent_exec_list]
                avg_recent_time = sum(recent_times) / len(recent_times)
                success_count = sum(1 for e in recent_exec_list if e["success"])
                success_rate = success_count / len(recent_exec_list)

            return {
                "uptime_seconds": uptime_seconds,
                "total_tasks": len(all_tasks),
                "completed_tasks": completed_tasks,
                "throughput_tasks_per_second": throughput,
                "total_workers": len(all_workers),
                "active_workers": sum(1 for w in all_workers if w.status != WorkerStatus.DOWN),
                "status_distribution": dict(self.status_counts),
                "recent_executions_count": len(recent_exec_list),
                "recent_avg_execution_time_ms": avg_recent_time,
                "recent_success_rate": success_rate
            }

# Agora vamos modificar o use_cases/task_scheduler.py para incorporar o monitoramento
# Isso requer atualizar o uso_cases/task_scheduler.py para adicionar a dependência do monitor