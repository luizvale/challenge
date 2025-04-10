"""
Adapter for receiving webhook data.
"""
import json
import logging
from typing import Dict, Any, Optional, Callable, List, Generator
from ..core.interfaces.input_source import InputSource

logger = logging.getLogger(__name__)

class WebhookAdapter(InputSource):
    """
    Adapter for receiving data from an HTTP webhook.
    
    Provides an iterator that generates data as it arrives,
    allowing streaming processing with constant memory usage.
    """
    
    def __init__(self, 
                buffer_size: int = 100,
                validator: Optional[Callable[[Dict[str, Any]], bool]] = None):
        """
        Initializes the adapter.
        
        Args:
            buffer_size: Maximum size of the internal buffer
            validator: Optional function to validate received data
        """
        self.buffer_size = buffer_size
        self.validator = validator
        self.buffer: List[Dict[str, Any]] = []
    
    def receive_webhook_data(self, raw_data: str) -> bool:
        """
        Receives raw data from the webhook and adds it to the buffer.
        
        Args:
            raw_data: JSON string from webhook
            
        Returns:
            True if processed successfully, False otherwise
        """
        try:
            data = json.loads(raw_data)
            
            # Validate if configured
            if self.validator and not self.validator(data):
                logger.warning(f"Invalid data: {raw_data[:100]}...")
                return False
            
            # Implement backpressure if buffer is full
            if len(self.buffer) >= self.buffer_size:
                logger.warning("Buffer full, applying backpressure")
                # We could implement different strategies:
                # 1. Discard oldest data
                # 2. Discard newest data (this case)
                # 3. Temporarily increase buffer
                return False
            
            # Add to buffer
            self.buffer.append(data)
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return False
        except Exception as e:
            logger.error(f"Error processing webhook data: {e}")
            return False
    
    def get_data_stream(self) -> Generator[Dict[str, Any], None, None]:
        """
        Creates an iterator over the buffered data.
        
        Yields:
            Data received from the webhook
        """
        while self.buffer:
            yield self.buffer.pop(0)