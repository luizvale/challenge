# examples/high_load_example.py
"""
Example for high load testing of the distributed task scheduler.
This will create and process a large number of tasks to demonstrate
performance under stress conditions.
"""

import time
import logging
import random
import threading
import argparse
from concurrent.futures import ThreadPoolExecutor

from src.core.entities.task import Task, TaskStatus, TaskPriority
from src.external.memory_repository import MemoryTaskRepository, MemoryWorkerRegistry
from src.external.task_queue import PriorityTaskQueue
from src.external.task_executor import DefaultTaskExecutor
from src.external.monitoring import SystemMonitor
from src.use_cases.optimized_task_scheduler import OptimizedTaskScheduler


# Task handlers with variable execution times
def very_fast_handler(task: Task) -> str:
    """Very fast task (1-10ms)."""
    duration = random.uniform(0.001, 0.01)
    time.sleep(duration)
    return f"Completed in {duration * 1000:.1f}ms"


def fast_handler(task: Task) -> str:
    """Fast task (10-50ms)."""
    duration = random.uniform(0.01, 0.05)
    time.sleep(duration)
    return f"Completed in {duration * 1000:.1f}ms"


def medium_handler(task: Task) -> str:
    """Medium task (50-200ms)."""
    duration = random.uniform(0.05, 0.2)
    time.sleep(duration)
    return f"Completed in {duration * 1000:.1f}ms"


def slow_handler(task: Task) -> str:
    """Slow task (200-500ms)."""
    duration = random.uniform(0.2, 0.5)
    time.sleep(duration)
    return f"Completed in {duration * 1000:.1f}ms"


def random_failing_handler(task: Task) -> str:
    """Task that fails randomly (15% chance)."""
    if random.random() < 0.15:
        raise ValueError("Random task failure")
    duration = random.uniform(0.02, 0.1)
    time.sleep(duration)
    return f"Completed in {duration * 1000:.1f}ms"


def cpu_intensive_handler(task: Task) -> str:
    """CPU intensive task."""
    start = time.time()
    # Simulate CPU-intensive work
    result = 0
    for i in range(1000000):
        result += i * i

    duration = time.time() - start
    return f"Computed sum of squares: {result}, took {duration * 1000:.1f}ms"


class PerformanceMonitor:
    """Monitors and reports on system performance."""

    def __init__(self, scheduler, interval=5, logger=None):
        self.scheduler = scheduler
        self.interval = interval
        self.logger = logger or logging.getLogger("perf_monitor")
        self.running = False
        self.thread = None
        self.start_time = None

        # Performance stats
        self.previous_completed = 0
        self.task_completion_times = []

    def start(self):
        """Start the performance monitor."""
        if self.running:
            return

        self.running = True
        self.start_time = time.time()
        self.thread = threading.Thread(target=self._monitor_loop)
        self.thread.daemon = True
        self.thread.start()
        self.logger.info("Performance monitor started")

    def stop(self):
        """Stop the performance monitor."""
        if not self.running:
            return

        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        self.logger.info("Performance monitor stopped")

    def _monitor_loop(self):
        """Main monitoring loop."""
        last_check = time.time()

        while self.running:
            current_time = time.time()

            if current_time - last_check >= self.interval:
                self._gather_metrics()
                last_check = current_time

            time.sleep(0.5)

    def _gather_metrics(self):
        """Gather and log performance metrics."""
        # Get current system metrics
        system_metrics = self.scheduler.get_system_metrics()

        # Get worker metrics
        worker_metrics = self.scheduler.get_worker_metrics()

        # Calculate throughput
        elapsed = time.time() - self.start_time
        current_completed = system_metrics.get("completed_tasks", 0)
        overall_throughput = current_completed / elapsed if elapsed > 0 else 0

        # Calculate recent throughput
        period_throughput = (current_completed - self.previous_completed) / self.interval
        self.previous_completed = current_completed

        # Get task queue info
        task_status_counts = system_metrics.get("status_distribution", {})

        # Get worker utilization
        worker_total = worker_metrics.get("total", 0)
        worker_busy = worker_metrics.get("busy", 0)
        worker_utilization = worker_busy / worker_total if worker_total > 0 else 0

        # Log the metrics
        self.logger.info(
            f"=== Performance Metrics ===\n"
            f"Runtime: {elapsed:.1f}s | "
            f"Tasks completed: {current_completed} | "
            f"Overall throughput: {overall_throughput:.2f} tasks/s | "
            f"Recent throughput: {period_throughput:.2f} tasks/s\n"
            f"Task status: {task_status_counts}\n"
            f"Workers: {worker_total} total, {worker_busy} busy, "
            f"Utilization: {worker_utilization * 100:.1f}%"
        )


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="High load testing for distributed task scheduler")
    parser.add_argument("--tasks", type=int, default=1000, help="Total number of tasks to create")
    parser.add_argument("--workers", type=int, default=10, help="Number of workers to start with")
    parser.add_argument("--batch-size", type=int, default=20, help="Batch size for scheduler")
    parser.add_argument("--max-workers", type=int, default=30, help="Maximum number of workers")
    parser.add_argument("--threads", type=int, default=5, help="Number of submission threads")
    parser.add_argument("--timeout", type=int, default=180, help="Timeout in seconds")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING"], default="INFO",
                        help="Logging level")
    return parser.parse_args()


