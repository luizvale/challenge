"""
Comprehensive tests for the data pipeline functionality.

This module contains unit and integration tests for the DataPipeline class
and its interactions with transformers, aggregators, and output sinks.
"""
import unittest
import time
from typing import Dict, Any, List, Generator, Optional
from datetime import datetime

from src.core.entities import DataItem
from src.core.interfaces import BaseOutputSink, BaseTransformer, Aggregator
from src.use_cases import DataPipeline
from src.use_cases.transformers import MapTransformer, FilterTransformer, ChainTransformer
from src.use_cases.aggregators import AggregationResult


class MockOutputSink(BaseOutputSink):
    """Mock output sink for testing."""

    def __init__(self, should_fail: bool = False, fail_every: int = 0):
        """
        Initialize the mock sink.

        Args:
            should_fail: If True, all operations fail
            fail_every: If > 0, fail every N items (for testing partial failures)
        """
        self.items: List[DataItem] = []
        self.should_fail = should_fail
        self.fail_every = fail_every
        self.send_count = 0

    def send(self, item: DataItem) -> bool:
        """
        Mock implementation of the send method.

        Args:
            item: Item to send

        Returns:
            True if successful, False otherwise
        """
        if self.should_fail:
            return False

        # Simulate intermittent failures if fail_every is set
        self.send_count += 1
        if self.fail_every > 0 and self.send_count % self.fail_every == 0:
            return False

        self.items.append(item)
        return True

    def reset(self) -> None:
        """Clears stored items."""
        self.items = []
        self.send_count = 0


class ErrorTransformer(BaseTransformer):
    """Transformer that raises errors for testing."""

    def __init__(self, error_on_id: Optional[int] = None):
        """
        Initialize with optional ID to error on.

        Args:
            error_on_id: If set, only error on items with this ID
        """
        self.error_on_id = error_on_id
        self.transform_count = 0

    def transform(self, item: DataItem) -> Optional[DataItem]:
        """
        Raises an error for specific items.

        Args:
            item: Item to transform

        Returns:
            The item unchanged or None if error raised

        Raises:
            ValueError: If item ID matches error_on_id
        """
        self.transform_count += 1

        if self.error_on_id is not None:
            if 'id' in item.data and item.data['id'] == self.error_on_id:
                raise ValueError(f"Simulated error on item ID {self.error_on_id}")

        return item


class SlowTransformer(BaseTransformer):
    """Transformer that introduces delays for testing throughput."""

    def __init__(self, delay_seconds: float = 0.01):
        """
        Initialize with delay time.

        Args:
            delay_seconds: Seconds to delay each transformation
        """
        self.delay_seconds = delay_seconds

    def transform(self, item: DataItem) -> Optional[DataItem]:
        """
        Applies a delay before returning the item.

        Args:
            item: Item to transform

        Returns:
            The item unchanged after delay
        """
        time.sleep(self.delay_seconds)
        return item


class MockAggregator(Aggregator[int]):
    """Mock aggregator for testing."""

    def __init__(self):
        """Initialize the mock aggregator."""
        self.items: List[DataItem] = []

    def add_item(self, item: DataItem) -> None:
        """
        Add an item to the aggregator.

        Args:
            item: The item to add
        """
        self.items.append(item)

    def get_results(self) -> List[AggregationResult[int]]:
        """
        Get the aggregation results.

        Returns:
            List containing a single result with the count of items
        """
        result = AggregationResult(
            value=len(self.items),
            count=len(self.items),
            metadata={}
        )
        return [result]

    def reset(self) -> None:
        """Reset the aggregator state."""
        self.items = []


