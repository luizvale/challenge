# Lazy Evaluation Project

## Project Overview

This project provides a robust implementation of a **Lazy Evaluation** system in Python, designed to handle large data sets and intensive computational tasks efficiently by minimizing memory usage and improving runtime performance. It demonstrates advanced concepts including filtering, mapping, reduction, pagination, chunking, caching, and memoization through practical examples.

## Project Structure

```
lazy_collection/
├── interfaces/
│   └── lazy_collection_contract.py
│
├── entities/
│   └── lazy_collection.py
│
├── usecases/
│   └── big_data_pipeline.py
│
├── examples/
│   ├── infinite_data_stream.py
│   ├── large_csv_processing.py
│   ├── demonstrate_lazy_sorting.py
│   └── caching_and_memoization.py
│
└── tests/
    └── test_lazy_collection.py
```

---

## Installation

```bash
cd memory-effient-pipeline
pip install matplotlib
pip install memory_profiler
```

## Key Components

### `interfaces/lazy_collection_contract.py`
Defines an abstract base class outlining the core functionalities required for lazy evaluation operations such as filtering, mapping, reduction, chunking, pagination, and basic retrieval.

### `entities/lazy_collection.py`
Provides the concrete implementation of the lazy evaluation methods defined in the interface. It ensures efficient handling of iterables through generators, significantly reducing memory usage.

---

## Use Cases and Examples

### Memory Usage Graph (`examples/memory_usage_graph.py`)
Visualizes memory consumption when processing large CSV files, showcasing the impact of lazy evaluation on memory efficiency.

### Time Caching Graph (`examples/time_caching_graph.py`)
Compares execution time with and without caching, demonstrating how memoization improves performance for repeated computations.

### Sorting Performance Graph (`examples/sorting_performance_graph.py`)
Compares the performance of different sorting algorithms or strategies when handling large datasets.


```python
import csv
from entities.lazy_collection import LazyCollection

def read_large_csv(file_path):
    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            yield row

if __name__ == '__main__':
    data = LazyCollection(read_large_csv('large_file.csv'))
    result = data.filter(lambda row: int(row[2]) > 5000).take(10).to_list()
    print(result)
```

```python
import functools
import time
from entities.lazy_collection import LazyCollection

@functools.lru_cache(maxsize=1000)
def expensive_computation(x):
    time.sleep(0.01)
    return x * x

if __name__ == '__main__':
    data = LazyCollection(range(10000)).map(expensive_computation)
    first_pass = data.take(5).to_list()
    second_pass = data.take(5).to_list()  # cached results

    print('First pass:', first_pass)
    print('Second pass (cached):', second_pass)
```

---

## Testing
The provided tests ensure that each lazy evaluation method performs correctly and efficiently. Example tests include validation of map, filter, chunking, and pagination operations.

---

## Discussions and Advanced Concepts

- **Lazy vs. Eager Evaluation:**
  - Discussions on memory usage and runtime performance differences between lazy and eager evaluations.
  - Graphical performance comparisons to illustrate efficiency clearly.

- **Complexity Analysis:**
  - Examination of time and space complexity trade-offs when using lazy evaluation.
  - Practical demonstrations to highlight real-world implications.

- **Caching Strategies:**
  - Exploring effective caching and memoization to optimize lazy operations.
  - Demonstrating significant performance gains through caching.

- **Sorting Strategies:**
  - In-depth discussion of lazy sorting strategies, their benefits, and potential pitfalls.
  - Demonstration of practical implications in performance-critical scenarios.

---

## Conclusion

This project effectively showcases the power and flexibility of Lazy Evaluation in Python. It combines clear architectural design with practical, real-world examples, fostering deep technical discussions around efficiency, performance, and advanced programming concepts.

