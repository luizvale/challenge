# Distributed Task Scheduler - Usage Guide

This project provides a Python-based distributed task scheduling system with different implementations for various use cases. This guide will help you understand which example to use for your specific needs.

## Overview of Available Examples

### 1. Basic Task Scheduler (`example_usage.py`)

This is the standard implementation that demonstrates the core features:
- Task creation and execution
- Task dependencies
- Task failure handling and retries
- Worker management
- Simple monitoring

**When to use**: For basic task scheduling needs and to understand the system's core concepts.

```bash
python examples/example_usage.py
```

### 2. Optimized Task Scheduler (`optimized_example.py`)

An enhanced version with performance improvements:
- Batch processing of tasks
- Adaptive worker scaling
- More efficient task distribution
- Enhanced monitoring capabilities

**When to use**: For production workloads where throughput and efficiency are important.

```bash
python examples/optimized_example.py
```

### 3. High Load Testing (`high_load_example.py`)

A specialized version for stress testing and performance evaluation:
- Can handle thousands of concurrent tasks
- Detailed performance metrics
- Configurable via command line arguments
- Distributes load across multiple threads

**When to use**: For testing system capacity, identifying bottlenecks, and validating performance under stress.

```bash
# Basic usage
python examples/high_load_example.py

# Advanced usage with custom parameters
python examples/high_load_example.py --tasks 2000 --workers 15 --batch-size 30 --timeout 300
```

## Comparing the Implementations

| Feature | Basic | Optimized | High Load |
|---------|-------|-----------|-----------|
| Task Processing | One at a time | Batch processing | Batch with tuning |
| Worker Scaling | Manual | Adaptive | Highly adaptive |
| Monitoring | Basic | Enhanced | Comprehensive |
| Throughput | ~20 tasks/s | ~60 tasks/s | 100+ tasks/s |
| Memory Usage | Moderate | Efficient | Optimized |
| Use Case | Learning | Production | Testing |

## Common Workflows

### 1. Basic Task Execution

For simple task execution without dependencies:

```python
task = Task(
    name="task_type",
    payload={"param1": "value1"},
    priority=TaskPriority.NORMAL
)
task_id = scheduler.schedule_task(task)
```

### 2. Creating Task Dependencies

To make one task depend on another:

```python
# Create first task
task1_id = scheduler.schedule_task(task1)

# Create dependent task
task2 = Task(
    name="dependent_task",
    payload={"input": "value"},
    dependency_ids={task1_id}  # Depends on task1
)
task2_id = scheduler.schedule_task(task2)
```

### 3. Complex Task Chains

For more complex workflows with multiple dependencies:

```python
# Task with multiple dependencies
complex_task = Task(
    name="complex_task",
    payload={"param": "value"},
    dependency_ids={task1_id, task2_id, task3_id}  # Depends on multiple tasks
)
complex_task_id = scheduler.schedule_task(complex_task)
```

### 4. Monitoring Task Progress

To check task status and results:

```python
# Get status of a specific task
status = scheduler.get_task_status(task_id)
print(f"Task status: {status['status']}")

# If completed, access the result
if status["status"] == TaskStatus.COMPLETED.value:
    print(f"Task result: {status['result']}")
```

### 5. Managing Workers

To control worker scaling:

```python
# Manual scaling
scheduler.scale_workers(10)  # Scale to 10 workers

# With the optimized scheduler, you can also enable adaptive scaling
optimized_scheduler = OptimizedTaskScheduler(
    # ... other parameters ...
    adaptive_workers=True,
    min_workers=5,
    max_workers=20
)
```

## Task Handlers

Task handlers define what happens when a task is executed. Here's how to create and register them:

```python
def my_task_handler(task: Task) -> Any:
    # Process the task payload
    input_value = task.payload.get("input")
    
    # Do some work
    result = process_data(input_value)
    
    # Return the result (can be any serializable value)
    return result

# Register the handler with the task executor
task_executor.register_handler("my_task_type", my_task_handler)
```

## Performance Tips

1. **Use batch processing** (Optimized Scheduler) for high-throughput scenarios
2. **Set appropriate priorities** for tasks based on their importance
3. **Be careful with dependencies** - complex dependency chains can limit parallelism
4. **Monitor system metrics** to identify bottlenecks
5. **Adjust worker count** based on the nature of your tasks:
   - CPU-bound tasks: Use fewer workers (around number of CPU cores)
   - I/O-bound tasks: Use more workers to maximize throughput

## Common Issues and Solutions

### Issue: Tasks taking too long to complete
**Solution**: Review task handlers for inefficiencies, increase timeout values, or break large tasks into smaller subtasks.

### Issue: Worker count constantly increasing
**Solution**: Adjust the busy_threshold and idle_threshold parameters to prevent excessive scaling.

### Issue: Memory usage growing over time
**Solution**: Ensure tasks are being properly completed and removed from the task repository.

### Issue: Some tasks never complete
**Solution**: Check for circular dependencies or deadlocks in your task relationships.

## Advanced Configuration

For production use with the optimized scheduler, consider these settings:

```python
scheduler = OptimizedTaskScheduler(
    # Required components
    task_repository=task_repository,
    worker_registry=worker_registry,
    task_queue=task_queue,
    task_executor=task_executor,
    task_monitor=monitor,
    
    # Performance tuning
    batch_size=20,               # Number of tasks to process in a batch
    heartbeat_timeout_seconds=30, # How long before worker is considered dead
    worker_check_interval=10,    # How often to check worker health
    
    # Adaptive scaling
    adaptive_workers=True,       # Enable dynamic scaling
    min_workers=5,               # Minimum worker count
    max_workers=30,              # Maximum worker count
    scaling_check_interval=15,   # How often to check if scaling is needed
    
    # Logging
    logger=custom_logger         # Optional custom logger
)
```

## Conclusion

The Distributed Task Scheduler provides a flexible framework for executing tasks across multiple workers with different performance characteristics. By choosing the right implementation for your needs and properly configuring it, you can build robust and efficient task processing systems.

Remember to start with the basic example to understand core concepts, then move to the optimized version for production use, and use the high load version for testing and performance validation.