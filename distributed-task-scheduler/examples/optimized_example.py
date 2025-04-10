# examples/optimized_example.py
"""
Example demonstrating the usage of the OptimizedTaskScheduler.
This shows the improved performance with batch processing and adaptive scaling.
"""

import time
import logging
import random
from typing import Dict, Any

from src.core.entities.task import Task, TaskStatus, TaskPriority
from src.external.memory_repository import MemoryTaskRepository, MemoryWorkerRegistry
from src.external.task_queue import PriorityTaskQueue
from src.external.task_executor import DefaultTaskExecutor
from src.external.monitoring import SystemMonitor
from src.use_cases.optimized_task_scheduler import OptimizedTaskScheduler


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
    raise ValueError("This task always fails")


def wait_for_tasks_completion(task_ids, scheduler, logger, timeout=60):
    """Wait for tasks to complete and print their results."""
    tasks_to_monitor = set(task_ids)
    completed_tasks = set()

    logger.info(f"Waiting for tasks to complete: {tasks_to_monitor}")

    start_time = time.time()

    while completed_tasks != tasks_to_monitor and (time.time() - start_time < timeout):
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

    if completed_tasks != tasks_to_monitor:
        logger.warning(f"Timeout: {len(tasks_to_monitor) - len(completed_tasks)} tasks did not complete in time")

    return len(completed_tasks)


