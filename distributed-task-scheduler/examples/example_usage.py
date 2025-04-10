# examples/example_usage.py
import os
import sys
import time
import logging
from typing import Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from src.core.entities.task import Task, TaskStatus, TaskPriority
from src.external.memory_repository import MemoryTaskRepository, MemoryWorkerRegistry
from src.external.task_queue import PriorityTaskQueue
from src.external.task_executor import DefaultTaskExecutor
from src.external.monitoring import SystemMonitor
from src.use_cases.task_scheduler import TaskScheduler


def add_numbers_handler(task: Task) -> int:
    """Handler for 'add_numbers' task."""
    time.sleep(2)  # Simulate work
    a = task.payload.get("a", 0)
    b = task.payload.get("b", 0)
    return a + b


def multiply_numbers_handler(task: Task) -> int:
    """Handler for 'multiply_numbers' task."""
    time.sleep(3)  # Simulate work
    a = task.payload.get("a", 0)
    b = task.payload.get("b", 0)
    return a * b


def process_text_handler(task: Task) -> Dict[str, Any]:
    """Handler for 'process_text' task."""
    time.sleep(2)  # Simulate work
    text = task.payload.get("text", "")
    return {
        "word_count": len(text.split()),
        "char_count": len(text),
        "uppercase": text.upper()
    }


def failing_handler(task: Task) -> None:
    """Handler that always fails."""
    time.sleep(1)  # Simulate work
    raise Exception("This task always fails")


