# Memory-Efficient Data Pipeline

A robust data processing pipeline designed for memory efficiency, capable of handling variable-rate data streams with constant memory usage. This implementation follows Clean Architecture principles to ensure separation of concerns and maintainability.

## Features

- **Memory Efficiency**: Processes data streams of any size with constant memory usage
- **Flexible Transformations**: Apply custom transformations to data items
- **Powerful Aggregations**: Aggregate data using various window and grouping strategies
- **Multiple Outputs**: Send processed data to databases, message queues, and more
- **Monitoring**: Track memory usage and performance metrics

## Architecture

This project follows a simplified Clean Architecture with three main layers:

1. **Entities Layer** (`entities/`)
   - Core domain entities and business rules
   - Interfaces defining the contracts between layers

2. **Use Cases Layer** (`use_cases/`)
   - Application-specific business logic
   - Implementation of transformers and aggregators
   - Orchestration of the data flow

3. **External Layer** (`external/`)
   - Adapters for external systems (webhooks, databases, queues)
   - Infrastructure concerns like monitoring

## Installation

```bash
cd memory-effient-pipeline
pip install matplotlib
```

## Quick Start

Here's a simple example of using the pipeline if you installed as a library:

```python
from memory_efficient_pipeline.entities import DataItem
from memory_efficient_pipeline.use_cases import DataPipeline
from memory_efficient_pipeline.use_cases.transformers import MapTransformer, FilterTransformer
from memory_efficient_pipeline.external.output import DatabaseOutputSink

# Define transformations
def normalize_data(data):
    result = dict(data)
    if 'name' in result:
        result['name'] = result['name'].strip().title()
    return result

def is_valid(data):
    return 'email' in data and '@' in data['email']

# Create pipeline components
normalizer = MapTransformer(normalize_data)
validator = FilterTransformer(is_valid)
db_output = DatabaseOutputSink(
    connection_params={"host": "localhost", "port": 5432},
    table_name="processed_data"
)

# Set up the pipeline
pipeline = DataPipeline()
pipeline.add_transformer(normalizer)
pipeline.add_transformer(validator)
pipeline.add_output(db_output)

# Process data stream
data_stream = [
    {"name": "john doe", "email": "john@example.com"},
    {"name": "jane smith", "email": "jane@example.com"},
    {"name": "invalid user", "phone": "123456"}  # Will be filtered out
]

# Execute the pipeline
processed_items = list(pipeline.process_data(data_stream))
print(f"Processed {len(processed_items)} valid items")
```

## Advanced Usage

For more complex examples, see the `examples/` directory, particularly `examples/example_pipeline.py`.

### Custom Transformers

You can create custom transformers by implementing the `Transformer` interface:

```python
from memory_efficient_pipeline.entities import DataItem
from memory_efficient_pipeline.entities.interfaces import Transformer

class MyCustomTransformer(Transformer):
    def transform(self, item: DataItem):
        # Your transformation logic here
        new_data = dict(item.data)
        new_data['processed_by'] = 'MyCustomTransformer'
        return item.with_transformation(new_data)
```

### Custom Aggregators

Similarly, you can create custom aggregators:

```python
from memory_efficient_pipeline.entities import DataItem
from memory_efficient_pipeline.entities.interfaces import Aggregator
from memory_efficient_pipeline.use_cases.aggregators import AggregationResult

class MyCustomAggregator(Aggregator):
    def __init__(self):
        self.items = []
    
    def add_item(self, item: DataItem):
        self.items.append(item)
    
    def get_results(self):
        # Your aggregation logic here
        return [AggregationResult(
            value=len(self.items),
            count=len(self.items),
            metadata={}
        )]
    
    def reset(self):
        self.items = []
```

## Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src
```

## Contribution

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.