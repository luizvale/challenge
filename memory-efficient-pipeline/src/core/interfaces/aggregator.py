"""
Interface for aggregation components.
"""
from abc import ABC, abstractmethod
from typing import List, Iterable, Generator, TypeVar, Generic, Optional
from ..entities.data_item import DataItem

# Generic type for aggregation results
T = TypeVar('T')

class Aggregator(Generic[T], ABC):
    """
    Contract for data aggregators in the pipeline.
    Aggregators combine multiple items into summary results.
    """
    
    @abstractmethod
    def add_item(self, item: DataItem) -> None:
        """
        Adds an item to the aggregation state.
        
        Args:
            item: The item to be added to the aggregation
        """
        pass
    
    @abstractmethod
    def get_results(self) -> List[T]:
        """
        Retrieves current aggregation results.
        
        Returns:
            List of aggregation results
        """
        pass
    
    @abstractmethod
    def reset(self) -> None:
        """
        Resets the aggregator state.
        """
        pass
    
    def process_stream(self, 
                      stream: Iterable[DataItem], 
                      window_size: Optional[int] = None) -> Generator[List[T], None, None]:
        """
        Processes a stream of items, yielding aggregation results periodically.
        
        Args:
            stream: Iterable of items to aggregate
            window_size: Optional size of the window for periodic results
                         If None, results are only returned after all items
                         
        Yields:
            Periodic aggregation results
        """
        count = 0
        
        for item in stream:
            self.add_item(item)
            count += 1
            
            if window_size and count % window_size == 0:
                yield self.get_results()
                self.reset()
        
        # Final results if any items remaining
        if count % (window_size or count) > 0:
            yield self.get_results()
            self.reset()