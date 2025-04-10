"""
Window-based aggregators for data processing.
"""
import logging
from typing import Dict, Any, List, Callable, Optional, TypeVar, Generic
from collections import deque
from dataclasses import dataclass, field
from ...core.entities.data_item import DataItem
from ...core.interfaces.aggregator import Aggregator

logger = logging.getLogger(__name__)

# Generic type for aggregation results
T = TypeVar('T')

@dataclass
class AggregationResult(Generic[T]):
    """
    Represents the result of an aggregation operation.
    """
    value: T
    count: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class SlidingWindowAggregator(Aggregator[AggregationResult[T]]):
    """
    Aggregates items using a sliding window approach.
    Maintains a fixed-size window of the most recent items.
    """
    
    def __init__(self, 
                window_size: int, 
                aggregation_func: Callable[[List[Dict[str, Any]]], T],
                key_selector: Optional[Callable[[Dict[str, Any]], Any]] = None):
        """
        Initializes the sliding window aggregator.
        
        Args:
            window_size: Maximum number of items in the window
            aggregation_func: Function that computes the aggregate value
            key_selector: Optional function to group items by key
        """
        self.window_size = window_size
        self.aggregation_func = aggregation_func
        self.key_selector = key_selector
        
        # Use deque for efficient window operations
        self.window: deque[DataItem] = deque(maxlen=window_size)
        
        # For grouped aggregation
        self.groups: Dict[Any, List[DataItem]] = {}
    
    def add_item(self, item: DataItem) -> None:
        """
        Adds an item to the window.
        
        Args:
            item: Item to add to the window
        """
        self.window.append(item)
        
        # Update groups if using key_selector
        if self.key_selector:
            try:
                key = self.key_selector(item.data)
                if key not in self.groups:
                    self.groups[key] = []
                self.groups[key].append(item)
                
                # Limit group size to window_size
                if len(self.groups[key]) > self.window_size:
                    self.groups[key].pop(0)
            except Exception as e:
                logger.error(f"Error selecting key for item: {e}")
    
    def get_results(self) -> List[AggregationResult[T]]:
        """
        Computes aggregation results from the current window.
        
        Returns:
            List of aggregation results
        """
        results: List[AggregationResult[T]] = []
        
        if self.key_selector:
            # Grouped aggregation
            for key, items in self.groups.items():
                try:
                    # Extract data from items
                    data_list = [item.data for item in items]
                    value = self.aggregation_func(data_list)
                    result = AggregationResult(
                        value=value,
                        count=len(items),
                        metadata={'key': key}
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error computing aggregation for key {key}: {e}")
        else:
            # Global aggregation
            try:
                data_list = [item.data for item in self.window]
                if data_list:
                    value = self.aggregation_func(data_list)
                    result = AggregationResult(
                        value=value,
                        count=len(data_list),
                        metadata={}
                    )
                    results.append(result)
            except Exception as e:
                logger.error(f"Error computing aggregation: {e}")
        
        return results
    
    def reset(self) -> None:
        """
        Resets the aggregator state.
        """
        self.window.clear()
        self.groups.clear()


class TumblingWindowAggregator(Aggregator[AggregationResult[T]]):
    """
    Aggregates items using a tumbling window approach.
    Windows don't overlap and items belong to exactly one window.
    Reset is required after reading results.
    """
    
    def __init__(self, 
                aggregation_func: Callable[[List[Dict[str, Any]]], T],
                key_selector: Optional[Callable[[Dict[str, Any]], Any]] = None):
        """
        Initializes the tumbling window aggregator.
        
        Args:
            aggregation_func: Function that computes the aggregate value
            key_selector: Optional function to group items by key
        """
        self.aggregation_func = aggregation_func
        self.key_selector = key_selector
        
        # Store all items until reset
        self.items: List[DataItem] = []
        
        # For grouped aggregation
        self.groups: Dict[Any, List[DataItem]] = {}
    
    def add_item(self, item: DataItem) -> None:
        """
        Adds an item to the current window.
        
        Args:
            item: Item to add
        """
        self.items.append(item)
        
        # Update groups if using key_selector
        if self.key_selector:
            try:
                key = self.key_selector(item.data)
                if key not in self.groups:
                    self.groups[key] = []
                self.groups[key].append(item)
            except Exception as e:
                logger.error(f"Error selecting key for item: {e}")
    
    def get_results(self) -> List[AggregationResult[T]]:
        """
        Computes aggregation results from the current window.
        
        Returns:
            List of aggregation results
        """
        results: List[AggregationResult[T]] = []
        
        if self.key_selector:
            # Grouped aggregation
            for key, items in self.groups.items():
                try:
                    # Extract data from items
                    data_list = [item.data for item in items]
                    value = self.aggregation_func(data_list)
                    result = AggregationResult(
                        value=value,
                        count=len(items),
                        metadata={'key': key}
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error computing aggregation for key {key}: {e}")
        else:
            # Global aggregation
            try:
                data_list = [item.data for item in self.items]
                if data_list:
                    value = self.aggregation_func(data_list)
                    result = AggregationResult(
                        value=value,
                        count=len(data_list),
                        metadata={}
                    )
                    results.append(result)
            except Exception as e:
                logger.error(f"Error computing aggregation: {e}")
        
        return results
    
    def reset(self) -> None:
        """
        Resets the aggregator state.
        """
        self.items.clear()
        self.groups.clear()