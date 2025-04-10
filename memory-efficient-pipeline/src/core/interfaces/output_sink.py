"""
Interface for data output destinations.
"""
from abc import ABC, abstractmethod
from typing import Iterable
from ..entities.data_item import DataItem

class OutputSinkInterface(ABC):
    """
    Contract for components that receive processed data.
    Can be a database, message queue, etc.
    """
    
    @abstractmethod
    def send(self, item: DataItem) -> bool:
        """
        Sends a single item to the destination.
        
        Args:
            item: Item to be sent
            
        Returns:
            True if sent successfully, False otherwise
        """
        pass

    @abstractmethod
    def send_batch(self, items: Iterable[DataItem]) -> int:
        """
        Sends a batch of items to the destination.
        
        Args:
            items: Items to be sent
            
        Returns:
            Number of items successfully sent
        """
        pass

class BaseOutputSink(OutputSinkInterface):

    def send(self, item: DataItem) -> bool:
        """
        Sends a single item to the destination.

        Args:
            item: Item to be sent

        Returns:
            True if sent successfully, False otherwise
        """
        pass

    def send_batch(self, items: Iterable[DataItem]) -> int:
        """
        Sends a batch of items to the destination.

        Args:
            items: Items to be sent

        Returns:
            Number of items successfully sent
        """
        success_count = 0
        for item in items:
            if self.send(item):
                success_count += 1
        return success_count
