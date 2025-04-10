# Resource Manager

A robust and efficient context manager for handling multiple external resources with proper cleanup, detailed logging, and performance metrics.

## Features

- **Resource Lifecycle Management**: Safely acquire and release multiple resources
- **Proper Exception Handling**: Ensures resources are released even when exceptions occur
- **Detailed Logging**: Comprehensive logging of resource operations
- **Performance Metrics**: Tracks acquisition, usage, and release times
- **Nested Contexts**: Supports nested resource managers
- **Clean Architecture**: Follows Clean Architecture principles for maintainability

## Installation

```bash
cd custom-context-manager
python custom-context-manager\examples\basic_usage.py
python custom-context-manager\examples\nested_usage.py
```

## Basic Usage

```python
from resource_manager import ResourceManager
from resource_manager.resources import DatabaseResource, ApiResource, FileResource

# Create a resource manager
manager = ResourceManager()

# Add resources to be managed
manager.add_resource("db", DatabaseResource("sqlite:///example.db"))
manager.add_resource("api", ApiResource("https://api.example.com", api_key="your_key"))
manager.add_resource("log", FileResource("app.log", mode="w"))

# Use resources with the context manager
with manager as resources:
    # All resources are now acquired and ready to use
    
    # Use the database
    results = resources.db.execute("SELECT * FROM users")
    
    # Use the API
    response = resources.api.get("/data")
    
    # Use the log file
    resources.log.write(f"Retrieved {len(results)} users\n")
    
# All resources are automatically released when exiting the context
```

## Working with Individual Resources

For cases where you only need a single resource:

```python
# Using a single resource
with manager.use_resource("db") as db:
    results = db.execute("SELECT * FROM users")
```

## Nested Resource Managers

For more complex scenarios with different resource lifetimes:

```python
# Outer manager for long-lived resources
with ResourceManager() as outer:
    # Add and use long-lived resources
    
    # For a specific operation that needs additional resources
    with ResourceManager() as inner:
        # Use resources from both managers
        outer.db.execute("BEGIN TRANSACTION")
        inner.api.post("/data", {"status": "processing"})
        
        # ... do work ...
        
        outer.db.execute("COMMIT")
    
    # Inner resources are released, outer resources still available
```

## Resource Types

### Built-in Resources

- **DatabaseResource**: Manages database connections
- **ApiResource**: Manages API clients and connections
- **FileResource**: Manages file handles

### Creating Custom Resources

You can easily create custom resources by implementing the `Resource` interface:

```python
from resource_manager import Resource

class MyCustomResource(Resource):
    def __init__(self, config):
        self._config = config
        self._connection = None
    
    def acquire(self):
        # Initialize the resource
        self._connection = initialize_resource(self._config)
    
    def release(self):
        # Clean up the resource
        if self._connection:
            self._connection.close()
            self._connection = None
    
    @property
    def is_acquired(self):
        return self._connection is not None
```

## Metrics and Monitoring

The resource manager includes built-in metrics collection:

```python
from resource_manager import ResourceManager
from resource_manager.metrics import BasicMetricsCollector

# Create a metrics collector
metrics = BasicMetricsCollector()

# Use it with the manager
manager = ResourceManager(metrics_collector=metrics)

# ... use resources ...

# Get metrics report
report = metrics.get_metrics()
print(f"Total acquisition time: {report['total_acquisition_time']}s")
```

## Logging

Enhanced logging is available:

```python
from resource_manager import ResourceManager
from resource_manager.monitoring import get_logger

# Create a custom logger
logger = get_logger(level=logging.DEBUG, use_colors=True)

# Use it with the manager
manager = ResourceManager(logger=logger)
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.