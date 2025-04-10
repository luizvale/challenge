#!/usr/bin/env python3
"""
Basic usage example for the resource manager.

This example demonstrates the fundamental usage of the ResourceManager
to manage database, API, and file resources (all emulated).
"""
import os
import sys
import logging
import time

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.use_cases.resource_manager import ResourceManager
from src.use_cases.metrics import BasicMetricsCollector
from src.external.database_resource import DatabaseResource
from src.external.api_resource import ApiResource
from src.external.file_resource import FileResource
from src.external.logger import get_logger


def main():
    """Run the basic usage example."""
    # Set up logging
    logger = get_logger(level=logging.INFO, use_colors=True)
    logger.info("Starting resource manager basic usage example")
    
    # Set up metrics collection
    metrics = BasicMetricsCollector()
    
    # Create a resource manager with our logger and metrics
    manager = ResourceManager(metrics_collector=metrics, logger=logger)
    
    # Create some emulated resources (no real infrastructure dependencies)
    db = DatabaseResource(
        connection_string=":memory:",  # In-memory SQLite DB for example
        connection_timeout=5.0,
        retry_attempts=2
    )
    
    api = ApiResource(
        base_url="https://api.example.com",  # This will be emulated
        api_key="example_key_12345",
        timeout=10.0
    )
    
    log_file = FileResource(
        filepath="example_log.txt",
        mode="w",
        encoding="utf-8"
    )
    
    # Add resources to the manager
    manager.add_resource("db", db)
    manager.add_resource("api", api)
    manager.add_resource("log", log_file)
    
    # Use the resources with the context manager
    try:
        logger.info("Entering resource manager context")
        
        with manager as resources:
            logger.info("Resources acquired, performing operations")
            
            # Use the emulated database
            try:
                logger.info("Executing database query")
                resources.db.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, name TEXT)")
                resources.db.execute("INSERT INTO test (name) VALUES (?)", ("Example",))
                result = resources.db.execute("SELECT * FROM test")
                logger.info(f"Query result: {result}")
            except Exception as e:
                logger.error(f"Database operation failed: {e}")
            
            # Use the emulated API
            try:
                logger.info("Making API request")
                response = resources.api.get("/users")
                logger.info(f"API response status: {response['status']}")
            except Exception as e:
                logger.error(f"API request failed: {e}")
            
            # Use the file
            try:
                logger.info("Writing to file")
                resources.log.write("This is a test log entry\n")
                resources.log.write("All operations completed successfully\n")
            except Exception as e:
                logger.error(f"File operation failed: {e}")
            
            # Show resource status
            status = resources.status()
            logger.info(f"Resources status: {len(status['resources'])} resources managed")
            
            # Simulate some work
            logger.info("Simulating work...")
            time.sleep(1)
            
        logger.info("Exited resource manager context, all resources released")
        
    except Exception as e:
        logger.error(f"Error during resource management: {e}")
    
    # Show metrics
    metrics_data = metrics.get_metrics()
    logger.info(f"Total resources managed: {len(metrics_data['resources'])}")
    logger.info(f"Total acquisition time: {metrics_data['total_acquisition_time']:.6f}s")
    logger.info(f"Total release time: {metrics_data['total_release_time']:.6f}s")


if __name__ == "__main__":
    main()