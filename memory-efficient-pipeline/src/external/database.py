"""
Adapter for sending data to a database.
"""
import logging
from typing import Dict, Any, List
from ..core.entities.data_item import DataItem
from ..core.interfaces.output_sink import BaseOutputSink

logger = logging.getLogger(__name__)

class DatabaseOutputSink(BaseOutputSink):
    """
    Adapter for sending data to a database.
    
    Generic implementation that can be specialized for
    different databases (SQL, NoSQL, etc).
    """
    
    def __init__(self, 
                connection_params: Dict[str, Any],
                table_name: str,
                batch_size: int = 50,
                retry_attempts: int = 3):
        """
        Initializes the database adapter.
        
        Args:
            connection_params: Connection parameters
            table_name: Name of the table/collection for insertion
            batch_size: Batch size for bulk insertions
            retry_attempts: Number of retry attempts on failure
        """
        self.connection_params = connection_params
        self.table_name = table_name
        self.batch_size = batch_size
        self.retry_attempts = retry_attempts
        self.connection = None
        self._connect()
    
    def _connect(self) -> bool:
        """
        Establishes connection to the database.
        
        Note: Generic implementation - would be replaced by
        specific code for the chosen database.
        
        Returns:
            True if connection successful, False otherwise
        """
        logger.info(f"Connecting to database: {self.connection_params.get('host')}")
        try:
            # This would be real connection code
            self.connection = {"connected": True}
            logger.info("Connection established successfully")
            return True
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            self.connection = None
            return False
    
    def send(self, item: DataItem) -> bool:
        """
        Sends an item to the database.
        
        Args:
            item: Item to be persisted
            
        Returns:
            True if success, False otherwise
        """
        if not self.connection:
            if not self._connect():
                logger.error("Failed to establish database connection")
                return False
        
        try:
            # Here would be the real insertion code
            logger.debug(f"Inserting item {item.id} into table {self.table_name}")
            
            # Sample implementation
            # cursor = self.connection.cursor()
            # cursor.execute("INSERT INTO ? (id, data) VALUES (?, ?)", 
            #                (self.table_name, item.id, json.dumps(item.data)))
            # self.connection.commit()
            
            return True
        except Exception as e:
            logger.error(f"Error inserting into database: {e}")
            
            # Retry logic
            for attempt in range(self.retry_attempts):
                try:
                    logger.info(f"Retrying insertion, attempt {attempt + 1}")
                    # Retry insertion code here
                    return True
                except Exception as retry_error:
                    logger.error(f"Retry attempt {attempt + 1} failed: {retry_error}")
            
            return False
    
    def send_batch(self, items: List[DataItem]) -> int:
        """
        Sends a batch of items using bulk insertion.
        
        Args:
            items: List of items to persist
            
        Returns:
            Number of successfully inserted items
        """
        if not self.connection:
            if not self._connect():
                logger.error("Failed to establish database connection")
                return 0
        
        try:
            # Here would be the real bulk insertion code
            count = len(items)
            logger.info(f"Bulk inserting {count} items into table {self.table_name}")
            
            # Sample implementation
            # cursor = self.connection.cursor()
            # values = [(item.id, json.dumps(item.data)) for item in items]
            # cursor.executemany("INSERT INTO ? (id, data) VALUES (?, ?)", 
            #                    [(self.table_name, *value) for value in values])
            # self.connection.commit()
            
            return count
        except Exception as e:
            logger.error(f"Error bulk inserting into database: {e}")
            
            # Fallback to individual insertion in case of error
            logger.info("Falling back to individual insertions")
            return sum(1 for item in items if self.send(item))
    
    def __del__(self) -> None:
        """Automatic connection cleanup."""
        if self.connection:
            # Here would be connection closing code
            logger.info("Database connection closed")