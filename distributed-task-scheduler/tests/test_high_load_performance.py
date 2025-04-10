# tests/test_high_load.py
import time
import logging
import random
import unittest
from concurrent.futures import ThreadPoolExecutor

from src.core.entities.task import Task, TaskStatus, TaskPriority
from src.external.memory_repository import MemoryTaskRepository, MemoryWorkerRegistry
from src.external.task_queue import PriorityTaskQueue
from src.external.task_executor import DefaultTaskExecutor
from src.external.monitoring import SystemMonitor
from src.use_cases.optimized_task_scheduler import OptimizedTaskScheduler

from src.core.entities.worker import WorkerStatus


class HighLoadPerformanceTest(unittest.TestCase):
    """Performance tests for the optimized task scheduler under high load."""

    def setUp(self):
        """Setup run before each test."""
        # Configure logger
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("high_load_test")

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

        # Register task handlers
        def fast_handler(task):
            # Simulate fast work (1-5ms)
            time.sleep(random.uniform(0.001, 0.005))
            return "fast result"

        def medium_handler(task):
            # Simulate medium work (10-50ms)
            time.sleep(random.uniform(0.01, 0.05))
            return "medium result"

        def slow_handler(task):
            # Simulate slow work (100-300ms)
            time.sleep(random.uniform(0.1, 0.3))
            return "slow result"

        def random_failing_handler(task):
            # Random failure 10% of the time
            if random.random() < 0.1:
                raise ValueError("Random failure")
            time.sleep(random.uniform(0.01, 0.05))
            return "success"

        self.task_executor.register_handler("fast", fast_handler)
        self.task_executor.register_handler("medium", medium_handler)
        self.task_executor.register_handler("slow", slow_handler)
        self.task_executor.register_handler("random_fail", random_failing_handler)

        # Create optimized scheduler
        self.scheduler = OptimizedTaskScheduler(
            task_repository=self.task_repository,
            worker_registry=self.worker_registry,
            task_queue=self.task_queue,
            task_executor=self.task_executor,
            task_monitor=self.monitor,
            batch_size=20,  # Process tasks in batches of 20
            adaptive_workers=True,  # Enable dynamic worker scaling
            min_workers=5,
            max_workers=30,
            scaling_check_interval=5,
            logger=self.logger
        )

        # Start the scheduler
        self.scheduler.start()
        self.logger.info("Optimized scheduler started")

    def tearDown(self):
        """Cleanup run after each test."""
        self.logger.info("Stopping scheduler")
        self.scheduler.stop()
        time.sleep(1)  # Ensure scheduler is fully stopped
        self.logger.info("Scheduler stopped")

    def test_high_concurrency_1000_tasks(self):
        """Test high concurrency with 1000 tasks."""
        # Scale to initial workers count
        self.scheduler.scale_workers(10)
        self.logger.info(f"Scaled to 10 workers")

        # Test settings
        num_threads = 5
        tasks_per_thread = 200
        total_tasks = num_threads * tasks_per_thread

        self.logger.info(
            f"Starting test with {num_threads} threads and {tasks_per_thread} tasks per thread ({total_tasks} total)")

        # Mapping of task_id -> (thread_id, task_index) for tracking
        task_mapping = {}
        all_task_ids = []

        # Function to create tasks in a thread
        def create_tasks(thread_id):
            thread_task_ids = []
            for i in range(tasks_per_thread):
                # Distribute task types with realistic mix
                if i % 20 == 0:
                    task_type = "slow"
                elif i % 5 == 0:
                    task_type = "random_fail"
                elif i % 3 == 0:
                    task_type = "medium"
                else:
                    task_type = "fast"

                # Realistic priority distribution
                if i % 50 == 0:
                    priority = TaskPriority.CRITICAL
                elif i % 10 == 0:
                    priority = TaskPriority.HIGH
                elif i % 4 == 0:
                    priority = TaskPriority.LOW
                else:
                    priority = TaskPriority.NORMAL

                task = Task(
                    name=task_type,
                    payload={"thread": thread_id, "index": i},
                    priority=priority
                )

                # Create some dependency chains (5% of tasks)
                if i > 0 and i % 20 == 0 and thread_task_ids:
                    # Make this task depend on previous task
                    previous_id = thread_task_ids[-1]
                    task.dependency_ids = {previous_id}

                task_id = self.scheduler.schedule_task(task)
                thread_task_ids.append(task_id)
                task_mapping[task_id] = (thread_id, i)

            return thread_task_ids

        # Start threads to create tasks
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(create_tasks, t) for t in range(num_threads)]

            for future in futures:
                all_task_ids.extend(future.result())

        submission_time = time.time() - start_time
        self.logger.info(f"Time to submit {total_tasks} tasks concurrently: {submission_time:.2f} seconds")

        # Monitor progress periodically
        max_wait = 120  # 2 minutes timeout
        check_interval = 5  # seconds

        self.logger.info(f"Waiting for tasks to complete with {max_wait} seconds timeout")

        start_wait_time = time.time()
        last_check_time = start_wait_time
        last_completed = 0

        while True:
            current_time = time.time()
            elapsed = current_time - start_wait_time

            # Check if we've hit the timeout
            if elapsed > max_wait:
                self.logger.warning(f"Hit timeout after {elapsed:.1f} seconds")
                break

            # Periodic status check
            if current_time - last_check_time >= check_interval:
                # Count tasks by status
                all_tasks = self.scheduler.list_tasks()
                status_counts = {}
                completed_count = 0

                for task in all_tasks:
                    status = task["status"]
                    status_counts[status] = status_counts.get(status, 0) + 1
                    if status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value,
                                  TaskStatus.CANCELED.value, TaskStatus.TIMEOUT.value]:
                        completed_count += 1

                # Calculate completion rate
                completion_percentage = (completed_count / total_tasks) * 100

                # Calculate throughput
                throughput_since_last = (completed_count - last_completed) / check_interval
                last_completed = completed_count

                # Get worker info
                workers = self.scheduler.get_worker_status()
                worker_status = {
                    "total": len(workers),
                    "busy": sum(1 for w in workers if w["status"] == WorkerStatus.BUSY.value),
                    "idle": sum(1 for w in workers if w["status"] == WorkerStatus.IDLE.value),
                    "down": sum(1 for w in workers if w["status"] == WorkerStatus.DOWN.value)
                }

                # Log progress
                self.logger.info(
                    f"Progress after {elapsed:.1f}s: "
                    f"Completed: {completed_count}/{total_tasks} ({completion_percentage:.1f}%), "
                    f"Status: {status_counts}, "
                    f"Workers: {worker_status}, "
                    f"Throughput: {throughput_since_last:.1f} tasks/s"
                )

                # Check if all tasks are completed
                if completed_count == total_tasks:
                    self.logger.info("All tasks completed!")
                    break

                # Get system metrics
                system_metrics = self.scheduler.get_system_metrics()
                self.logger.info(f"System metrics: {system_metrics}")

                last_check_time = current_time

            time.sleep(0.1)

        # Final assessment
        end_time = time.time()
        total_elapsed = end_time - start_time

        # Get final task counts
        final_tasks = self.scheduler.list_tasks()
        final_status_counts = {}
        for task in final_tasks:
            status = task["status"]
            final_status_counts[status] = final_status_counts.get(status, 0) + 1

        completed_count = sum(
            final_status_counts.get(status.value, 0)
            for status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELED, TaskStatus.TIMEOUT]
        )

        self.logger.info(f"Final status counts: {final_status_counts}")
        self.logger.info(f"Total elapsed time: {total_elapsed:.2f} seconds")
        self.logger.info(f"Overall throughput: {completed_count / total_elapsed:.2f} tasks/second")

        # Check success criteria (95% completion rate is acceptable)
        completion_rate = completed_count / total_tasks
        self.logger.info(f"Completion rate: {completion_rate:.2%}")

        self.assertGreaterEqual(completion_rate, 0.95,
                                f"Completion rate too low: {completion_rate:.2%}, expected at least 95%")