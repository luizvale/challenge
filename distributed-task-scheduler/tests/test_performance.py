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
from src.use_cases.task_scheduler import TaskScheduler


class TaskSchedulerPerformanceTest(unittest.TestCase):
    """Performance tests for the TaskScheduler."""

    def setUp(self):
        """Setup executed before each test."""
        # Configure logger
        logging.basicConfig(level=logging.ERROR)
        self.logger = logging.getLogger("perf_test")

        # Configure components
        self.task_repository = MemoryTaskRepository()
        self.worker_registry = MemoryWorkerRegistry()
        self.task_queue = PriorityTaskQueue()
        self.task_executor = DefaultTaskExecutor()
        self.monitor = SystemMonitor(self.task_repository, self.worker_registry)

        # Register task handlers
        def fast_handler(task):
            # Simulate fast work (1–5 ms)
            time.sleep(random.uniform(0.001, 0.005))
            return "fast result"

        def medium_handler(task):
            # Simulate medium work (10–50 ms)
            time.sleep(random.uniform(0.01, 0.05))
            return "medium result"

        def slow_handler(task):
            # Simulate slow work (100–500 ms)
            time.sleep(random.uniform(0.1, 0.5))
            return "slow result"

        def random_failing_handler(task):
            # Randomly fails 30% of the time
            if random.random() < 0.3:
                raise ValueError("Random failure")
            time.sleep(random.uniform(0.01, 0.05))
            return "success"

        self.task_executor.register_handler("fast", fast_handler)
        self.task_executor.register_handler("medium", medium_handler)
        self.task_executor.register_handler("slow", slow_handler)
        self.task_executor.register_handler("random_fail", random_failing_handler)

        # Create scheduler
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

        # Start scheduler
        self.scheduler.start()

    def tearDown(self):
        """Cleanup executed after each test."""
        self.scheduler.stop()
        time.sleep(1)  # Wait for scheduler to fully stop

    def test_high_throughput(self):
        """High throughput processing test."""
        # Scale to 10 workers
        self.scheduler.scale_workers(10)

        # Number of tasks to create
        num_tasks = 1000
        task_ids = []

        # Measure scheduling time
        start_time = time.time()

        # Create and schedule tasks
        for i in range(num_tasks):
            # Distribute task types
            if i % 10 == 0:
                task_type = "slow"
            elif i % 3 == 0:
                task_type = "medium"
            else:
                task_type = "fast"

            task = Task(
                name=task_type,
                payload={"index": i},
                priority=random.choice(list(TaskPriority))
            )

            task_id = self.scheduler.schedule_task(task)
            task_ids.append(task_id)

        scheduling_time = time.time() - start_time
        print(f"Time to schedule {num_tasks} tasks: {scheduling_time:.2f} seconds")

        # Wait for all tasks to complete
        self.wait_for_completion(task_ids)

        # Calculate stats
        elapsed_time = time.time() - start_time
        throughput = num_tasks / elapsed_time

        print(f"Total processing time: {elapsed_time:.2f} seconds")
        print(f"Processing rate: {throughput:.2f} tasks/second")

        # Get system metrics
        metrics = self.scheduler.get_system_metrics()
        print(f"System metrics: {metrics}")

        # Verify all tasks were processed
        incomplete_tasks = 0
        for task_id in task_ids:
            status = self.scheduler.get_task_status(task_id)
            if status["status"] not in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value]:
                incomplete_tasks += 1

        self.assertEqual(incomplete_tasks, 0, f"{incomplete_tasks} tasks were not completed")
        self.assertGreaterEqual(throughput, 100, "Processing rate below expected threshold")

    def test_high_concurrency(self):
        """High concurrency test with multiple threads submitting tasks."""
        # Scale to 8 workers
        self.scheduler.scale_workers(8)

        # Test configuration
        num_threads = 5
        tasks_per_thread = 200
        total_tasks = num_threads * tasks_per_thread
        all_task_ids = []

        # Function to create tasks in a thread
        def create_tasks(thread_id):
            thread_task_ids = []
            for i in range(tasks_per_thread):
                # Alternate between task types
                task_type = ["fast", "medium", "random_fail"][i % 3]

                task = Task(
                    name=task_type,
                    payload={"thread": thread_id, "index": i},
                    priority=random.choice(list(TaskPriority))
                )

                task_id = self.scheduler.schedule_task(task)
                thread_task_ids.append(task_id)

            return thread_task_ids

        # Start threads to create tasks
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(create_tasks, t) for t in range(num_threads)]
            for future in futures:
                all_task_ids.extend(future.result())

        submission_time = time.time() - start_time
        print(f"Time to submit {total_tasks} tasks concurrently: {submission_time:.2f} seconds")

        # Wait for all tasks to complete
        self.wait_for_completion(all_task_ids)

        # Calculate stats
        elapsed_time = time.time() - start_time
        throughput = total_tasks / elapsed_time

        print(f"Total concurrent processing time: {elapsed_time:.2f} seconds")
        print(f"Concurrent processing rate: {throughput:.2f} tasks/second")

        # Verify all tasks were processed
        incomplete_tasks = 0
        failed_tasks = 0
        for task_id in all_task_ids:
            status = self.scheduler.get_task_status(task_id)
            if status["status"] not in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value]:
                incomplete_tasks += 1
            elif status["status"] == TaskStatus.FAILED.value:
                failed_tasks += 1

        print(f"Failed tasks: {failed_tasks} ({failed_tasks / total_tasks * 100:.1f}%)")
        self.assertEqual(incomplete_tasks, 0, f"{incomplete_tasks} tasks were not completed")

    def test_priority_effectiveness(self):
        """Test to verify if higher-priority tasks are processed earlier."""
        # Use only 2 workers to create queueing
        self.scheduler.scale_workers(2)

        # Create low-priority slow tasks
        slow_task_ids = []
        for i in range(20):
            task = Task(
                name="slow",
                payload={"index": i},
                priority=TaskPriority.LOW
            )
            task_id = self.scheduler.schedule_task(task)
            slow_task_ids.append(task_id)

        # Brief pause to allow slow tasks to enter queue
        time.sleep(0.2)

        # Create high-priority critical tasks
        critical_task_ids = []
        for i in range(5):
            task = Task(
                name="medium",
                payload={"index": i},
                priority=TaskPriority.CRITICAL
            )
            task_id = self.scheduler.schedule_task(task)
            critical_task_ids.append(task_id)

        # Wait for critical tasks to complete
        start_time = time.time()
        completed_critical = self.wait_for_completion(critical_task_ids)
        critical_completion_time = time.time() - start_time

        # Check how many slow tasks completed in that time
        completed_slow = 0
        for task_id in slow_task_ids:
            status = self.scheduler.get_task_status(task_id)
            if status["status"] in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value]:
                completed_slow += 1

        print(f"Critical tasks completed: {completed_critical} in {critical_completion_time:.2f} seconds")
        print(f"Slow tasks completed in the same period: {completed_slow}")

        self.assertEqual(completed_critical, 5, "Not all critical tasks completed")
        self.assertLess(completed_slow, 10, "Too many slow tasks completed before critical ones")

        # Wait for all tasks to complete for cleanup
        self.wait_for_completion(slow_task_ids)

    def test_dependency_chain_performance(self):
        """Performance test with long dependency chains."""
        # Scale to 5 workers
        self.scheduler.scale_workers(5)

        # Create a long chain of dependent tasks
        chain_length = 50
        task_ids = []

        # Create initial task
        initial_task = Task(
            name="fast",
            payload={"position": 0}
        )
        previous_id = self.scheduler.schedule_task(initial_task)
        task_ids.append(previous_id)

        # Create the rest of the chain
        for i in range(1, chain_length):
            dependent_task = Task(
                name="fast",
                payload={"position": i},
                dependency_ids={previous_id}
            )
            task_id = self.scheduler.schedule_task(dependent_task)
            previous_id = task_id
            task_ids.append(task_id)

        # Measure time to complete chain
        start_time = time.time()
        self.wait_for_completion(task_ids)
        chain_time = time.time() - start_time

        print(f"Time to process chain of {chain_length} dependent tasks: {chain_time:.2f} seconds")

        # Ensure all tasks were processed in order
        for i, task_id in enumerate(task_ids):
            task = self.task_repository.get(task_id)
            self.assertEqual(task.status, TaskStatus.COMPLETED)
            self.assertEqual(task.payload["position"], i)

    def wait_for_completion(self, task_ids, timeout=60):
        """Waits for tasks to complete with a timeout."""
        if not task_ids:
            return 0

        pending_tasks = set(task_ids)
        completed_tasks = set()

        start_time = time.time()
        while pending_tasks and (time.time() - start_time < timeout):
            for task_id in list(pending_tasks):
                status = self.scheduler.get_task_status(task_id)
                if status["status"] in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value]:
                    pending_tasks.remove(task_id)
                    completed_tasks.add(task_id)

            if pending_tasks:
                time.sleep(0.1)

        return len(completed_tasks)


if __name__ == "__main__":
    unittest.main()