def main():
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("example")

    # Set up components
    task_repository = MemoryTaskRepository()
    worker_registry = MemoryWorkerRegistry()
    task_queue = PriorityTaskQueue()
    task_executor = DefaultTaskExecutor()

    # Create monitor
    monitor = SystemMonitor(
        task_repository=task_repository,
        worker_registry=worker_registry,
        logger=logger
    )

    # Register task handlers
    task_executor.register_handler("add_numbers", add_numbers_handler)
    task_executor.register_handler("multiply_numbers", multiply_numbers_handler)
    task_executor.register_handler("process_text", process_text_handler)
    task_executor.register_handler("failing_task", failing_handler)

    # Create scheduler
    scheduler = TaskScheduler(
        task_repository=task_repository,
        worker_registry=worker_registry,
        task_queue=task_queue,
        task_executor=task_executor,
        task_monitor=monitor,
        logger=logger
    )

    # Scale to 3 workers
    scheduler.scale_workers(3)

    # Start the scheduler
    scheduler.start()

    try:
        # Example 1: Create simple tasks
        logger.info("=== Example 1: Creating Simple Tasks ===")

        task1_id = scheduler.schedule_task(
            Task(
                name="add_numbers",
                payload={"a": 5, "b": 7},
                priority=TaskPriority.NORMAL
            )
        )
        logger.info(f"Created task {task1_id}")

        task2_id = scheduler.schedule_task(
            Task(
                name="multiply_numbers",
                payload={"a": 6, "b": 8},
                priority=TaskPriority.HIGH
            )
        )
        logger.info(f"Created task {task2_id}")

        # Wait for tasks to complete
        wait_for_tasks_completion([task1_id, task2_id], scheduler, logger)

        # Example 2: Create dependent tasks
        logger.info("=== Example 2: Creating Dependent Tasks ===")

        # Create a task
        parent_task_id = scheduler.schedule_task(
            Task(
                name="add_numbers",
                payload={"a": 10, "b": 20},
            )
        )
        logger.info(f"Created parent task {parent_task_id}")

        # Create a dependent task
        child_task_id = scheduler.schedule_task(
            Task(
                name="multiply_numbers",
                payload={"a": 2, "b": 3},
                dependency_ids={parent_task_id}
            )
        )
        logger.info(f"Created child task {child_task_id} dependent on {parent_task_id}")

        # Wait for tasks to complete
        wait_for_tasks_completion([parent_task_id, child_task_id], scheduler, logger)

        # Example 3: Task cancellation
        logger.info("=== Example 3: Task Cancellation ===")

        # Create a task with a long timeout
        cancel_task_id = scheduler.schedule_task(
            Task(
                name="process_text",
                payload={"text": "This task will be canceled"},
                timeout_seconds=60
            )
        )
        logger.info(f"Created task {cancel_task_id} to be canceled")

        # Wait briefly
        time.sleep(1)

        # Cancel the task
        cancel_result = scheduler.cancel_task(cancel_task_id)
        logger.info(f"Task cancellation result: {cancel_result}")

        # Check the task status
        task_status = scheduler.get_task_status(cancel_task_id)
        logger.info(f"Canceled task status: {task_status['status']}")

        # Example 4: Failing task with retries
        logger.info("=== Example 4: Failing Task with Retries ===")

        failing_task_id = scheduler.schedule_task(
            Task(
                name="failing_task",
                payload={},
                max_retries=2  # Will try 3 times in total (original + 2 retries)
            )
        )
        logger.info(f"Created failing task {failing_task_id}")

        # Wait for task to complete all retries and fail
        wait_for_tasks_completion([failing_task_id], scheduler, logger)

        # Example 5: Worker monitoring
        logger.info("=== Example 5: Worker Monitoring ===")

        # Get worker statuses
        worker_statuses = scheduler.get_worker_status()
        logger.info(f"Workers: {worker_statuses}")

        # Get worker metrics
        worker_metrics = scheduler.get_worker_metrics()
        logger.info(f"Worker metrics: {worker_metrics}")

        # Example 6: Task chain with multiple dependencies
        logger.info("=== Example 6: Task Chain with Multiple Dependencies ===")

        # Create initial tasks
        task_a = scheduler.schedule_task(
            Task(
                name="add_numbers",
                payload={"a": 5, "b": 5},
            )
        )
        logger.info(f"Created task A: {task_a}")

        task_b = scheduler.schedule_task(
            Task(
                name="multiply_numbers",
                payload={"a": 2, "b": 3},
            )
        )
        logger.info(f"Created task B: {task_b}")

        # Create a task that depends on both A and B
        task_c = scheduler.schedule_task(
            Task(
                name="process_text",
                payload={"text": "This task depends on multiple tasks"},
                dependency_ids={task_a, task_b}
            )
        )
        logger.info(f"Created task C: {task_c} (depends on A and B)")

        # Wait for all tasks to complete
        wait_for_tasks_completion([task_a, task_b, task_c], scheduler, logger)

        # Example 7: System metrics
        logger.info("=== Example 7: System Metrics ===")

        # Get system metrics
        system_metrics = scheduler.get_system_metrics()
        logger.info(f"System metrics: {system_metrics}")

        # Get task metrics
        task_metrics = scheduler.get_task_metrics()
        logger.info(f"Task metrics: {task_metrics}")

        # Get metrics for a specific task
        task_detail = scheduler.get_task_metrics(task_a)
        logger.info(f"Details for task {task_a}: {task_detail}")

    finally:
        # Stop the scheduler
        scheduler.stop()
        logger.info("Scheduler stopped")


def wait_for_tasks_completion(task_ids, scheduler, logger):
    """Wait for tasks to complete and print their results."""
    tasks_to_monitor = set(task_ids)
    completed_tasks = set()

    logger.info(f"Waiting for tasks to complete: {tasks_to_monitor}")

    while completed_tasks != tasks_to_monitor:
        for task_id in tasks_to_monitor - completed_tasks:
            status = scheduler.get_task_status(task_id)
            if status["status"] in [
                TaskStatus.COMPLETED.value,
                TaskStatus.FAILED.value,
                TaskStatus.CANCELED.value,
                TaskStatus.TIMEOUT.value
            ]:
                logger.info(f"Task {task_id} completed with status: {status['status']}")
                if "result" in status and status["result"] is not None:
                    logger.info(f"Result: {status['result']}")
                if "error" in status and status["error"] is not None:
                    logger.info(f"Error: {status['error']}")
                completed_tasks.add(task_id)

        if completed_tasks != tasks_to_monitor:
            time.sleep(0.5)


if __name__ == "__main__":
    main()