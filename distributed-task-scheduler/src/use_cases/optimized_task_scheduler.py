# use_cases/optimized_task_scheduler.py
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Set
import logging

from ..core.entities.task import Task, TaskStatus
from ..core.entities.worker import Worker, WorkerStatus
from ..core.interfaces.task_repository import TaskRepository
from ..core.interfaces.worker_registry import WorkerRegistry
from ..core.interfaces.task_queue import TaskQueue
from ..core.interfaces.task_executor import TaskExecutor
from ..core.interfaces.monitoring import TaskMonitor


class OptimizedTaskScheduler:
    """Optimized version of task scheduler for high performance."""

    def __init__(
            self,
            task_repository: TaskRepository,
            worker_registry: WorkerRegistry,
            task_queue: TaskQueue,
            task_executor: TaskExecutor,
            task_monitor: TaskMonitor,
            heartbeat_timeout_seconds: int = 30,
            worker_check_interval: int = 10,
            batch_size: int = 20,
            adaptive_workers: bool = True,
            min_workers: int = 5,
            max_workers: int = 50,
            scaling_check_interval: int = 15,
            logger=None
    ):
        self.task_repository = task_repository
        self.worker_registry = worker_registry
        self.task_queue = task_queue
        self.task_executor = task_executor
        self.task_monitor = task_monitor
        self.heartbeat_timeout_seconds = heartbeat_timeout_seconds
        self.worker_check_interval = worker_check_interval
        self.batch_size = batch_size
        self.adaptive_workers = adaptive_workers
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.scaling_check_interval = scaling_check_interval
        self.logger = logger or logging.getLogger(__name__)
        self.running = False
        self.completed_task_ids: Set[str] = set()
        self._scheduler_thread = None
        self._last_scaling_check = time.time()

        # Settings for adaptive adjustments
        self.idle_threshold = 0.3  # If more than 30% of workers are idle, scale down
        self.busy_threshold = 0.8  # If more than 80% of workers are busy, scale up

    def schedule_task(self, task: Task) -> str:
        """Schedule a task for execution."""
        self.task_repository.add(task)

        # Record task creation in monitor
        self.task_monitor.record_task_created(task.id, task.name)

        # If task has no dependencies, add it to the queue immediately
        if not task.dependency_ids or all(
                dep_id in self.completed_task_ids for dep_id in task.dependency_ids
        ):
            task.status = TaskStatus.QUEUED
            self.task_repository.update(task)
            self.task_queue.enqueue(task)

        return task.id

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled task."""
        task = self.task_repository.get(task_id)

        if not task:
            return False

        # If task is queued, remove from queue
        if task.status == TaskStatus.QUEUED:
            self.task_queue.remove(task_id)

        # If task is running and assigned to a worker, update worker status
        if task.status == TaskStatus.RUNNING and task.worker_id:
            worker = self.worker_registry.get(task.worker_id)
            if worker and worker.current_task_id == task_id:
                worker.status = WorkerStatus.IDLE
                worker.current_task_id = None
                self.worker_registry.update(worker)

        # Update task status
        task.status = TaskStatus.CANCELED
        task.completed_at = datetime.now()
        self.task_repository.update(task)

        # Record cancellation in monitor
        self.task_monitor.record_task_canceled(task_id)

        return True

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get the status of a task."""
        task = self.task_repository.get(task_id)

        if not task:
            return None

        result = {
            "id": task.id,
            "name": task.name,
            "status": task.status.value,
            "priority": task.priority.value,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "retry_count": task.retry_count,
            "result": task.result,
            "error": task.error
        }

        # Add worker information if assigned
        if task.worker_id:
            worker = self.worker_registry.get(task.worker_id)
            if worker:
                result["worker_id"] = worker.id
                result["worker_status"] = worker.status.value

        return result

    def list_tasks(self, status: Optional[str] = None) -> List[Dict]:
        """List tasks with optional filtering."""
        if status:
            try:
                task_status = TaskStatus(status)
                tasks = self.task_repository.get_by_status(task_status)
            except ValueError:
                tasks = []
        else:
            tasks = self.task_repository.get_all()

        return [
            {
                "id": task.id,
                "name": task.name,
                "status": task.status.value,
                "priority": task.priority.value,
                "worker_id": task.worker_id
            }
            for task in tasks
        ]

    def scale_workers(self, count: int) -> int:
        """Scale the number of workers."""
        current_workers = self.worker_registry.get_all()
        current_count = len(current_workers)

        # Apply limits
        count = max(self.min_workers, min(self.max_workers, count))

        if count == current_count:
            return current_count

        if count > current_count:
            # Scale up - create new workers
            for i in range(current_count, count):
                worker = Worker()
                self.worker_registry.register(worker)
            self.logger.info(f"Scaled workers up from {current_count} to {count}")
        else:
            # Scale down - remove excess workers (idle ones first)
            idle_workers = [w for w in current_workers if w.status == WorkerStatus.IDLE]

            # Remove idle workers first
            for worker in idle_workers[:current_count - count]:
                self.worker_registry.unregister(worker.id)

            self.logger.info(f"Scaled workers down from {current_count} to {count}")

        return count

    def get_worker_status(self, worker_id: Optional[str] = None) -> List[Dict]:
        """Get status information about workers."""
        if worker_id:
            worker = self.worker_registry.get(worker_id)
            workers = [worker] if worker else []
        else:
            workers = self.worker_registry.get_all()

        return [
            {
                "id": worker.id,
                "status": worker.status.value,
                "current_task_id": worker.current_task_id,
                "last_heartbeat": worker.last_heartbeat
            }
            for worker in workers
        ]

    def get_system_metrics(self) -> Dict:
        """Get system metrics from the monitor."""
        return self.task_monitor.get_system_metrics()

    def get_worker_metrics(self, worker_id: Optional[str] = None) -> Dict:
        """Get worker metrics from the monitor."""
        return self.task_monitor.get_worker_stats(worker_id)

    def get_task_metrics(self, task_id: Optional[str] = None) -> Dict:
        """Get task metrics from the monitor."""
        return self.task_monitor.get_task_stats(task_id)

    def start(self) -> None:
        """Start the scheduler."""
        if self.running:
            return

        self.running = True
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop)
        self._scheduler_thread.daemon = True
        self._scheduler_thread.start()
        self.logger.info("Scheduler started")

    def stop(self) -> None:
        """Stop the scheduler."""
        if not self.running:
            return

        self.running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
        self.logger.info("Scheduler stopped")

    def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        last_worker_check = time.time()

        while self.running:
            try:
                # Check for dead workers
                current_time = time.time()
                if current_time - last_worker_check > self.worker_check_interval:
                    self._check_workers()
                    last_worker_check = current_time

                # Check for tasks with satisfied dependencies
                self._check_dependencies()

                # Check for timed out tasks
                self._check_timeouts()

                # Assign tasks to available workers in batches
                self._assign_tasks_batch()

                # Perform adaptive worker scaling if enabled
                if self.adaptive_workers and (current_time - self._last_scaling_check > self.scaling_check_interval):
                    self._adjust_worker_count()
                    self._last_scaling_check = current_time

                # Short sleep to prevent CPU hogging
                time.sleep(0.05)  # Reduced from 0.1 to be more responsive

            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")
                time.sleep(1)  # Sleep longer on error

    def _check_workers(self) -> None:
        """Check for dead workers and handle their tasks."""
        dead_workers = self.worker_registry.get_dead_workers(self.heartbeat_timeout_seconds)

        for worker in dead_workers:
            self.logger.warning(f"Worker {worker.id} appears to be dead")

            # If worker was running a task, mark it for retry
            if worker.current_task_id:
                task = self.task_repository.get(worker.current_task_id)

                if task and task.status == TaskStatus.RUNNING:
                    if task.retry_count < task.max_retries:
                        task.retry_count += 1
                        task.status = TaskStatus.PENDING
                        task.worker_id = None
                        self.task_repository.update(task)
                        self.logger.info(f"Task {task.id} scheduled for retry")
                    else:
                        task.status = TaskStatus.FAILED
                        task.error = f"Worker {worker.id} died and max retries reached"
                        task.completed_at = datetime.now()
                        self.task_repository.update(task)
                        self.logger.warning(f"Task {task.id} failed after max retries")

                        # Record failure in monitor
                        self.task_monitor.record_task_failed(task.id, task.error)

            # Mark worker as down
            worker.status = WorkerStatus.DOWN
            self.worker_registry.update(worker)

    def _check_dependencies(self) -> None:
        """Check for tasks with satisfied dependencies and queue them."""
        ready_tasks = self.task_repository.get_pending_tasks(self.completed_task_ids)

        if ready_tasks:
            for task in ready_tasks:
                task.status = TaskStatus.QUEUED
                self.task_repository.update(task)
                self.task_queue.enqueue(task)

            self.logger.debug(f"Queued {len(ready_tasks)} tasks with satisfied dependencies")

    def _check_timeouts(self) -> None:
        """Check for timed out tasks."""
        timed_out_tasks = self.task_repository.get_timed_out_tasks()

        for task in timed_out_tasks:
            # Check if task should be retried
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                task.started_at = None
                task.worker_id = None

                if task.worker_id:
                    worker = self.worker_registry.get(task.worker_id)
                    if worker and worker.current_task_id == task.id:
                        worker.status = WorkerStatus.IDLE
                        worker.current_task_id = None
                        self.worker_registry.update(worker)

                self.task_repository.update(task)
                self.logger.info(f"Timed out task {task.id} scheduled for retry")
            else:
                # Mark as timed out
                task.status = TaskStatus.TIMEOUT
                task.completed_at = datetime.now()
                task.error = "Task timed out"

                if task.worker_id:
                    worker = self.worker_registry.get(task.worker_id)
                    if worker and worker.current_task_id == task.id:
                        worker.status = WorkerStatus.IDLE
                        worker.current_task_id = None
                        self.worker_registry.update(worker)

                self.task_repository.update(task)
                self.logger.warning(f"Task {task.id} timed out after max retries")

                # Record failure in monitor
                self.task_monitor.record_task_failed(task.id, task.error)

    def _assign_tasks_batch(self) -> None:
        """Assign tasks to available workers in batches for better performance."""
        if self.task_queue.is_empty():
            return

        available_workers = self.worker_registry.get_available_workers()
        if not available_workers:
            return

        # Determine batch size based on available workers
        batch_size = min(self.batch_size, max(1, len(available_workers) * 2))

        # Get batch of tasks
        tasks = []
        for _ in range(batch_size):
            if self.task_queue.is_empty():
                break
            task = self.task_queue.dequeue()
            if task:
                tasks.append(task)

        if not tasks:
            return

        self.logger.debug(f"Processing batch of {len(tasks)} tasks with {len(available_workers)} workers")

        # Distribute tasks to workers
        worker_index = 0
        for task in tasks:
            if worker_index >= len(available_workers):
                worker_index = 0

            worker = available_workers[worker_index]

            # Assign task to worker
            worker.status = WorkerStatus.BUSY
            worker.current_task_id = task.id
            self.worker_registry.update(worker)

            # Update task status
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            task.worker_id = worker.id
            self.task_repository.update(task)

            # Record task start in monitor
            self.task_monitor.record_task_started(task.id, worker.id)

            # Start task execution in a separate thread
            threading.Thread(
                target=self._execute_task,
                args=(task, worker),
                daemon=True
            ).start()

            worker_index += 1

    def _adjust_worker_count(self) -> None:
        """Dynamically adjust the number of workers based on current load."""
        # Get current metrics
        workers = self.worker_registry.get_all()

        if not workers:
            self.scale_workers(self.min_workers)
            return

        current_count = len(workers)
        busy_count = sum(1 for w in workers if w.status == WorkerStatus.BUSY)
        idle_count = sum(1 for w in workers if w.status == WorkerStatus.IDLE)

        busy_ratio = busy_count / current_count if current_count > 0 else 0
        idle_ratio = idle_count / current_count if current_count > 0 else 0

        # Check if queue is empty
        queue_empty = self.task_queue.is_empty()

        # Make scaling decision
        if busy_ratio > self.busy_threshold and not queue_empty and current_count < self.max_workers:
            # Many busy workers and tasks still in queue - scale up
            new_count = min(self.max_workers, int(current_count * 1.5))
            if new_count > current_count:
                self.logger.info(f"Scaling workers up: {current_count} -> {new_count} (busy_ratio={busy_ratio:.2f})")
                self.scale_workers(new_count)

        elif idle_ratio > self.idle_threshold and current_count > self.min_workers:
            # Many idle workers - scale down
            new_count = max(self.min_workers, int(current_count * 0.8))
            if new_count < current_count:
                self.logger.info(f"Scaling workers down: {current_count} -> {new_count} (idle_ratio={idle_ratio:.2f})")
                self.scale_workers(new_count)

    def _execute_task(self, task: Task, worker: Worker) -> None:
        """Execute a task on a worker."""
        start_time = time.time()

        try:
            # Execute the task
            result = self.task_executor.execute(task)

            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)

            # Update task status based on result
            if result.get("success", False):
                task.status = TaskStatus.COMPLETED
                task.result = result.get("result")
                # Add to completed tasks set for dependency tracking
                self.completed_task_ids.add(task.id)

                # Record successful completion in monitor
                self.task_monitor.record_task_completed(task.id, True, execution_time_ms)
            else:
                if task.retry_count < task.max_retries:
                    task.retry_count += 1
                    task.status = TaskStatus.PENDING
                    task.error = result.get("error", "Unknown error")
                    self.logger.info(f"Task {task.id} failed, scheduling retry {task.retry_count}/{task.max_retries}")
                else:
                    task.status = TaskStatus.FAILED
                    task.error = result.get("error", "Unknown error")
                    self.logger.warning(f"Task {task.id} failed after max retries: {task.error}")

                    # Record failure in monitor
                    self.task_monitor.record_task_failed(task.id, task.error)

            task.completed_at = datetime.now()
            self.task_repository.update(task)

        except Exception as e:
            # Calculate execution time even on exception
            execution_time_ms = int((time.time() - start_time) * 1000)

            self.logger.error(f"Error executing task {task.id}: {e}")
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now()
            self.task_repository.update(task)

            # Record failure in monitor
            self.task_monitor.record_task_failed(task.id, str(e))

        finally:
            # Update worker status
            try:
                worker = self.worker_registry.get(worker.id)
                if worker and worker.current_task_id == task.id:
                    worker.status = WorkerStatus.IDLE
                    worker.current_task_id = None
                    self.worker_registry.update(worker)
            except Exception as e:
                self.logger.error(f"Error updating worker {worker.id}: {e}")