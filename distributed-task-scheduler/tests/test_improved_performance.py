import time
import logging
import random
import unittest
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from src.core.entities.task import Task, TaskStatus, TaskPriority
from src.external.memory_repository import MemoryTaskRepository, MemoryWorkerRegistry
from src.external.task_queue import PriorityTaskQueue
from src.external.task_executor import DefaultTaskExecutor
from src.external.monitoring import SystemMonitor
from src.use_cases.task_scheduler import TaskScheduler

from src.core.entities.worker import WorkerStatus


class ImprovedPerformanceTest(unittest.TestCase):
    """Improved version of performance tests with detailed logging."""

    def setUp(self):
        """Executed before each test."""
        # Configure logger for more detailed output
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("improved_perf_test")

        # Set up components
        self.task_repository = MemoryTaskRepository()
        self.worker_registry = MemoryWorkerRegistry()
        self.task_queue = PriorityTaskQueue()
        self.task_executor = DefaultTaskExecutor()
        self.monitor = SystemMonitor(
            task_repository=self.task_repository,
            worker_registry=self.worker_registry,
            logger=self.logger
        )

        # Register task handlers with logging
        def fast_handler(task):
            self.logger.debug(f"Running fast task {task.id}")
            time.sleep(random.uniform(0.001, 0.005))  # Simulate fast work (1–5 ms)
            return "fast result"

        def medium_handler(task):
            self.logger.debug(f"Running medium task {task.id}")
            time.sleep(random.uniform(0.01, 0.05))  # Simulate medium work (10–50 ms)
            return "medium result"

        def slow_handler(task):
            self.logger.debug(f"Running slow task {task.id}")
            time.sleep(random.uniform(0.1, 0.5))  # Simulate slow work (100–500 ms)
            return "slow result"

        def random_failing_handler(task):
            self.logger.debug(f"Running randomly failing task {task.id}")
            if random.random() < 0.2:  # 20% chance of failure
                self.logger.debug(f"Task {task.id} failed randomly")
                raise ValueError("Random failure")
            time.sleep(random.uniform(0.01, 0.05))
            return "success"

        self.task_executor.register_handler("fast", fast_handler)
        self.task_executor.register_handler("medium", medium_handler)
        self.task_executor.register_handler("slow", slow_handler)
        self.task_executor.register_handler("random_fail", random_failing_handler)

        # Create scheduler with detailed log monitoring
        self.scheduler = TaskScheduler(
            task_repository=self.task_repository,
            worker_registry=self.worker_registry,
            task_queue=self.task_queue,
            task_executor=self.task_executor,
            task_monitor=self.monitor,
            heartbeat_timeout_seconds=10,
            worker_check_interval=5,
            logger=self.logger
        )

        self.scheduler.start()
        self.logger.info("Scheduler started")

    def tearDown(self):
        """Executed after each test."""
        self.logger.info("Stopping scheduler")
        self.scheduler.stop()
        time.sleep(1)
        self.logger.info("Scheduler stopped")

    def test_improved_concurrency(self):
        """Enhanced high-concurrency test with detailed monitoring."""
        self.scheduler.scale_workers(10)
        self.logger.info("Scaled to 10 workers")

        num_threads = 5
        tasks_per_thread = 50
        total_tasks = num_threads * tasks_per_thread

        self.logger.info(
            f"Starting test with {num_threads} threads and {tasks_per_thread} tasks per thread ({total_tasks} total)")

        task_mapping = {}
        all_task_ids = []

        def create_tasks(thread_id):
            thread_task_ids = []
            for i in range(tasks_per_thread):
                task_type = ["fast", "medium", "random_fail"][i % 3]
                task = Task(
                    name=task_type,
                    payload={"thread": thread_id, "index": i},
                    priority=random.choice(list(TaskPriority))
                )
                task_id = self.scheduler.schedule_task(task)
                thread_task_ids.append(task_id)
                task_mapping[task_id] = (thread_id, i)
            return thread_task_ids

        start_time = time.time()
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(create_tasks, t) for t in range(num_threads)]
            for future in futures:
                all_task_ids.extend(future.result())

        submission_time = time.time() - start_time
        self.logger.info(f"Submission time for {total_tasks} tasks: {submission_time:.2f} seconds")

        system_metrics_before = self.scheduler.get_system_metrics()
        self.logger.info(f"System metrics after submission: {system_metrics_before}")

        worker_metrics_before = self.scheduler.get_worker_metrics()
        self.logger.info(f"Worker metrics after submission: {worker_metrics_before}")

        max_wait = 120
        remaining_tasks = set(all_task_ids)
        check_interval = 5

        self.logger.info(f"Waiting for task completion (timeout: {max_wait} seconds)")

        progress_updates = []
        start_wait_time = time.time()
        last_check_time = start_wait_time

        while remaining_tasks and (time.time() - start_wait_time < max_wait):
            current_time = time.time()
            if current_time - last_check_time >= check_interval:
                newly_completed = set()
                task_status_counts = {
                    TaskStatus.PENDING.value: 0,
                    TaskStatus.QUEUED.value: 0,
                    TaskStatus.RUNNING.value: 0,
                    TaskStatus.COMPLETED.value: 0,
                    TaskStatus.FAILED.value: 0,
                    TaskStatus.CANCELED.value: 0,
                    TaskStatus.TIMEOUT.value: 0
                }

                for task_id in list(remaining_tasks):
                    status = self.scheduler.get_task_status(task_id)
                    current_status = status["status"]
                    task_status_counts[current_status] = task_status_counts.get(current_status, 0) + 1

                    if current_status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value]:
                        newly_completed.add(task_id)

                for task_id in newly_completed:
                    remaining_tasks.remove(task_id)

                elapsed = current_time - start_wait_time
                progress = {
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "elapsed_seconds": elapsed,
                    "remaining_tasks": len(remaining_tasks),
                    "completed_tasks": total_tasks - len(remaining_tasks),
                    "status_counts": task_status_counts
                }

                progress_updates.append(progress)
                self.logger.info(
                    f"Progress after {elapsed:.1f}s: Remaining: {len(remaining_tasks)}, Status: {task_status_counts}")

                system_metrics = self.scheduler.get_system_metrics()
                self.logger.info(f"System metrics during execution: {system_metrics}")

                worker_metrics = self.scheduler.get_worker_metrics()
                self.logger.info(f"Worker metrics during execution: {worker_metrics}")

                workers = self.scheduler.get_worker_status()
                idle_workers = sum(1 for w in workers if w["status"] == WorkerStatus.IDLE.value)

                if idle_workers > 0 and task_status_counts.get(TaskStatus.PENDING.value, 0) > 0:
                    self.logger.warning(
                        f"ANOMALY DETECTED: {idle_workers} idle workers, but {task_status_counts.get(TaskStatus.PENDING.value, 0)} pending tasks"
                    )

                last_check_time = current_time

            time.sleep(0.1)

        elapsed_time = time.time() - start_time
        throughput = (total_tasks - len(remaining_tasks)) / elapsed_time

        self.logger.info(f"Total processing time: {elapsed_time:.2f} seconds")
        self.logger.info(f"Processing throughput: {throughput:.2f} tasks/second")

        if remaining_tasks:
            self.logger.warning(f"{len(remaining_tasks)} tasks were not completed!")

            status_counts = {}
            type_counts = {}
            thread_counts = {}

            for task_id in remaining_tasks:
                status = self.scheduler.get_task_status(task_id)
                current_status = status["status"]
                task = self.task_repository.get(task_id)

                status_counts[current_status] = status_counts.get(current_status, 0) + 1
                type_counts[task.name] = type_counts.get(task.name, 0) + 1

                thread_info = task_mapping.get(task_id, (-1, -1))
                thread_id = thread_info[0]
                thread_counts[thread_id] = thread_counts.get(thread_id, 0) + 1

                if len(status_counts) < 10:
                    self.logger.warning(
                        f"Incomplete task: {task_id}, Status: {current_status}, Type: {task.name}, Thread: {thread_info}")

            self.logger.warning(f"Status distribution of incomplete tasks: {status_counts}")
            self.logger.warning(f"Type distribution of incomplete tasks: {type_counts}")
            self.logger.warning(f"Thread distribution of incomplete tasks: {thread_counts}")

            system_metrics = self.scheduler.get_system_metrics()
            self.logger.info(f"Final system metrics: {system_metrics}")

            worker_metrics = self.scheduler.get_worker_metrics()
            self.logger.info(f"Final worker metrics: {worker_metrics}")

            queue_empty = self.task_queue.is_empty()
            self.logger.info(f"Is task queue empty? {queue_empty}")

            pending_tasks = self.task_repository.get_by_status(TaskStatus.PENDING)
            for task in pending_tasks[:5]:
                self.logger.info(
                    f"Pending task: {task.id}, Dependencies: {task.dependency_ids}, Ready? {task.is_ready(self.scheduler.completed_task_ids)}")

        incomplete_tasks = len(remaining_tasks)
        max_allowed_incomplete = int(total_tasks * 0.05)

        self.logger.info(f"Incomplete tasks: {incomplete_tasks} (max allowed: {max_allowed_incomplete})")
        self.assertLessEqual(incomplete_tasks, max_allowed_incomplete,
                             f"{incomplete_tasks} tasks were not completed (allowed up to {max_allowed_incomplete})")


if __name__ == "__main__":
    unittest.main()
