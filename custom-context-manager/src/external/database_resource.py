"""
Database resource implementation.

This module provides a concrete implementation of the Resource interface
for database connections.
"""
import random
import time
import logging
import threading
from typing import Any, Dict, List, Optional, Tuple, Union
import sqlite3

from ..core import Resource

class DatabaseResource(Resource):
    """
    Resource implementation for database connections.

    This class manages connections to a database system,
    ensuring proper acquisition and release of connections.
    """

    def __init__(
        self,
        connection_string: str,
        connection_timeout: float = 30.0,
        retry_attempts: int = 3,
        retry_delay: float = 1.0,
        max_connections: int = 10,  # New parameter for connection pool
        name: Optional[str] = None,
    ):
        """
        Initialize a database resource.

        For demonstration, this uses SQLite (which can work in-memory with ':memory:').
        In a real application, you would connect to your actual database system.

        Args:
            connection_string: Connection string for the database
            connection_timeout: Timeout for connection attempts in seconds
            retry_attempts: Number of retry attempts for failed connections
            retry_delay: Delay between retry attempts in seconds
            max_connections: Maximum number of concurrent connections
            name: Optional custom name for the resource
        """
        self._connection_string = connection_string
        self._connection_timeout = connection_timeout
        self._retry_attempts = retry_attempts
        self._retry_delay = retry_delay
        self._custom_name = name

        # Thread-local storage for connections
        self._thread_local = threading.local()

        # Connection pool management
        self._connection_lock = threading.Lock()
        self._connection_pool = []
        self._max_connections = max_connections

        self._logger = logging.getLogger(__name__)

    @property
    def name(self) -> str:
        """
        Get the name of the resource.

        Returns:
            str: The custom name if provided, otherwise the class name
        """
        return self._custom_name or super().name

    def _create_connection(self):
        """
        Create a new database connection.

        Returns:
            A new database connection

        Raises:
            ConnectionError: If connection creation fails
        """
        attempt = 0
        last_error = None

        while attempt < self._retry_attempts:
            try:
                self._logger.debug(
                    f"Connecting to database '{self.name}' "
                    f"(attempt {attempt + 1}/{self._retry_attempts})"
                )

                conn = sqlite3.connect(
                    self._connection_string,
                    timeout=self._connection_timeout,
                    check_same_thread=False  # Allow cross-thread use
                )

                # Test the connection
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.close()

                return conn

            except Exception as e:
                last_error = e
                self._logger.warning(
                    f"Failed to connect to database '{self.name}': {e}. "
                    f"Retrying in {self._retry_delay}s..."
                )
                attempt += 1
                time.sleep(self._retry_delay)

        raise ConnectionError(
            f"Failed to connect to database '{self.name}' "
            f"after {self._retry_attempts} attempts: {last_error}"
        )

    def acquire(self) -> None:
        """
        Acquire a database connection.

        This method attempts to establish a connection to the database.
        It will retry according to the configured retry attempts.

        Raises:
            ConnectionError: If the connection cannot be established
        """
        with self._connection_lock:
            # Check if thread already has a connection
            if not hasattr(self._thread_local, 'connection'):
                # If pool isn't full, create new connection
                if len(self._connection_pool) < self._max_connections:
                    connection = self._create_connection()
                    self._connection_pool.append(connection)
                    self._thread_local.connection = connection
                else:
                    # Reuse an existing connection from the pool
                    self._thread_local.connection = self._connection_pool[
                        random.randint(0, len(self._connection_pool) - 1)
                    ]

            self._logger.info(f"Connected to database '{self.name}'")

    def release(self) -> None:
        """
        Release the database connection.

        This method closes the connection to the database.

        Raises:
            RuntimeError: If there's an error closing the connection
        """
        with self._connection_lock:
            if hasattr(self._thread_local, 'connection'):
                try:
                    self._logger.debug(f"Closing database connection '{self.name}'")
                    # Instead of closing, we'll keep the connection in the pool
                    del self._thread_local.connection
                    self._logger.info(f"Database connection '{self.name}' released")

                except Exception as e:
                    self._logger.error(f"Error releasing database connection '{self.name}': {e}")
                    raise RuntimeError(f"Error releasing database connection: {e}")

    @property
    def is_acquired(self) -> bool:
        """
        Check if the database connection is acquired.

        Returns:
            bool: True if the connection is acquired, False otherwise
        """
        return hasattr(self._thread_local, 'connection')

    def execute(self, query: str, parameters: Optional[Union[Tuple, Dict[str, Any]]] = None) -> List[Tuple]:
        """
        Execute a query on the database.

        Args:
            query: SQL query to execute
            parameters: Optional parameters for the query

        Returns:
            List[Tuple]: Result rows from the query

        Raises:
            RuntimeError: If the connection is not acquired
            Exception: If the query execution fails
        """
        # Simulate processing time
        time.sleep(random.uniform(0.01, 0.1))

        if not hasattr(self._thread_local, 'connection'):
            raise RuntimeError(f"Database connection '{self.name}' not acquired")

        cursor = self._thread_local.connection.cursor()
        try:
            if parameters:
                cursor.execute(query, parameters)
            else:
                cursor.execute(query)

            result = cursor.fetchall()
            self._thread_local.connection.commit()
            return result

        except Exception as e:
            self._thread_local.connection.rollback()
            self._logger.error(f"Error executing query on '{self.name}': {e}")
            raise

        finally:
            cursor.close()

    def execute_many(self, query: str, parameters_list: List[Tuple]) -> int:
        """
        Execute a query multiple times with different parameter sets.
        Uses batching for efficiency.
        """
        if not hasattr(self._thread_local, 'connection'):
            raise RuntimeError(f"Database connection '{self.name}' not acquired")

        cursor = self._thread_local.connection.cursor()
        affected_rows = 0

        try:
            # Process in smaller batches for better performance/reliability
            batch_size = min(1000, max(10, len(parameters_list) // 10))

            for i in range(0, len(parameters_list), batch_size):
                batch = parameters_list[i:i + batch_size]

                # Use executor.executemany when available
                cursor.executemany(query, batch)

                # Track affected rows
                if hasattr(cursor, 'rowcount'):
                    affected_rows += cursor.rowcount

                # Commit each batch to avoid large transactions
                self._thread_local.connection.commit()

            return affected_rows

        except Exception as e:
            self._thread_local.connection.rollback()
            self._logger.error(f"Error executing batch query on '{self.name}': {e}")
            raise

        finally:
            cursor.close()

    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the resource.

        Returns:
            Dict[str, Any]: A dictionary containing status information
        """
        status = super().get_status()
        status.update({
            "type": "database",
            "connection_string": self._connection_string.split(":")[-1],  # Don't show full connection string
            "timeout": self._connection_timeout,
            "retry_attempts": self._retry_attempts,
            "total_connections": len(self._connection_pool),
            "max_connections": self._max_connections
        })
        return status