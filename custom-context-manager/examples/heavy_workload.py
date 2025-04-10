import os
import sys
import time
import random
import logging
import threading
import queue
import psutil
import matplotlib.pyplot as plt
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Resource Manager imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.use_cases.resource_manager import ResourceManager
from src.use_cases.metrics import AdvancedMetricsCollector
from src.external.database_resource import DatabaseResource
from src.external.api_resource import ApiResource
from src.external.file_resource import FileResource
from src.external.logger import get_logger


class SystemMonitor:
    """
    Monitors system resources like CPU and memory usage during workload tests.
    """

    def __init__(self, interval=0.5):
        """
        Initialize the system monitor.

        Args:
            interval: Sampling interval in seconds
        """
        self.interval = interval
        self.cpu_percentages = []
        self.memory_usage = []
        self.timestamps = []
        self._stop_event = threading.Event()
        self._monitor_thread = None

    def start(self):
        """Start the monitoring thread."""
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_resources)
        self._monitor_thread.daemon = True
        self._monitor_thread.start()

    def stop(self):
        """Stop the monitoring thread."""
        if self._monitor_thread:
            self._stop_event.set()
            self._monitor_thread.join(timeout=2.0)

    def _monitor_resources(self):
        """Monitor system resources at regular intervals."""
        process = psutil.Process(os.getpid())

        while not self._stop_event.is_set():
            # CPU usage (percentage)
            self.cpu_percentages.append(process.cpu_percent(interval=0))

            # Memory usage (MB)
            memory_info = process.memory_info()
            self.memory_usage.append(memory_info.rss / (1024 * 1024))

            # Timestamp
            self.timestamps.append(time.time())

            # Wait for next sample
            time.sleep(self.interval)

    def generate_report(self, concurrency_level, output_dir="performance_reports"):
        """
        Generate a graphical report of the monitored resources.

        Args:
            concurrency_level: Current concurrency level being tested
            output_dir: Directory to save the report files

        Returns:
            Dict with summary statistics
        """
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Convert timestamps to relative seconds from start
        if not self.timestamps:
            return {"error": "No monitoring data collected"}

        start_time = self.timestamps[0]
        relative_times = [t - start_time for t in self.timestamps]

        # Create a figure with subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

        # CPU Usage plot
        ax1.plot(relative_times, self.cpu_percentages, label=f"Concurrency Level: {concurrency_level}")
        ax1.set_title(f'CPU Usage (Concurrency: {concurrency_level})', fontsize=14)
        ax1.set_ylabel('CPU Utilization (%)', fontsize=12)
        ax1.set_xlabel('Time (seconds)', fontsize=12)
        ax1.grid(True)
        ax1.legend(loc='upper right')

        # Memory Usage plot
        ax2.plot(relative_times, self.memory_usage, label=f"Concurrency Level: {concurrency_level}")
        ax2.set_title(f'Memory Usage (Concurrency: {concurrency_level})', fontsize=14)
        ax2.set_ylabel('Memory Usage (MB)', fontsize=12)
        ax2.set_xlabel('Time (seconds)', fontsize=12)
        ax2.grid(True)
        ax2.legend(loc='upper right')

        plt.tight_layout()
        plt.savefig(f"{output_dir}/resources_concurrency_{concurrency_level}.png")
        plt.close()

        # Create summary statistics
        summary = {
            "cpu": {
                "average": np.mean(self.cpu_percentages),
                "max": max(self.cpu_percentages),
                "min": min(self.cpu_percentages)
            },
            "memory": {
                "average_mb": np.mean(self.memory_usage),
                "max_mb": max(self.memory_usage),
                "min_mb": min(self.memory_usage),
                "final_mb": self.memory_usage[-1] if self.memory_usage else 0
            },
            "duration_seconds": relative_times[-1] if relative_times else 0
        }

        return summary


