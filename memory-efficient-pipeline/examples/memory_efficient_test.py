"""
Memory efficiency test for the data pipeline.

This example demonstrates how the memory usage remains constant
regardless of the input data volume, which is a key requirement
of the memory-efficient data pipeline challenge.
"""
import time
import psutil
import os
import gc
import logging
import matplotlib.pyplot as plt
from typing import List, Dict, Any

from src.use_cases import DataPipeline
from src.use_cases.transformers import MapTransformer


def test_memory_efficiency_with_sizes(logger):
    """
    Tests memory efficiency of the pipeline with different data volumes.

    This function processes increasingly large volumes of data through
    the pipeline and monitors memory usage throughout the process to
    verify that memory usage remains relatively constant regardless
    of input volume.
    """
    # Get current process for memory monitoring
    process = psutil.Process(os.getpid())

    # Function to generate test data of specified size
    def generate_data(size: int):
        """Generates a stream of test data items."""
        for i in range(size):
            yield {
                "id": i,
                "name": f"User {i}",
                "email": f"user{i}@example.com",
                "data": "x" * 100  # Fixed-size data for consistency
            }

    # Data sizes to test (increasing by factor of 10)
    sizes = [100, 1000, 10000, 100000]

    # Simple transformation function
    def simple_transform(data: Dict[str, Any]) -> Dict[str, Any]:
        """Applies a simple transformation to the data."""
        result = dict(data)
        result['processed'] = True
        return result

    # Store results for plotting
    all_results = []

    logger.info("Starting memory efficiency test...")
    logger.info("=" * 50)

    for size in sizes:
        logger.info(f"\nTesting with {size} items...")

        # Configure pipeline
        pipeline = DataPipeline(buffer_size=100)
        pipeline.add_transformer(MapTransformer(simple_transform))

        # Measure initial memory
        memory_start = process.memory_info().rss / (1024 * 1024)

        # Process data, collecting measurements during processing
        mem_measurements = []
        start_time = time.time()

        count = 0
        for _ in pipeline.process_data(generate_data(size)):
            count += 1

            # Collect a sample every n items (adjust for larger volumes)
            sample_interval = max(1, size // 20)
            if count % sample_interval == 0:
                current_mem = process.memory_info().rss / (1024 * 1024)
                mem_measurements.append((count, current_mem))

        # Measure final memory and elapsed time
        memory_end = process.memory_info().rss / (1024 * 1024)
        elapsed = time.time() - start_time

        # Calculate statistics
        if mem_measurements:
            max_mem = max(m[1] for m in mem_measurements)
            min_mem = min(m[1] for m in mem_measurements)
            avg_mem = sum(m[1] for m in mem_measurements) / len(mem_measurements)
            mem_range = max_mem - min_mem
        else:
            max_mem = min_mem = avg_mem = mem_range = 0

        # Log results
        logger.info(f"  Time: {elapsed:.2f} seconds")
        logger.info(f"  Items/second: {size / elapsed:.0f}")
        logger.info(f"  Initial Memory: {memory_start:.2f} MB")
        logger.info(f"  Final Memory: {memory_end:.2f} MB")
        logger.info(f"  Difference: {memory_end - memory_start:.2f} MB")
        logger.info(f"  Memory Range: {mem_range:.2f} MB (Min: {min_mem:.2f}, Max: {max_mem:.2f}, Avg: {avg_mem:.2f})")

        # Determine efficiency based on memory range
        if mem_range < 5:
            efficiency = "GOOD"
        elif mem_range < 10:
            efficiency = "FAIR"
        else:
            efficiency = "POOR"

        logger.info(f"  Efficiency: {efficiency} - Memory range should remain small")

        # Save results for plotting
        all_results.append({
            'size': size,
            'time': elapsed,
            'memory_start': memory_start,
            'memory_end': memory_end,
            'memory_min': min_mem,
            'memory_max': max_mem,
            'memory_avg': avg_mem,
            'memory_range': mem_range,
            'measurements': mem_measurements
        })

        # Force garbage collection between runs
        gc.collect()
        time.sleep(1)  # Give system time to stabilize

    logger.info("\n" + "=" * 50)
    logger.info("Memory efficiency test completed!")

    # Generate summary and conclusions
    logger.info("\nSUMMARY:")
    logger.info("-" * 50)
    logger.info(f"{'Size':<10} {'Time (s)':<10} {'Mem Min':<10} {'Mem Max':<10} {'Mem Range':<10}")
    logger.info("-" * 50)

    for result in all_results:
        logger.info(f"{result['size']:<10} {result['time']:<10.2f} {result['memory_min']:<10.2f} "
              f"{result['memory_max']:<10.2f} {result['memory_range']:<10.2f}")

    # Analyze the results
    is_memory_efficient = all(r['memory_range'] < 10 for r in all_results)

    logger.info("\nCONCLUSION:")
    if is_memory_efficient:
        logger.info("✅ The pipeline demonstrates good memory efficiency!")
        logger.info("   Memory usage remains relatively constant regardless of input volume.")
    else:
        logger.info("❌ The pipeline may not have optimal memory efficiency.")
        logger.info("   Memory usage fluctuates significantly during processing.")

    # Return the results for potential further analysis
    return all_results


def plot_memory_usage(results: List[Dict[str, Any]], logger) -> None:
    """
    Creates and displays plots of memory usage during processing.

    Args:
        results: List of test results from the memory efficiency test
        logger: Logger instance for logging messages
    """
    try:
        # Only attempt to plot if matplotlib is available
        plt.figure(figsize=(12, 8))

        # Create subplots for each test size
        for i, result in enumerate(results):
            size = result['size']
            measurements = result['measurements']

            if not measurements:
                continue

            # Extract x and y values
            x_vals = [m[0] for m in measurements]
            y_vals = [m[1] for m in measurements]

            # Create subplot
            plt.subplot(2, 2, i + 1)
            plt.plot(x_vals, y_vals, '-o')
            plt.title(f"Memory Usage - {size} Items")
            plt.xlabel("Items Processed")
            plt.ylabel("Memory Usage (MB)")
            plt.grid(True)

            # Add horizontal line for average
            plt.axhline(y=result['memory_avg'], color='r', linestyle='--',
                        label=f"Avg: {result['memory_avg']:.2f} MB")
            plt.legend()

        plt.tight_layout()

        # Save the plot
        plt.savefig("memory_usage_plot.png")
        logger.info("\nPlot saved as 'memory_usage_plot.png'")

        # Display the plot if running in interactive environment
        plt.show()

    except ImportError:
        logger.warning("\nMatplotlib not available. Install it to generate plots.")
    except Exception as e:
        logger.error(f"\nError generating plot: {e}")


def main():
    """Main function to run the memory efficiency test."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("memory_efficiency_test")
    
    results = test_memory_efficiency_with_sizes(logger)

    try:
        plot_memory_usage(results, logger)
    except Exception as e:
        logger.error(f"Error in plotting: {e}")

    logger.info("\nTest completed!")


if __name__ == "__main__":
    main()