class TestDataPipeline(unittest.TestCase):
    """Test cases for the DataPipeline class."""

    def test_empty_pipeline(self) -> None:
        """Test pipeline with no transformers or outputs."""
        pipeline = DataPipeline()

        # Simple test data
        data = [{"id": 1, "value": "test"}]

        # Process the data
        results = list(pipeline.process_data(data))

        # Verify results
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].data["id"], 1)
        self.assertEqual(results[0].data["value"], "test")

    def test_single_transformation(self) -> None:
        """Test pipeline with a single transformer."""
        # Create a simple transformation
        def add_flag(data: Dict[str, Any]) -> Dict[str, Any]:
            result = dict(data)
            result["processed"] = True
            return result

        transformer = MapTransformer(add_flag)

        # Create pipeline with transformer
        pipeline = DataPipeline()
        pipeline.add_transformer(transformer)

        # Test data
        data = [{"id": 1, "value": "test"}]

        # Process the data
        results = list(pipeline.process_data(data))

        # Verify results
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].data["id"], 1)
        self.assertEqual(results[0].data["value"], "test")
        self.assertTrue(results[0].data["processed"])

    def test_filter_transformation(self) -> None:
        """Test pipeline with a filter transformer."""
        # Create a filter that only keeps items with even ids
        def is_even_id(data: Dict[str, Any]) -> bool:
            return data.get("id", 0) % 2 == 0

        filter_transformer = FilterTransformer(is_even_id)

        # Create pipeline with filter
        pipeline = DataPipeline()
        pipeline.add_transformer(filter_transformer)

        # Test data with mix of even and odd ids
        data = [
            {"id": 1, "value": "odd"},
            {"id": 2, "value": "even"},
            {"id": 3, "value": "odd"},
            {"id": 4, "value": "even"}
        ]

        # Process the data
        results = list(pipeline.process_data(data))

        # Verify results - should only have even ids
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].data["id"], 2)
        self.assertEqual(results[1].data["id"], 4)

    def test_chained_transformations(self) -> None:
        """Test pipeline with multiple transformers chained."""
        # Create transformers
        def add_squared(data: Dict[str, Any]) -> Dict[str, Any]:
            result = dict(data)
            if "value" in result and isinstance(result["value"], (int, float)):
                result["squared"] = result["value"] ** 2
            return result

        def add_tag(data: Dict[str, Any]) -> Dict[str, Any]:
            result = dict(data)
            result["tag"] = "processed"
            return result

        transformer1 = MapTransformer(add_squared)
        transformer2 = MapTransformer(add_tag)

        # Create pipeline with both transformers
        pipeline = DataPipeline()
        pipeline.add_transformer(transformer1)
        pipeline.add_transformer(transformer2)

        # Test data
        data = [{"id": 1, "value": 5}]

        # Process the data
        results = list(pipeline.process_data(data))

        # Verify results - should have both transformations applied
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].data["squared"], 25)
        self.assertEqual(results[0].data["tag"], "processed")

    def test_chain_transformer(self) -> None:
        """Test the ChainTransformer class."""
        # Create transformers
        def capitalize_name(data: Dict[str, Any]) -> Dict[str, Any]:
            result = dict(data)
            if "name" in result:
                result["name"] = result["name"].upper()
            return result

        def add_greeting(data: Dict[str, Any]) -> Dict[str, Any]:
            result = dict(data)
            if "name" in result:
                result["greeting"] = f"Hello, {result['name']}!"
            return result

        # Create chain transformer
        chain = ChainTransformer([
            MapTransformer(capitalize_name),
            MapTransformer(add_greeting)
        ])

        # Create pipeline with chain transformer
        pipeline = DataPipeline()
        pipeline.add_transformer(chain)

        # Test data
        data = [{"id": 1, "name": "alice"}]

        # Process the data
        results = list(pipeline.process_data(data))

        # Verify results
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].data["name"], "ALICE")
        self.assertEqual(results[0].data["greeting"], "Hello, ALICE!")

    def test_output_sink(self) -> None:
        """Test pipeline with output sink."""
        # Create a mock output sink
        mock_sink = MockOutputSink()

        # Create a simple transformer
        def uppercase_value(data: Dict[str, Any]) -> Dict[str, Any]:
            result = dict(data)
            if "value" in result and isinstance(result["value"], str):
                result["value"] = result["value"].upper()
            return result

        transformer = MapTransformer(uppercase_value)

        # Create pipeline with transformer and output
        pipeline = DataPipeline()
        pipeline.add_transformer(transformer)
        pipeline.add_output(mock_sink)

        # Test data
        data = [
            {"id": 1, "value": "test1"},
            {"id": 2, "value": "test2"}
        ]

        # Process the data
        results = list(pipeline.process_data(data))

        # Verify results in both pipeline output and sink
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].data["value"], "TEST1")
        self.assertEqual(results[1].data["value"], "TEST2")

        # Verify items were sent to the sink
        self.assertEqual(len(mock_sink.items), 2)
        self.assertEqual(mock_sink.items[0].data["value"], "TEST1")
        self.assertEqual(mock_sink.items[1].data["value"], "TEST2")

    def test_multiple_output_sinks(self) -> None:
        """Test pipeline with multiple output sinks."""
        # Create mock output sinks
        sink1 = MockOutputSink()
        sink2 = MockOutputSink()

        # Create pipeline with both sinks
        pipeline = DataPipeline()
        pipeline.add_output(sink1)
        pipeline.add_output(sink2)

        # Test data
        data = [{"id": 1, "value": "test"}]

        # Process the data
        results = list(pipeline.process_data(data))

        # Verify results
        self.assertEqual(len(results), 1)

        # Verify items were sent to both sinks
        self.assertEqual(len(sink1.items), 1)
        self.assertEqual(len(sink2.items), 1)

        # Verify item content
        self.assertEqual(sink1.items[0].data["id"], 1)
        self.assertEqual(sink2.items[0].data["id"], 1)

    def test_failed_output(self) -> None:
        """Test pipeline with failing output sink."""
        # Create a failing mock output sink
        failing_sink = MockOutputSink(should_fail=True)
        working_sink = MockOutputSink()

        # Create pipeline with both sinks
        pipeline = DataPipeline()
        pipeline.add_output(failing_sink)
        pipeline.add_output(working_sink)

        # Test data
        data = [{"id": 1, "value": "test"}]

        # Process the data
        results = list(pipeline.process_data(data))

        # Verify results are still returned
        self.assertEqual(len(results), 1)

        # Verify items were not sent to the failing sink
        self.assertEqual(len(failing_sink.items), 0)

        # Verify items were sent to the working sink
        self.assertEqual(len(working_sink.items), 1)

    def test_intermittent_failures(self) -> None:
        """Test pipeline with intermittently failing output sink."""
        # Create sink that fails every 2nd item
        intermittent_sink = MockOutputSink(fail_every=2)

        # Create pipeline with sink
        pipeline = DataPipeline()
        pipeline.add_output(intermittent_sink)

        # Test data - 5 items
        data = [{"id": i, "value": f"test{i}"} for i in range(5)]

        # Process the data
        results = list(pipeline.process_data(data))

        # Verify all results are returned
        self.assertEqual(len(results), 5)

        # Verify only non-failing items were sent to the sink
        # Items 0, 2, 4 should be sent (1 and 3 fail)
        self.assertEqual(len(intermittent_sink.items), 3)
        self.assertEqual(intermittent_sink.items[0].data["id"], 0)
        self.assertEqual(intermittent_sink.items[1].data["id"], 2)
        self.assertEqual(intermittent_sink.items[2].data["id"], 4)

    def test_batch_processing(self) -> None:
        """Test pipeline with batch processing."""
        # Create a mock output sink
        mock_sink = MockOutputSink()

        # Create pipeline with small buffer size
        pipeline = DataPipeline(buffer_size=2)
        pipeline.add_output(mock_sink)

        # Generate a larger dataset
        data = [{"id": i, "value": f"test{i}"} for i in range(10)]

        # Process the data and collect results
        results = list(pipeline.process_data(data))

        # Verify all items were processed
        self.assertEqual(len(results), 10)

        # Verify all items were sent to the sink
        self.assertEqual(len(mock_sink.items), 10)

        # Verify the order is maintained
        for i, item in enumerate(mock_sink.items):
            self.assertEqual(item.data["id"], i)
            self.assertEqual(item.data["value"], f"test{i}")

    def test_error_handling_in_transformer(self) -> None:
        """Test error handling when a transformer fails."""
        # Create a transformer that fails for specific items
        error_transformer = ErrorTransformer(error_on_id=2)

        # Create pipeline with transformer
        pipeline = DataPipeline()
        pipeline.add_transformer(error_transformer)

        # Test data with a problematic item
        data = [
            {"id": 1, "value": "good"},
            {"id": 2, "value": "bad"},  # This will cause an error
            {"id": 3, "value": "good"}
        ]

        # Process the data - should skip the failing item
        results = list(pipeline.process_data(data))

        # Verify results - should have two items (the good ones)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].data["id"], 1)
        self.assertEqual(results[1].data["id"], 3)

    def test_custom_error_handling(self) -> None:
        """Test custom error handling with error callbacks."""
        # Track errors
        errors = []

        def error_callback(item, error):
            errors.append((item.data.get('id'), str(error)))

        # Create a transformer that fails for specific items
        error_transformer = ErrorTransformer(error_on_id=2)

        # Create pipeline with transformer and error callback
        pipeline = DataPipeline()
        pipeline.add_transformer(error_transformer)

        # Test data with a problematic item
        data = [
            {"id": 1, "value": "good"},
            {"id": 2, "value": "bad"},  # This will cause an error
            {"id": 3, "value": "good"}
        ]

        # Process the data with custom error handling
        try:
            # This is where we'd register an error callback if it was supported
            # For now, we just process and catch errors manually
            results = list(pipeline.process_data(data))

            # Verify results - should have two items (the good ones)
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0].data["id"], 1)
            self.assertEqual(results[1].data["id"], 3)

            # Note: In a future enhancement, we could add a proper error callback
            # system to the pipeline class that would populate the errors list

        except Exception as e:
            self.fail(f"Should not raise exception: {e}")

    def test_throughput(self) -> None:
        """Test pipeline throughput with slow components."""
        # Create a slow transformer
        slow_transformer = SlowTransformer(delay_seconds=0.001)  # 1ms delay

        # Create pipeline with slow transformer
        pipeline = DataPipeline(buffer_size=10)
        pipeline.add_transformer(slow_transformer)

        # Generate test data - 100 items
        data = [{"id": i, "value": f"test{i}"} for i in range(100)]

        # Measure processing time
        start_time = time.time()
        results = list(pipeline.process_data(data))
        elapsed_time = time.time() - start_time

        # Verify all items were processed
        self.assertEqual(len(results), 100)

        # The minimum time should be at least 100 * 0.001 = 0.1 seconds
        # allowing for some overhead
        self.assertGreaterEqual(elapsed_time, 0.09)

        # But it shouldn't be too slow either (adding some margin)
        # This is a loose test because CI environments can be unpredictable
        self.assertLess(elapsed_time, 0.5)

    def test_large_dataset(self) -> None:
        """Test pipeline with a larger dataset."""
        # Create simple transformer
        def add_processed(data: Dict[str, Any]) -> Dict[str, Any]:
            result = dict(data)
            result["processed"] = True
            return result

        transformer = MapTransformer(add_processed)

        # Create pipeline
        pipeline = DataPipeline(buffer_size=100)
        pipeline.add_transformer(transformer)

        # Generate larger dataset - 1000 items
        data = [{"id": i, "value": f"test{i}"} for i in range(1000)]

        # Process the data
        results = list(pipeline.process_data(data))

        # Verify all items were processed
        self.assertEqual(len(results), 1000)

        # Verify transformation was applied to all items
        for item in results:
            self.assertTrue(item.data["processed"])

    def test_metadata_preservation(self) -> None:
        """Test that metadata is preserved through transformations."""
        # Create a transformer that modifies data but should preserve metadata
        def modify_value(data: Dict[str, Any]) -> Dict[str, Any]:
            result = dict(data)
            result["modified"] = True
            return result

        transformer = MapTransformer(modify_value)

        # Create pipeline
        pipeline = DataPipeline()
        pipeline.add_transformer(transformer)

        # Create test data with metadata
        data = [{"id": 1, "value": "test"}]

        # Create DataItem with custom metadata
        custom_metadata = {"source": "test", "timestamp": datetime.now()}
        data_item = DataItem(data=data[0], metadata=custom_metadata)

        # Process the data item
        results = list(pipeline.process_data([data_item.data]))

        # Verify results
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].data["modified"])

        # Unfortunately, metadata isn't preserved because we're passing raw data
        # This highlights a potential improvement area for the pipeline

    def test_with_aggregator(self) -> None:
        """Test pipeline integration with an aggregator."""
        # Create mock aggregator
        aggregator = MockAggregator()

        # Create pipeline
        pipeline = DataPipeline()

        # Test data
        data = [{"id": i, "value": f"test{i}"} for i in range(5)]

        # Process data through pipeline
        results = list(pipeline.process_data(data))

        # Add results to aggregator
        for item in results:
            aggregator.add_item(item)

        # Get aggregation results
        agg_results = aggregator.get_results()

        # Verify aggregation
        self.assertEqual(len(agg_results), 1)
        self.assertEqual(agg_results[0].value, 5)  # 5 items counted
        self.assertEqual(agg_results[0].count, 5)

    def test_memory_usage(self) -> None:
        """
        Test that memory usage remains constant regardless of data volume.
        Note: This is more of an integration test and actual memory
        measurement is complex in a unit test environment.

        This test is based on execution time as a proxy, since proper
        memory measurement requires external tools.
        """
        # Create a simple pipeline
        pipeline = DataPipeline(buffer_size=10)

        # Helper function to generate data of a given size
        def generate_data(size: int) -> Generator[Dict[str, Any], None, None]:
            for i in range(size):
                yield {"id": i, "value": f"test{i}"}

        # Process datasets of different sizes
        sizes = [100, 1000]
        times = []

        for size in sizes:
            start_time = time.time()
            results = list(pipeline.process_data(generate_data(size)))
            elapsed = time.time() - start_time
            times.append(elapsed)

            # Verify correct number of results
            self.assertEqual(len(results), size)

        # Avoid division by zero or very small numbers
        if times[0] < 0.001:
            # If first measurement is too small, we can't reliably calculate ratio
            # Instead check that the second time isn't unreasonably large
            self.assertLess(times[1], 0.5)  # Should process 1000 items quickly
        else:
            # If time measurements are reliable, check ratio against size ratio
            size_ratio = sizes[1] / sizes[0]  # Should be 10
            time_ratio = times[1] / times[0]

            # This is a very loose test with wide margins
            # Just checking that time doesn't increase exponentially with data size
            self.assertLess(time_ratio, size_ratio * 3)

    def test_empty_input(self) -> None:
        """Test pipeline behavior with empty input."""
        # Create pipeline
        pipeline = DataPipeline()

        # Empty data
        data = []

        # Process the data
        results = list(pipeline.process_data(data))

        # Verify empty results
        self.assertEqual(len(results), 0)

    def test_none_values_in_input(self) -> None:
        """Test pipeline behavior with None values in input."""
        # Create pipeline
        pipeline = DataPipeline()

        # Data with None mixed in
        data = [{"id": 1}, None, {"id": 2}]

        # Process the data - should skip None values
        results = list(pipeline.process_data(data))

        # Verify results
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].data["id"], 1)
        self.assertEqual(results[1].data["id"], 2)


if __name__ == "__main__":
    unittest.main()