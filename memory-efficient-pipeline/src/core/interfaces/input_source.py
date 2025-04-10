"""
Interface for data input sources.
"""
from abc import ABC, abstractmethod
from typing import Generator, Dict, Any

class InputSource(ABC):
    """
    Contract for components that provide data to the pipeline.
    Can be a webhook, file reader, etc.
    """
    
    @abstractmethod
    def get_data_stream(self) -> Generator[Dict[str, Any], None, None]:
        """
        Creates a generator that provides data items.
        
        Yields:
            Raw data items to be processed by the pipeline
        """
        pass