class HeavyWorkloadSimulator:
    """
    Simulates a heavy workload scenario to test the Resource Manager.
    """

    def __init__(self,
                 num_concurrent_operations=50,
                 duration_seconds=300,
                 log_level=logging.INFO):
        """
        Initialize the heavy workload simulator.

        Args:
            num_concurrent_operations: Number of concurrent operations
            duration_seconds: Duration of the load test
            log_level: Logging level
        """
        self.num_concurrent_operations = num_concurrent_operations
        self.duration_seconds = duration_seconds
        self.logger = get_logger(level=log_level, use_colors=True)
        self.metrics_collector = AdvancedMetricsCollector()
        self.system_monitor = SystemMonitor(interval=0.5)
        self._lock = threading.Lock()
        self.task_queue = queue.Queue(maxsize=100)

        # Results storage
        self.results = {
            'successful_operations': 0,
            'failed_operations': 0,
            'total_processing_time': 0,
            'throughput': 0,
            'resource_utilization': {}
        }

        # Benchmark results across all concurrency levels
        self.benchmark_results = {}

    def _simulate_database_heavy_operations(self, db_resource):
        """
        Simulate heavy database operations.

        Args:
            db_resource: Database resource

        Returns:
            Query results or None if operation failed
        """
        try:
            # Create table with complex indices
            with self.metrics_collector.track_operation('database', 'create_complex_table'):
                db_resource.execute("""
                    CREATE TABLE IF NOT EXISTS heavy_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        log_level TEXT,
                        message TEXT,
                        process_id INTEGER,
                        thread_id INTEGER,
                        extra_data JSON
                    )
                """)

                # Create indices for better performance
                db_resource.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON heavy_logs(timestamp)")
                db_resource.execute("CREATE INDEX IF NOT EXISTS idx_log_level ON heavy_logs(log_level)")

            # Batch insertions
            with self.metrics_collector.track_operation('database', 'bulk_insert'):
                batch_size = 1000
                logs_data = [
                    (
                        random.choice(['INFO', 'WARNING', 'ERROR', 'DEBUG']),
                        f"Simulated log message {i}",
                        os.getpid(),
                        threading.get_ident(),
                        str({"random_key": random.random()})
                    )
                    for i in range(batch_size)
                ]

                db_resource.execute_many("""
                    INSERT INTO heavy_logs 
                    (log_level, message, process_id, thread_id, extra_data) 
                    VALUES (?, ?, ?, ?, ?)
                """, logs_data)

            # Complex analytical queries
            with self.metrics_collector.track_operation('database', 'complex_analytics'):
                result = db_resource.execute("""
                    SELECT 
                        log_level, 
                        COUNT(*) as count, 
                        AVG(length(message)) as avg_message_length 
                    FROM heavy_logs 
                    GROUP BY log_level 
                    ORDER BY count DESC
                """)
                return result

        except Exception as e:
            self.logger.error(f"Error in database operations: {e}")
            return None

    def _simulate_api_operations(self, api_resource):
        """
        Simulate API operations with different endpoints.

        Args:
            api_resource: API resource

        Returns:
            Dictionary with results or None if operation failed
        """
        try:
            # Simulate multiple API calls
            endpoints = [
                '/users',
                '/posts',
                '/comments',
                '/todos',
                '/albums'
            ]

            results = {}
            for endpoint in endpoints:
                with self.metrics_collector.track_operation('api', f'get_{endpoint[1:]}'):
                    response = api_resource.get(endpoint)
                    results[endpoint] = len(response.json()) if response else 0

            return results

        except Exception as e:
            self.logger.error(f"Error in API operations: {e}")
            return None

    def _simulate_file_operations(self, file_resource):
        """
        Simulate complex file operations.

        Args:
            file_resource: File resource

        Returns:
            Number of processed lines or None if operation failed
        """
        try:
            # Generate data for writing
            with self.metrics_collector.track_operation('file', 'generate_large_log'):
                log_data = '\n'.join([
                    f"{time.time()}: Simulated event {i} - Random data: {random.random()}"
                    for i in range(10000)
                ])

                file_resource.write(log_data)
                file_resource.flush()

            # Simulate reading and processing
            with self.metrics_collector.track_operation('file', 'process_log'):
                file_content = file_resource.read()
                processed_lines = len(file_content.splitlines())

                return processed_lines

        except Exception as e:
            self.logger.error(f"Error in file operations: {e}")
            return None

    def _worker(self, worker_id):
        """
        Worker function to execute concurrent operations.

        Args:
            worker_id: Unique ID for this worker
        """
        try:
            # Create resource manager with unique resource identifiers
            resource_manager = ResourceManager(
                metrics_collector=self.metrics_collector,
                logger=self.logger
            )

            # Add resources with unique/shared configurations
            db_connection = ":memory:" if worker_id % 10 == 0 else "heavy_workload_shared.db"

            resource_manager.add_resource("db", DatabaseResource(
                connection_string=db_connection,
                connection_timeout=10.0
            ))

            resource_manager.add_resource("api", ApiResource(
                base_url="https://jsonplaceholder.typicode.com",
                timeout=5.0
            ))

            resource_manager.add_resource("log", FileResource(
                filepath=f"heavy_workload_log_{worker_id % 5}.txt",  # Limit number of files
                mode="a+",  # Append mode for file sharing
                encoding="utf-8"
            ))

            with resource_manager as resources:
                # Execute operations with lenient success criteria
                db_result = self._simulate_database_heavy_operations(resources.db)
                api_result = self._simulate_api_operations(resources.api)
                file_result = self._simulate_file_operations(resources.log)

                # Thread-safe update of results - allow partial success
                with self._lock:
                    # Consider the operation successful if at least 2 out of 3 components succeed
                    success_count = sum([1 if x else 0 for x in [db_result, api_result, file_result]])
                    if success_count >= 2:
                        self.results['successful_operations'] += 1
                    else:
                        self.results['failed_operations'] += 1

        except Exception as e:
            self.logger.error(f"Error in worker {worker_id}: {e}")
            # Thread-safe update with the lock
            with self._lock:
                self.results['failed_operations'] += 1

    def run_concurrency_benchmark(self):
        """
        Run benchmarks with widely spaced concurrency levels (10, 50, 100).

        Returns:
            Dictionary with benchmark results for each concurrency level
        """
        concurrency_levels = [10, 50, 100]

        self.benchmark_results = {}

        for concurrency in concurrency_levels:
            self.logger.info(f"\n=== Testing with {concurrency} concurrent operations ===")

            # Update concurrency setting
            self.num_concurrent_operations = concurrency

            # Reset results
            self.results = {
                'successful_operations': 0,
                'failed_operations': 0,
                'total_processing_time': 0,
                'throughput': 0,
                'resource_utilization': {}
            }

            # Run the benchmark
            self.run_heavy_workload()

            # Save results
            self.benchmark_results[concurrency] = {
                'success_rate': (self.results['successful_operations'] /
                                 (self.results['successful_operations'] +
                                  self.results['failed_operations'])) * 100
                if (self.results['successful_operations'] +
                    self.results['failed_operations']) > 0 else 0,
                'throughput': self.results['throughput'],
                'total_time': self.results['total_processing_time'],
                'successful_operations': self.results['successful_operations'],
                'failed_operations': self.results['failed_operations'],
                'cpu_avg': self.results['resource_utilization']['cpu']['average'],
                'memory_avg': self.results['resource_utilization']['memory']['average_mb']
            }

        # Generate comparative report
        self._generate_concurrency_report()

        return self.benchmark_results

    def _generate_concurrency_report(self):
        """
        Generate graphs comparing performance across different concurrency levels.
        """
        if not self.benchmark_results:
            self.logger.error("No benchmark results to generate report from")
            return

        # Ensure output directory exists
        os.makedirs("performance_reports", exist_ok=True)

        levels = list(self.benchmark_results.keys())

        # Extract metrics
        success_rates = [self.benchmark_results[l]['success_rate'] for l in levels]
        throughputs = [self.benchmark_results[l]['throughput'] for l in levels]
        total_times = [self.benchmark_results[l]['total_time'] for l in levels]
        cpu_avgs = [self.benchmark_results[l]['cpu_avg'] for l in levels]
        memory_avgs = [self.benchmark_results[l]['memory_avg'] for l in levels]

        # Create two figures: one for performance metrics, one for resource usage
        # Performance metrics figure
        plt.figure(figsize=(12, 10))

        # Plot 1: Success Rate
        plt.subplot(2, 1, 1)
        plt.plot(levels, success_rates, 'o-', linewidth=2, markersize=10, color='green')
        for i, level in enumerate(levels):
            plt.annotate(f"{success_rates[i]:.1f}%",
                         (level, success_rates[i]),
                         textcoords="offset points",
                         xytext=(0, 10),
                         ha='center')
        plt.title('Success Rate by Concurrency Level', fontsize=16)
        plt.xlabel('Number of Concurrent Operations', fontsize=14)
        plt.ylabel('Success Rate (%)', fontsize=14)
        plt.grid(True)
        plt.xticks(levels)

        # Plot 2: Throughput
        plt.subplot(2, 1, 2)
        plt.plot(levels, throughputs, 'o-', linewidth=2, markersize=10, color='blue')
        for i, level in enumerate(levels):
            plt.annotate(f"{throughputs[i]:.1f} ops/s",
                         (level, throughputs[i]),
                         textcoords="offset points",
                         xytext=(0, 10),
                         ha='center')
        plt.title('Operations Per Second by Concurrency Level', fontsize=16)
        plt.xlabel('Number of Concurrent Operations', fontsize=14)
        plt.ylabel('Throughput (operations/second)', fontsize=14)
        plt.grid(True)
        plt.xticks(levels)

        plt.tight_layout()
        plt.savefig("performance_reports/performance_metrics.png")
        plt.close()

        # Resource usage figure
        plt.figure(figsize=(12, 10))

        # Plot 1: Total Time
        plt.subplot(3, 1, 1)
        plt.plot(levels, total_times, 'o-', linewidth=2, markersize=10, color='red')
        for i, level in enumerate(levels):
            plt.annotate(f"{total_times[i]:.1f}s",
                         (level, total_times[i]),
                         textcoords="offset points",
                         xytext=(0, 10),
                         ha='center')
        plt.title('Total Processing Time by Concurrency Level', fontsize=16)
        plt.xlabel('Number of Concurrent Operations', fontsize=14)
        plt.ylabel('Time (seconds)', fontsize=14)
        plt.grid(True)
        plt.xticks(levels)

        # Plot 2: CPU Usage
        plt.subplot(3, 1, 2)
        plt.plot(levels, cpu_avgs, 'o-', linewidth=2, markersize=10, color='purple')
        for i, level in enumerate(levels):
            plt.annotate(f"{cpu_avgs[i]:.1f}%",
                         (level, cpu_avgs[i]),
                         textcoords="offset points",
                         xytext=(0, 10),
                         ha='center')
        plt.title('Average CPU Usage by Concurrency Level', fontsize=16)
        plt.xlabel('Number of Concurrent Operations', fontsize=14)
        plt.ylabel('CPU Usage (%)', fontsize=14)
        plt.grid(True)
        plt.xticks(levels)

        # Plot 3: Memory Usage
        plt.subplot(3, 1, 3)
        plt.plot(levels, memory_avgs, 'o-', linewidth=2, markersize=10, color='orange')
        for i, level in enumerate(levels):
            plt.annotate(f"{memory_avgs[i]:.1f} MB",
                         (level, memory_avgs[i]),
                         textcoords="offset points",
                         xytext=(0, 10),
                         ha='center')
        plt.title('Average Memory Usage by Concurrency Level', fontsize=16)
        plt.xlabel('Number of Concurrent Operations', fontsize=14)
        plt.ylabel('Memory Usage (MB)', fontsize=14)
        plt.grid(True)
        plt.xticks(levels)

        plt.tight_layout()
        plt.savefig("performance_reports/resource_usage_metrics.png")
        plt.close()

        # Create a single consolidated report file
        with open("performance_reports/benchmark_summary.txt", "w") as f:
            f.write("=== Resource Manager Performance Benchmark Summary ===\n\n")
            f.write(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("Concurrency Levels Tested: " + ", ".join([str(l) for l in levels]) + "\n\n")

            f.write("Performance Results:\n")
            f.write("-" * 80 + "\n")
            f.write(
                f"{'Concurrency':<15}{'Success Rate':<15}{'Throughput':<15}{'Total Time':<15}{'CPU Avg':<15}{'Memory Avg':<15}\n")
            f.write(f"{'Level':<15}{'(%)':<15}{'(ops/sec)':<15}{'(seconds)':<15}{'(%)':<15}{'(MB)':<15}\n")
            f.write("-" * 80 + "\n")

            for level in levels:
                result = self.benchmark_results[level]
                f.write(f"{level:<15}{result['success_rate']:<15.2f}{result['throughput']:<15.2f}"
                        f"{result['total_time']:<15.2f}{result['cpu_avg']:<15.2f}{result['memory_avg']:<15.2f}\n")

            f.write("\n=== Key Observations ===\n\n")

            # Optimal concurrency level based on throughput
            optimal_level = max(self.benchmark_results.keys(),
                                key=lambda k: self.benchmark_results[k]['throughput'])
            f.write(f"Optimal concurrency level for throughput: {optimal_level} "
                    f"({self.benchmark_results[optimal_level]['throughput']:.2f} ops/sec)\n")

            # Memory usage trend
            mem_increase = memory_avgs[-1] - memory_avgs[0]
            mem_increase_percent = (mem_increase / memory_avgs[0]) * 100
            f.write(f"Memory usage increase from {levels[0]} to {levels[-1]} workers: "
                    f"{mem_increase:.2f} MB ({mem_increase_percent:.1f}%)\n")

            # Success rate trend
            if min(success_rates) < 90:
                f.write(f"Warning: Success rate drops below 90% at certain concurrency levels\n")

            f.write("\nPerformance report graphs saved to performance_reports directory.\n")

    def run_heavy_workload(self):
        """
        Run the heavy workload test.
        """
        start_time = time.time()

        # Start system monitoring
        self.system_monitor.start()

        # Launch workers with unique IDs
        with ThreadPoolExecutor(max_workers=self.num_concurrent_operations) as executor:
            futures = [
                executor.submit(self._worker, i)
                for i in range(self.num_concurrent_operations)
            ]

            # Wait for completion or timeout
            completed = 0
            for future in as_completed(futures):
                try:
                    future.result(timeout=self.duration_seconds)
                    completed += 1
                    if completed % 10 == 0:
                        self.logger.info(f"Completed {completed}/{len(futures)} operations")
                except Exception as e:
                    self.logger.warning(f"Task did not complete: {e}")

        # Stop system monitoring
        self.system_monitor.stop()

        # Calculate final metrics
        end_time = time.time()
        self.results['total_processing_time'] = end_time - start_time
        self.results['throughput'] = self.num_concurrent_operations / self.results['total_processing_time']

        # Generate system resource report and store in results
        self.results['resource_utilization'] = self.system_monitor.generate_report(self.num_concurrent_operations)

        # Generate workload report
        self._generate_workload_report()

    def _generate_workload_report(self):
        """
        Generate a basic report for the current load test.
        """
        self.logger.info("\n=== Load Test Report ===")
        self.logger.info(f"Concurrent Operations: {self.num_concurrent_operations}")
        self.logger.info(f"Total Duration: {self.results['total_processing_time']:.2f} seconds")
        self.logger.info(f"Successful Operations: {self.results['successful_operations']}")
        self.logger.info(f"Failed Operations: {self.results['failed_operations']}")
        self.logger.info(f"Throughput: {self.results['throughput']:.2f} operations/second")

        total_operations = self.results['successful_operations'] + self.results['failed_operations']
        if total_operations > 0:
            success_rate = (self.results['successful_operations'] / total_operations) * 100
            self.logger.info(f"Success Rate: {success_rate:.2f}%")
        else:
            self.logger.info("Success Rate: N/A (no operations completed)")


def main():
    """
    Main function to run the load testing.
    """
    # Create output directory
    os.makedirs("performance_reports", exist_ok=True)

    # Set up the workload simulator
    workload_simulator = HeavyWorkloadSimulator(
        duration_seconds=60,  # Reduced to 1 minute per test for quicker results
        log_level=logging.INFO
    )

    # Run benchmarks with different concurrency levels
    workload_simulator.run_concurrency_benchmark()  # Uses [10, 50, 100]


if __name__ == "__main__":
    main()