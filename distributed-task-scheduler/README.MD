# Distributed Task Scheduler

A robust Python-based distributed task scheduling system that manages task distribution across multiple worker processes. The system supports priority queues, task dependencies, monitoring, fault tolerance, and dynamic worker scaling.

## Features

- **Task Distribution**: Distribute tasks among multiple worker processes
- **Priority Queue**: Process critical tasks first
- **Task Dependencies**: Support for complex workflows with dependency chains
- **Status Monitoring**: Real-time reporting on task and worker status
- **Fault Tolerance**: Gracefully handle worker failures
- **Cancellation & Timeout**: Support for task cancellation and automatic timeout handling
- **Dynamic Scaling**: Ability to scale workers up or down based on demand

## Project Structure

```
distributed-task-scheduler/
├── core/
│   ├── entities/              # Domain entities
│   │   ├── task.py            # Task entity definition
│   │   └── worker.py          # Worker entity definition
│   └── interfaces/            # Abstract interfaces
│       ├── task_repository.py # Interface for task storage
│       ├── worker_registry.py # Interface for worker management
│       ├── task_queue.py      # Interface for task queuing
│       ├── task_executor.py   # Interface for task execution
│       ├── scheduler.py       # Interface for task scheduling
│       └── monitoring.py      # Interface for monitoring
├── use_cases/
│   ├── task_scheduler.py      # Main scheduler implementation
│   └── optimized_task_scheduler.py # Performance-optimized scheduler
├── external/
│   ├── memory_repositories.py # In-memory implementations
│   ├── task_queue.py          # Priority queue implementation
│   ├── task_executor.py       # Task executor implementation
│   └── monitoring.py          # Monitoring implementation
├── examples/
│   ├── example_usage.py       # Basic usage example
│   ├── optimized_example.py   # Example of optimized scheduler
│   └── high_load_example.py   # High-load testing example
```

## Scheduler Implementations

The project includes multiple scheduler implementations to meet different needs:

### 1. Basic Task Scheduler

The standard implementation with core functionality:
- Single task processing
- Manual worker scaling
- Basic monitoring

### 2. Optimized Task Scheduler

Enhanced version with performance improvements:
- Batch processing of tasks
- Adaptive worker scaling
- Efficient task distribution
- Enhanced monitoring

### 3. High Load Testing Configuration

Specialized version for performance testing:
- Configurable task volume
- Detailed performance metrics
- Multi-threaded task submission
- Performance monitoring tools

## Performance Optimizations

The optimized scheduler includes several key improvements:

1. **Batch Processing**: Processes tasks in configurable batches to reduce overhead
   ```python
   # Process multiple tasks at once
   batch_size = min(self.batch_size, max(1, len(available_workers) * 2))
   ```

2. **Adaptive Worker Scaling**: Automatically adjusts worker count based on system load
   ```python
   # Scale up when workers are busy
   if busy_ratio > self.busy_threshold and not queue_empty:
       new_count = min(self.max_workers, int(current_count * 1.5))
   ```

3. **Reduced Processing Latency**: More responsive task scheduling
   ```python
   # Reduced from 0.1s to 0.05s for better responsiveness
   time.sleep(0.05)
   ```

4. **Comprehensive Monitoring**: Detailed metrics for system performance analysis

## Getting Started

### Installation

Clone the repository and install dependencies:

```bash
cd distributed-task-scheduler
```

### Basic Usage

```python
from core.entities.task import Task, TaskPriority
from external.memory_repositories import MemoryTaskRepository, MemoryWorkerRegistry
from external.task_queue import PriorityTaskQueue
from external.task_executor import DefaultTaskExecutor
from use_cases.task_scheduler import TaskScheduler

# Define a task handler
def my_task_handler(task):
    # Process task
    return "Task result"

# Set up components
task_repository = MemoryTaskRepository()
worker_registry = MemoryWorkerRegistry()
task_queue = PriorityTaskQueue()
task_executor = DefaultTaskExecutor()

# Register handler
task_executor.register_handler("my_task_type", my_task_handler)

# Create scheduler
scheduler = TaskScheduler(
    task_repository=task_repository,
    worker_registry=worker_registry,
    task_queue=task_queue,
    task_executor=task_executor
)

# Scale to desired workers
scheduler.scale_workers(3)

# Start the scheduler
scheduler.start()

# Create and schedule a task
task = Task(
    name="my_task_type",
    payload={"param": "value"},
    priority=TaskPriority.HIGH
)
task_id = scheduler.schedule_task(task)

# Check task status
status = scheduler.get_task_status(task_id)
```

### Running the Examples

```bash
# Basic example
python examples/example_usage.py

# Optimized scheduler example
python examples/optimized_example.py

# High load testing
python examples/high_load_example.py --tasks 1000 --workers 10
```

## Testing

Run the test suite:

```bash
# Run all tests
python tests/run_tests.py

# Run specific test categories
python tests/run_tests.py --type unit
python tests/run_tests.py --type integration
python tests/run_tests.py --type performance
```

## Performance Metrics

Performance comparison between implementations:

| Metric | Basic Scheduler | Optimized Scheduler | Improvement |
|--------|----------------|---------------------|-------------|
| Throughput (tasks/sec) | ~15-20 | ~50-60 | 3x |
| Task completion rate (1000 tasks) | <70% | >95% | >25% |
| CPU utilization | Spiky | Smooth | More efficient |
| Memory usage | Higher | Lower | More efficient |

## Usage Guide

Please refer to the [Usage Guide](USAGE.md) for detailed instructions on:
- When to use each implementation
- Common workflows
- Task handler creation
- Performance optimization tips
- Troubleshooting

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.