def main():
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("optimized_example")

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
    task_executor.register_handler("add_numbers", add_numbers_handler)
    task_executor.register_handler("multiply_numbers", multiply_numbers_handler)
    task_executor.register_handler("process_text", process_text_handler)
    task_executor.register_handler("failing_task", failing_handler)

    # Create the optimized scheduler
    scheduler = OptimizedTaskScheduler(
        task_repository=task_repository,
        worker_registry=worker_registry,
        task_queue=task_queue,
        task_executor=task_executor,
        task_monitor=monitor,
        batch_size=20,  # Process in batches of 20
        adaptive_workers=True,  # Enable dynamic scaling
        min_workers=3,  # Minimum 3 workers
        max_workers=10,  # Maximum 10 workers
        logger=logger
    )

    # Start with 5 workers
    scheduler.scale_workers(5)

    # Start the scheduler
    scheduler.start()
    logger.info("Optimized scheduler started with 5 workers")

    try:
        # Example 1: Multiple batches of tasks
        logger.info("=== Example 1: Processing Multiple Batches ===")

        # Create 50 tasks
        batch_tasks = 50
        batch_task_ids = []

        logger.info(f"Creating {batch_tasks} tasks for batch processing")
        start_time = time.time()

        for i in range(batch_tasks):
            # Mix of task types
            if i % 3 == 0:
                task_type = "multiply_numbers"
                payload = {"a": i, "b": i + 1}
            else:
                task_type = "add_numbers"
                payload = {"a": i * 10, "b": i * 5}

            task = Task(
                name=task_type,
                payload=payload,
                priority=random.choice(list(TaskPriority))
            )

            task_id = scheduler.schedule_task(task)
            batch_task_ids.append(task_id)

        submission_time = time.time() - start_time
        logger.info(f"Tasks submission time: {submission_time:.2f} seconds")

        # Wait for completion and measure throughput
        batch_start = time.time()
        completed = wait_for_tasks_completion(batch_task_ids, scheduler, logger)
        batch_time = time.time() - batch_start

        throughput = completed / batch_time
        logger.info(f"Processed {completed} tasks in {batch_time:.2f} seconds")
        logger.info(f"Throughput: {throughput:.2f} tasks/second")

        # Get worker metrics to see dynamic scaling in action
        worker_metrics = scheduler.get_worker_metrics()
        logger.info(f"Worker metrics after batch processing: {worker_metrics}")

        # Example 2: Complex dependency chain
        logger.info("\n=== Example 2: Complex Dependency Chain ===")

        # Create a chain where:
        #   Task1 -> Task2 -> Task3 -> Task4
        #      |                ^
        #      v                |
        #   Task5 -> Task6 -----+

        # Create the starting tasks
        task1 = Task(
            name="add_numbers",
            payload={"a": 10, "b": 20},
            priority=TaskPriority.HIGH
        )
        task1_id = scheduler.schedule_task(task1)
        logger.info(f"Created root task: {task1_id}")

        # Create two dependent chains
        # Chain 1: Task1 -> Task2 -> Task3 -> Task4
        task2 = Task(
            name="multiply_numbers",
            payload={"a": 2, "b": 3},
            dependency_ids={task1_id},
            priority=TaskPriority.NORMAL
        )
        task2_id = scheduler.schedule_task(task2)
        logger.info(f"Created task2 (depends on task1): {task2_id}")

        task3 = Task(
            name="process_text",
            payload={"text": "This is the first branch"},
            dependency_ids={task2_id},
            priority=TaskPriority.NORMAL
        )
        task3_id = scheduler.schedule_task(task3)
        logger.info(f"Created task3 (depends on task2): {task3_id}")

        # Chain 2: Task1 -> Task5 -> Task6
        task5 = Task(
            name="add_numbers",
            payload={"a": 100, "b": 200},
            dependency_ids={task1_id},
            priority=TaskPriority.HIGH
        )
        task5_id = scheduler.schedule_task(task5)
        logger.info(f"Created task5 (depends on task1): {task5_id}")

        task6 = Task(
            name="multiply_numbers",
            payload={"a": 5, "b": 10},
            dependency_ids={task5_id},
            priority=TaskPriority.HIGH
        )
        task6_id = scheduler.schedule_task(task6)
        logger.info(f"Created task6 (depends on task5): {task6_id}")

        # Final task with multiple dependencies
        task4 = Task(
            name="process_text",
            payload={"text": "This is the final task with multiple dependencies"},
            dependency_ids={task3_id, task6_id},
            priority=TaskPriority.CRITICAL
        )
        task4_id = scheduler.schedule_task(task4)
        logger.info(f"Created final task4 (depends on task3 and task6): {task4_id}")

        # Wait for all tasks to complete
        logger.info("Waiting for complex dependency chain to complete")
        chain_task_ids = [task1_id, task2_id, task3_id, task4_id, task5_id, task6_id]
        wait_for_tasks_completion(chain_task_ids, scheduler, logger)

        # Example 3: Adaptive Worker Scaling
        logger.info("\n=== Example 3: Adaptive Worker Scaling ===")

        # Log initial worker count
        workers = scheduler.get_worker_status()
        logger.info(f"Initial worker count: {len(workers)}")

        # Create a large batch of tasks to trigger scaling up
        logger.info("Creating large batch of tasks to trigger scaling up")
        scale_task_ids = []
        scale_tasks = 100

        for i in range(scale_tasks):
            task = Task(
                name="slow_task" if i % 10 == 0 else "add_numbers",
                payload={"a": i, "b": i * 2},
                priority=TaskPriority.NORMAL
            )
            task_id = scheduler.schedule_task(task)
            scale_task_ids.append(task_id)

        # Wait a bit and check worker count
        time.sleep(10)
        workers = scheduler.get_worker_status()
        logger.info(f"Worker count after creating many tasks: {len(workers)}")

        # Wait for tasks to complete
        wait_for_tasks_completion(scale_task_ids, scheduler, logger, timeout=120)

        # Wait for scale down
        logger.info("Waiting for workers to scale down due to decreased load")
        time.sleep(20)
        workers = scheduler.get_worker_status()
        logger.info(f"Worker count after tasks completed: {len(workers)}")

        # Example 4: System Metrics
        logger.info("\n=== Example 4: System Metrics ===")

        # Get various metrics
        system_metrics = scheduler.get_system_metrics()
        logger.info(f"System metrics: {system_metrics}")

        worker_metrics = scheduler.get_worker_metrics()
        logger.info(f"All workers metrics: {worker_metrics}")

        # Get metrics for best and worst performing workers
        workers = scheduler.get_worker_status()
        if workers:
            # Get metrics for the first worker
            first_worker_id = workers[0]["id"]
            first_worker_metrics = scheduler.get_worker_metrics(first_worker_id)
            logger.info(f"Metrics for worker {first_worker_id}: {first_worker_metrics}")

    finally:
        # Stop the scheduler
        scheduler.stop()
        logger.info("Scheduler stopped")


if __name__ == "__main__":
    main()