"""
Adapter for sending data to a message queue.
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from ..core.entities.data_item import DataItem
from ..core.interfaces.output_sink import BaseOutputSink

logger = logging.getLogger(__name__)

class MessageQueueOutputSink(BaseOutputSink):
    """
    Adapter for sending data to a message queue.
    
    Generic implementation that can be specialized for
    different message brokers (RabbitMQ, Kafka, etc).
    """
    
    def __init__(self, 
                connection_params: Dict[str, Any],
                queue_name: str,
                max_retries: int = 3,
                serializer: Optional[callable] = None):
        """
        Initializes the message queue adapter.
        
        Args:
            connection_params: Connection parameters
            queue_name: Name of the queue for sending messages
            max_retries: Maximum retry attempts on failure
            serializer: Optional custom serializer function
        """
        self.connection_params = connection_params
        self.queue_name = queue_name
        self.max_retries = max_retries
        self.serializer = serializer or self._default_serializer
        self.connection = None
        self._connect()

    def _default_serializer(self, item: DataItem) -> str:
        """
        Default serialization method with datetime handling.

        Args:
            item: The item to serialize

        Returns:
            JSON string representation of the item
        """

        # Use um JSONEncoder personalizado
        class DateTimeEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return super().default(obj)

        # Crie um dicionário a partir do item
        data_dict = {
            'id': item.id,
            'timestamp': item.timestamp,
            'data': item.data,
            'metadata': item.metadata
        }

        return json.dumps(data_dict, cls=DateTimeEncoder)
    
    def _connect(self) -> bool:
        """
        Establishes connection to the message queue.
        
        Note: Generic implementation - would be replaced by
        specific code for the chosen message broker.
        
        Returns:
            True if connection successful, False otherwise
        """
        logger.info(f"Connecting to message queue: {self.connection_params.get('host')}")
        try:
            # This would be real connection code
            self.connection = {"connected": True}
            logger.info("Connection to message queue established")
            return True
        except Exception as e:
            logger.error(f"Error connecting to message queue: {e}")
            self.connection = None
            return False
    
    def send(self, item: DataItem) -> bool:
        """
        Sends an item to the message queue.
        
        Args:
            item: Item to be sent
            
        Returns:
            True if success, False otherwise
        """
        if not self.connection:
            if not self._connect():
                logger.error("Failed to establish message queue connection")
                return False
        
        try:
            # Serialize the item
            message_data = self.serializer(item)
            
            # Here would be the real message publishing code
            logger.debug(f"Publishing message for item {item.id} to queue {self.queue_name}")
            
            # Sample implementation
            # channel = self.connection.channel()
            # channel.basic_publish(
            #     exchange='',
            #     routing_key=self.queue_name,
            #     body=message_data,
            #     properties=pika.BasicProperties(
            #         delivery_mode=2,  # make message persistent
            #     )
            # )
            
            return True
        except Exception as e:
            logger.error(f"Error publishing to message queue: {e}")
            
            # Retry logic
            for attempt in range(self.max_retries):
                try:
                    logger.info(f"Retrying publication, attempt {attempt + 1}")
                    # Retry code here
                    return True
                except Exception as retry_error:
                    logger.error(f"Retry attempt {attempt + 1} failed: {retry_error}")
            
            return False
    
    def send_batch(self, items: List[DataItem]) -> int:
        """
        Sends multiple items to the message queue.
        
        Args:
            items: List of items to be sent
            
        Returns:
            Number of successfully sent items
        """
        # Message queues typically don't have a true batch send operation
        # (unlike databases), so we implement it as multiple individual sends
        success_count = 0
        
        # Some message brokers might support transaction batching
        try:
            # Start transaction if supported
            # channel.tx_select()
            
            for item in items:
                if self.send(item):
                    success_count += 1
            
            # Commit transaction if supported
            # channel.tx_commit()
            
            logger.info(f"Batch published {success_count}/{len(items)} messages to {self.queue_name}")
            return success_count
            
        except Exception as e:
            logger.error(f"Error in batch publishing: {e}")
            # Rollback transaction if supported
            # try:
            #     channel.tx_rollback()
            # except Exception as rollback_error:
            #     logger.error(f"Error rolling back transaction: {rollback_error}")
            
            # Fallback to individual sends without transaction
            logger.info("Falling back to individual message publishing")
            return sum(1 for item in items if self.send(item))
    
    def __del__(self) -> None:
        """Automatic connection cleanup."""
        if self.connection:
            # Here would be connection closing code
            logger.info("Message queue connection closed")