def create_tasks_thread(thread_id, num_tasks, scheduler, task_types, priorities):
    """Thread function to create tasks."""
    logger = logging.getLogger(f"thread-{thread_id}")
    task_ids = []

    for i in range(num_tasks):
        # Select random task type and priority
        task_type = random.choice(task_types)
        priority = random.choice(priorities)

        # Create task with appropriate payload
        task = Task(
            name=task_type,
            payload={"thread_id": thread_id, "task_index": i, "created_at": time.time()},
            priority=priority
        )

        # Add dependency to previous task (10% chance)
        if random.random() < 0.1 and task_ids:
            previous_id = random.choice(task_ids)
            task.dependency_ids = {previous_id}

        # Schedule the task
        task_id = scheduler.schedule_task(task)
        task_ids.append(task_id)

    logger.debug(f"Thread {thread_id} created {len(task_ids)} tasks")
    return task_ids


def main():
    # Parse command line arguments
    args = parse_args()

    # Set up logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("high_load")

    # Log the test configuration
    logger.info(f"Starting high load test with configuration:")
    logger.info(f"  Total tasks: {args.tasks}")
    logger.info(f"  Workers: {args.workers} (max: {args.max_workers})")
    logger.info(f"  Batch size: {args.batch_size}")
    logger.info(f"  Submission threads: {args.threads}")
    logger.info(f"  Timeout: {args.timeout} seconds")

    # Set up components
    task_repository = MemoryTaskRepository()
    worker_registry = MemoryWorkerRegistry()
    task_queue = PriorityTaskQueue()
    task_executor = DefaultTaskExecutor()
    monitor = SystemMonitor(
        task_repository=task_repository,
        worker_registry=worker_registry,
        logger=logger
    )

    # Register task handlers
    task_executor.register_handler("very_fast", very_fast_handler)
    task_executor.register_handler("fast", fast_handler)
    task_executor.register_handler("medium", medium_handler)
    task_executor.register_handler("slow", slow_handler)
    task_executor.register_handler("random_fail", random_failing_handler)
    task_executor.register_handler("cpu_intensive", cpu_intensive_handler)

    # Create optimized scheduler
    scheduler = OptimizedTaskScheduler(
        task_repository=task_repository,
        worker_registry=worker_registry,
        task_queue=task_queue,
        task_executor=task_executor,
        task_monitor=monitor,
        batch_size=args.batch_size,
        adaptive_workers=True,
        min_workers=args.workers // 2,
        max_workers=args.max_workers,
        scaling_check_interval=5,
        logger=logger
    )

    # Initialize workers
    scheduler.scale_workers(args.workers)

    # Start the scheduler
    scheduler.start()
    logger.info(f"Scheduler started with {args.workers} workers")

    # Create performance monitor
    perf_monitor = PerformanceMonitor(scheduler, interval=5, logger=logger)
    perf_monitor.start()

    try:
        # Task configuration
        task_types = [
            "very_fast", "very_fast", "very_fast", "very_fast",  # 40% very fast
            "fast", "fast", "fast",  # 30% fast
            "medium", "medium",  # 20% medium
            "slow",  # 10% slow
            "random_fail", "random_fail",  # 20% with random failures
            "cpu_intensive"  # 10% CPU intensive
        ]

        priorities = [
            TaskPriority.LOW,  # 10% low
            TaskPriority.NORMAL, TaskPriority.NORMAL,  # 20% normal
            TaskPriority.HIGH, TaskPriority.HIGH, TaskPriority.HIGH,  # 30% high
            TaskPriority.CRITICAL, TaskPriority.CRITICAL,  # 20% critical
        ]

        # Start task creation
        logger.info(f"Starting task creation with {args.threads} threads")
        start_time = time.time()
        all_task_ids = []

        # Create tasks using multiple threads
        tasks_per_thread = args.tasks // args.threads
        with ThreadPoolExecutor(max_workers=args.threads) as executor:
            futures = [
                executor.submit(
                    create_tasks_thread,
                    i,
                    tasks_per_thread + (1 if i < args.tasks % args.threads else 0),
                    scheduler,
                    task_types,
                    priorities
                )
                for i in range(args.threads)
            ]

            # Collect task IDs
            for future in futures:
                thread_task_ids = future.result()
                all_task_ids.extend(thread_task_ids)

        submission_time = time.time() - start_time
        logger.info(f"Task creation completed in {submission_time:.2f} seconds")
        logger.info(f"Created {len(all_task_ids)} tasks")

        # Wait for task completion with timeout
        remaining_tasks = set(all_task_ids)
        completed_tasks = set()
        start_wait_time = time.time()

        logger.info(f"Waiting for all tasks to complete (timeout: {args.timeout}s)")

        while remaining_tasks and (time.time() - start_wait_time < args.timeout):
            # Check task status in batches to avoid overwhelming the system
            check_batch = list(remaining_tasks)[:100]

            for task_id in check_batch:
                status = scheduler.get_task_status(task_id)
                if status["status"] in [
                    TaskStatus.COMPLETED.value,
                    TaskStatus.FAILED.value,
                    TaskStatus.CANCELED.value,
                    TaskStatus.TIMEOUT.value
                ]:
                    remaining_tasks.remove(task_id)
                    completed_tasks.add(task_id)

            # Short sleep between checks
            time.sleep(1)

        # Calculate final stats
        total_time = time.time() - start_time
        completion_percentage = (len(completed_tasks) / len(all_task_ids)) * 100
        overall_throughput = len(completed_tasks) / total_time

        logger.info("=== Test Results ===")
        logger.info(f"Test duration: {total_time:.2f} seconds")
        logger.info(f"Tasks completed: {len(completed_tasks)}/{len(all_task_ids)} ({completion_percentage:.1f}%)")
        logger.info(f"Overall throughput: {overall_throughput:.2f} tasks/second")

        # Get final system metrics
        system_metrics = scheduler.get_system_metrics()
        logger.info(f"Final system metrics: {system_metrics}")

        # Check success criteria
        if completion_percentage >= 95:
            logger.info("TEST PASSED: At least 95% of tasks completed successfully")
        else:
            logger.warning(f"TEST FAILED: Only {completion_percentage:.1f}% of tasks completed (target: 95%)")

    finally:
        # Stop the monitoring
        perf_monitor.stop()

        # Stop the scheduler
        scheduler.stop()
        logger.info("Scheduler stopped")


if __name__ == "__main__":
    main()