"""
Enhanced Example of Nested Resource Managers with Advanced Metrics.

Demonstrates using nested resource managers with comprehensive
performance tracking and metrics collection.
"""
import os
import sys
import logging
import time

from src.use_cases.metrics import AdvancedMetricsCollector
from src.use_cases.resource_manager import ResourceManager
from src.external.database_resource import DatabaseResource
from src.external.api_resource import ApiResource
from src.external.file_resource import FileResource
from src.external.logger import get_logger


def pretty_print_metrics(logger, metrics):
    """
    Utility function to log metrics in a readable format.

    Args:
        logger: Logging instance
        metrics: Metrics dictionary from AdvancedMetricsCollector
    """
    logger.info("\n--- Comprehensive Metrics Report ---")

    # System Metrics
    logger.info("System Metrics:")
    system_metrics = metrics['system_metrics']
    logger.info(f"Total Resources Managed: {system_metrics['total_resources_managed']}")
    logger.info(f"Total Operations: {system_metrics['total_operations']}")
    logger.info(f"Total Errors: {system_metrics['total_errors']}")

    # Bottlenecks
    logger.info("\nPerformance Bottlenecks:")
    bottlenecks = metrics['bottlenecks']
    logger.info(f"Longest Acquisition: {bottlenecks['longest_acquisition']}")
    logger.info(f"Longest Release: {bottlenecks['longest_release']}")
    logger.info("Most Frequent Operations:")
    for op, count in bottlenecks['most_frequent_operations'].items():
        logger.info(f"  {op}: {count} times")

    # Detailed Resource Metrics
    logger.info("\nResource Details:")
    for resource_name, resource_details in metrics['resource_details'].items():
        logger.info(f"\n{resource_name.capitalize()} Resource:")

        # Acquisition Metrics
        acq_stats = resource_details['acquisition_stats']
        logger.info("Acquisition Statistics:")
        logger.info(f"  Count: {acq_stats['count']}")
        logger.info(f"  Average Time: {acq_stats['average']:.6f}s")
        logger.info(f"  Min Time: {acq_stats['min']:.6f}s")
        logger.info(f"  Max Time: {acq_stats['max']:.6f}s")

        # Release Metrics
        rel_stats = resource_details['release_stats']
        logger.info("Release Statistics:")
        logger.info(f"  Count: {rel_stats['count']}")
        logger.info(f"  Average Time: {rel_stats['average']:.6f}s")
        logger.info(f"  Min Time: {rel_stats['min']:.6f}s")
        logger.info(f"  Max Time: {rel_stats['max']:.6f}s")

        # Operation Metrics
        logger.info("Operations:")
        for op_name, op_details in resource_details['operations'].items():
            logger.info(f"  {op_name}:")
            perf = op_details['performance']
            logger.info(f"    Count: {op_details['count']}")
            logger.info(f"    Average Time: {perf['average']:.6f}s")
            logger.info(f"    Min Time: {perf['min']:.6f}s")
            logger.info(f"    Max Time: {perf['max']:.6f}s")

        # Error Metrics
        error_stats = resource_details['error_stats']
        logger.info("Error Statistics:")
        logger.info(f"  Total Errors: {error_stats['count']}")
        if error_stats['error_details']:
            logger.info("  Error Details:")
            for err in error_stats['error_details']:
                logger.info(f"    {err}")


def main():
    """Run the enhanced nested managers example."""
    # Set up logging
    logger = get_logger(level=logging.INFO, use_colors=True)
    logger.info("Starting enhanced nested resource managers example")

    # Setup advanced metrics collection
    outer_metrics = AdvancedMetricsCollector()
    inner_metrics = AdvancedMetricsCollector()

    # Create outer resource manager for long-lived resources
    outer_manager = ResourceManager(metrics_collector=outer_metrics, logger=logger)

    # Add resources to outer manager
    outer_manager.add_resource("db", DatabaseResource(
        connection_string="example.db",
        connection_timeout=5.0
    ))

    outer_manager.add_resource("log", FileResource(
        filepath="nested_example_log.txt",
        mode="w",
        encoding="utf-8"
    ))

    logger.info("Entering outer resource manager context")

    # Use the outer manager with long-lived resources
    with outer_manager as outer_resources:
        logger.info("Outer resources acquired")

        # Write to the log file
        outer_resources.log.write("Outer manager initialized\n")

        # Simulate multiple operations that use their own resources
        for i in range(3):
            logger.info(f"Starting operation {i+1}")

            # Create inner resource manager for operation-specific resources
            inner_manager = ResourceManager(metrics_collector=inner_metrics, logger=logger)

            # Add resources to inner manager
            inner_manager.add_resource("api", ApiResource(
                base_url=f"https://api{i+1}.example.com",
                timeout=5.0
            ))

            inner_manager.add_resource("temp_file", FileResource(
                filepath=f"temp_{i+1}.txt",
                mode="w+",
                encoding="utf-8"
            ))

            logger.info(f"Entering inner resource manager {i+1} context")

            # Use the inner manager
            try:
                with inner_manager as inner_resources:
                    logger.info(f"Inner resources {i+1} acquired")

                    # Use database from outer manager
                    with outer_metrics.track_operation("db", "create_table"):
                        outer_resources.db.execute(
                            "CREATE TABLE IF NOT EXISTS operations (id INTEGER PRIMARY KEY, operation TEXT)"
                        )

                    with outer_metrics.track_operation("db", "insert_operation"):
                        outer_resources.db.execute(
                            "INSERT INTO operations (operation) VALUES (?)",
                            (f"Operation {i+1}",)
                        )

                    # Use API from inner manager
                    with inner_metrics.track_operation("api", "get_status"):
                        api_response = inner_resources.api.get("/status")
                    logger.info(f"API {i+1} response: {api_response}")

                    # Write to temp file
                    with inner_metrics.track_operation("temp_file", "write_data"):
                        inner_resources.temp_file.write(f"Data from operation {i+1}\n")
                        inner_resources.temp_file.write(f"API response: {api_response}\n")

                    # Write to log file from outer manager
                    with outer_metrics.track_operation("log", "write_log"):
                        outer_resources.log.write(f"Operation {i+1} completed\n")

                    # Simulate work
                    time.sleep(0.5)

                logger.info(f"Inner resources {i+1} released")

            except Exception as e:
                logger.error(f"Error in inner manager {i+1}: {e}")

            logger.info(f"Operation {i+1} completed")

        # Read from database to verify all operations
        with outer_metrics.track_operation("db", "read_operations"):
            results = outer_resources.db.execute("SELECT * FROM operations")
        logger.info(f"All operations: {results}")

        # Final log entry
        with outer_metrics.track_operation("log", "write_final_log"):
            outer_resources.log.write("All operations completed\n")

    logger.info("Outer resources released")

    # Display metrics
    logger.info("\nOuter Manager Metrics:")
    pretty_print_metrics(logger, outer_metrics.get_metrics())

    logger.info("\nInner Managers Metrics:")
    pretty_print_metrics(logger, inner_metrics.get_metrics())

    logger.info("Enhanced nested resource managers example completed")

if __name__ == "__main__":
    main()