"""
Advanced aggregation implementations for complex data analysis needs.
"""
import logging
import math
from typing import Dict, Any, List, Optional, Callable, TypeVar, Set
from collections import defaultdict
from datetime import datetime, timedelta

from ...core.entities.data_item import DataItem
from ...core.interfaces.aggregator import Aggregator
from .window import AggregationResult

logger = logging.getLogger(__name__)

# Generic type for aggregation results
T = TypeVar('T')

class TimeWindowAggregator(Aggregator[AggregationResult[T]]):
    """
    Aggregator that groups data based on time windows.
    
    Creates time-based buckets (e.g., hourly, daily) and
    aggregates data within each bucket.
    """
    
    def __init__(self, 
                window_duration: timedelta,
                aggregation_func: Callable[[List[Dict[str, Any]]], T],
                timestamp_field: str = 'timestamp',
                timestamp_format: Optional[str] = None):
        """
        Initializes the time window aggregator.
        
        Args:
            window_duration: Length of the time window
            aggregation_func: Function that computes the aggregate value
            timestamp_field: Field containing the timestamp
            timestamp_format: Optional format string for parsing timestamps
        """
        self.window_duration = window_duration
        self.aggregation_func = aggregation_func
        self.timestamp_field = timestamp_field
        self.timestamp_format = timestamp_format
        
        # Storage for time windows
        self.windows: Dict[datetime, List[DataItem]] = defaultdict(list)
    
    def _parse_timestamp(self, value: Any) -> Optional[datetime]:
        """
        Parses a timestamp value from an item.
        
        Args:
            value: Timestamp value to parse
            
        Returns:
            Parsed datetime or None if parsing fails
        """
        if isinstance(value, datetime):
            return value
        
        if isinstance(value, (int, float)):
            # Assume Unix timestamp
            return datetime.fromtimestamp(value)
        
        if isinstance(value, str):
            if self.timestamp_format:
                # Parse using specified format
                try:
                    return datetime.strptime(value, self.timestamp_format)
                except ValueError:
                    logger.error(f"Failed to parse timestamp '{value}' with format '{self.timestamp_format}'")
                    return None
            else:
                # Try ISO format
                try:
                    return datetime.fromisoformat(value)
                except ValueError:
                    logger.error(f"Failed to parse ISO timestamp '{value}'")
                    return None
        
        return None
    
    def _get_window_start(self, timestamp: datetime) -> datetime:
        """
        Determines the start of the window containing the timestamp.
        
        Args:
            timestamp: Timestamp to find window for
            
        Returns:
            Start time of the containing window
        """
        # Calculate seconds since epoch
        epoch_seconds = timestamp.timestamp()
        
        # Calculate seconds in the window
        window_seconds = self.window_duration.total_seconds()
        
        # Calculate window start in seconds since epoch
        window_start_seconds = (epoch_seconds // window_seconds) * window_seconds
        
        # Convert back to datetime
        return datetime.fromtimestamp(window_start_seconds)
    
    def add_item(self, item: DataItem) -> None:
        """
        Adds an item to the appropriate time window.
        
        Args:
            item: Item to add
        """
        # Extract timestamp
        try:
            timestamp_value = item.data.get(self.timestamp_field)
            if timestamp_value is None:
                logger.warning(f"Item {item.id} has no '{self.timestamp_field}' field")
                return
            
            timestamp = self._parse_timestamp(timestamp_value)
            if timestamp is None:
                logger.warning(f"Failed to parse timestamp for item {item.id}")
                return
            
            # Get window start
            window_start = self._get_window_start(timestamp)
            
            # Add to appropriate window
            self.windows[window_start].append(item)
            
        except Exception as e:
            logger.error(f"Error processing item for time window: {e}")
    
    def get_results(self) -> List[AggregationResult[T]]:
        """
        Computes aggregation results for each time window.
        
        Returns:
            List of aggregation results, one per window
        """
        results: List[AggregationResult[T]] = []
        
        for window_start, items in sorted(self.windows.items()):
            try:
                if not items:
                    continue
                
                # Extract data from items
                data_list = [item.data for item in items]
                
                # Apply aggregation function
                value = self.aggregation_func(data_list)
                
                # Create result
                window_end = window_start + self.window_duration
                result = AggregationResult(
                    value=value,
                    count=len(items),
                    metadata={
                        'window_start': window_start.isoformat(),
                        'window_end': window_end.isoformat(),
                        'window_duration_seconds': self.window_duration.total_seconds()
                    }
                )
                
                results.append(result)
                
            except Exception as e:
                logger.error(f"Error computing aggregation for window {window_start}: {e}")
        
        return results
    
    def reset(self) -> None:
        """
        Resets the aggregator state.
        """
        self.windows.clear()


class TopNAggregator(Aggregator[AggregationResult[List[Dict[str, Any]]]]):
    """
    Aggregator that computes the top N items by a specified key.
    
    Maintains a sorted list of the highest (or lowest) N items
    according to a specified field or computed value.
    """
    
    def __init__(self, 
                n: int,
                key_func: Callable[[Dict[str, Any]], Any],
                reverse: bool = True,
                allow_ties: bool = True):
        """
        Initializes the top N aggregator.
        
        Args:
            n: Number of top items to keep
            key_func: Function to extract the sort key from an item
            reverse: If True, higher values rank better (descending order)
            allow_ties: If True, may return more than N if there are ties
        """
        self.n = n
        self.key_func = key_func
        self.reverse = reverse  # True for descending (highest first)
        self.allow_ties = allow_ties
        
        # Store all items
        self.items: List[DataItem] = []
    
    def add_item(self, item: DataItem) -> None:
        """
        Adds an item to the collection.
        
        Args:
            item: Item to add
        """
        self.items.append(item)
    
    def get_results(self) -> List[AggregationResult[List[Dict[str, Any]]]]:
        """
        Computes the top N items.
        
        Returns:
            List containing a single aggregation result with the top N items
        """
        try:
            if not self.items:
                return [AggregationResult(value=[], count=0, metadata={})]
            
            # Create a list of (item, key) tuples
            item_keys = []
            for item in self.items:
                try:
                    key = self.key_func(item.data)
                    item_keys.append((item, key))
                except Exception as e:
                    logger.error(f"Error extracting key from item {item.id}: {e}")
                    continue
            
            # Sort by key
            item_keys.sort(key=lambda x: x[1], reverse=self.reverse)
            
            # Select top N items
            if self.allow_ties:
                # Include all items that tie with the Nth item
                if len(item_keys) > self.n:
                    nth_key = item_keys[self.n-1][1]
                    top_n = [item for item, key in item_keys 
                             if self.reverse and key >= nth_key or 
                                not self.reverse and key <= nth_key]
                else:
                    top_n = [item for item, _ in item_keys]
            else:
                # Strictly limit to N items
                top_n = [item for item, _ in item_keys[:self.n]]
            
            # Extract data from items
            data_list = [item.data for item in top_n]
            
            # Create result
            result = AggregationResult(
                value=data_list,
                count=len(data_list),
                metadata={
                    'n': self.n,
                    'actual_count': len(data_list),
                    'reverse': self.reverse,
                    'allow_ties': self.allow_ties
                }
            )
            
            return [result]
            
        except Exception as e:
            logger.error(f"Error computing top N aggregation: {e}")
            return [AggregationResult(value=[], count=0, metadata={'error': str(e)})]
    
    def reset(self) -> None:
        """
        Resets the aggregator state.
        """
        self.items.clear()


class GroupByAggregator(Aggregator[AggregationResult[Dict[Any, T]]]):
    """
    Aggregator that groups items by a key and applies an aggregation function to each group.
    
    Similar to SQL GROUP BY or pandas groupby functionality.
    """
    
    def __init__(self, 
                key_func: Callable[[Dict[str, Any]], Any],
                aggregation_func: Callable[[List[Dict[str, Any]]], T],
                min_group_size: int = 1):
        """
        Initializes the group by aggregator.
        
        Args:
            key_func: Function to extract the group key from an item
            aggregation_func: Function to apply to each group
            min_group_size: Minimum group size to include in results
        """
        self.key_func = key_func
        self.aggregation_func = aggregation_func
        self.min_group_size = min_group_size
        
        # Storage for groups
        self.groups: Dict[Any, List[DataItem]] = defaultdict(list)
    
    def add_item(self, item: DataItem) -> None:
        """
        Adds an item to the appropriate group.
        
        Args:
            item: Item to add
        """
        try:
            key = self.key_func(item.data)
            self.groups[key].append(item)
        except Exception as e:
            logger.error(f"Error adding item to group: {e}")
    
    def get_results(self) -> List[AggregationResult[Dict[Any, T]]]:
        """
        Computes aggregation results for each group.
        
        Returns:
            List containing a single result with all group aggregations
        """
        try:
            # Aggregate each group
            aggregated_groups = {}
            total_count = 0
            
            for key, items in self.groups.items():
                if len(items) < self.min_group_size:
                    continue
                
                # Extract data from items
                data_list = [item.data for item in items]
                total_count += len(data_list)
                
                # Apply aggregation function
                try:
                    aggregated_groups[key] = self.aggregation_func(data_list)
                except Exception as e:
                    logger.error(f"Error aggregating group '{key}': {e}")
            
            # Create result
            result = AggregationResult(
                value=aggregated_groups,
                count=total_count,
                metadata={
                    'group_count': len(aggregated_groups),
                    'min_group_size': self.min_group_size
                }
            )
            
            return [result]
            
        except Exception as e:
            logger.error(f"Error in GroupByAggregator: {e}")
            return [AggregationResult(
                value={},
                count=0,
                metadata={'error': str(e)}
            )]
    
    def reset(self) -> None:
        """
        Resets the aggregator state.
        """
        self.groups.clear()


class StatisticalAggregator(Aggregator[AggregationResult[Dict[str, float]]]):
    """
    Aggregator that computes common statistical metrics for a field.
    
    Calculates mean, median, min, max, variance, standard deviation, etc.
    in an efficient single-pass algorithm where possible.
    """
    
    def __init__(self, 
                field: str,
                metrics: Optional[Set[str]] = None):
        """
        Initializes the statistical aggregator.
        
        Args:
            field: Name of the field to analyze
            metrics: Set of metrics to compute (None for all)
        """
        self.field = field
        self.metrics = metrics or {
            'count', 'min', 'max', 'sum', 'mean', 
            'variance', 'std_dev', 'median'
        }
        
        # Online statistics accumulators
        self._count = 0
        self._sum = 0.0
        self._sum_sq = 0.0
        self._min = float('inf')
        self._max = float('-inf')
        
        # For median calculation
        self._values: List[float] = []
    
    def add_item(self, item: DataItem) -> None:
        """
        Adds an item to the statistical calculation.
        
        Args:
            item: Item to add
        """
        try:
            # Extract field value
            value = item.data.get(self.field)
            
            # Skip if missing or not numeric
            if value is None or not isinstance(value, (int, float)):
                return
            
            # Convert to float for consistency
            value = float(value)
            
            # Update online statistics
            self._count += 1
            self._sum += value
            self._sum_sq += value * value
            self._min = min(self._min, value)
            self._max = max(self._max, value)
            
            # Store value for median calculation if needed
            if 'median' in self.metrics or 'percentile' in self.metrics:
                self._values.append(value)
                
        except Exception as e:
            logger.error(f"Error adding item to StatisticalAggregator: {e}")
    
    def get_results(self) -> List[AggregationResult[Dict[str, float]]]:
        """
        Computes the statistical results.
        
        Returns:
            List containing a single aggregation result with all statistics
        """
        try:
            results: Dict[str, float] = {}
            
            # Only compute if we have data
            if self._count > 0:
                # Simple statistics
                if 'count' in self.metrics:
                    results['count'] = self._count
                
                if 'sum' in self.metrics:
                    results['sum'] = self._sum
                
                if 'min' in self.metrics and self._min != float('inf'):
                    results['min'] = self._min
                
                if 'max' in self.metrics and self._max != float('-inf'):
                    results['max'] = self._max
                
                # Mean
                if 'mean' in self.metrics:
                    results['mean'] = self._sum / self._count
                
                # Variance and standard deviation
                if 'variance' in self.metrics or 'std_dev' in self.metrics:
                    if self._count > 1:
                        variance = (self._sum_sq - (self._sum * self._sum) / self._count) / (self._count - 1)
                        # Protect against numeric issues that might cause slight negative variance
                        variance = max(0, variance)
                        
                        if 'variance' in self.metrics:
                            results['variance'] = variance
                        
                        if 'std_dev' in self.metrics:
                            results['std_dev'] = math.sqrt(variance)
                
                # Median
                if 'median' in self.metrics and self._values:
                    sorted_values = sorted(self._values)
                    n = len(sorted_values)
                    
                    if n % 2 == 0:
                        # Even number, average middle two
                        results['median'] = (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
                    else:
                        # Odd number, take middle
                        results['median'] = sorted_values[n//2]
            
            # Create result
            result = AggregationResult(
                value=results,
                count=self._count,
                metadata={
                    'field': self.field,
                    'metrics': list(self.metrics)
                }
            )
            
            return [result]
            
        except Exception as e:
            logger.error(f"Error computing statistics: {e}")
            return [AggregationResult(
                value={},
                count=0,
                metadata={'error': str(e)}
            )]
    
    def reset(self) -> None:
        """
        Resets the aggregator state.
        """
        self._count = 0
        self._sum = 0.0
        self._sum_sq = 0.0
        self._min = float('inf')
        self._max = float('-inf')
        self._values = []


class DistinctCountAggregator(Aggregator[AggregationResult[Dict[str, int]]]):
    """
    Aggregator that counts distinct values for specified fields.
    
    Useful for cardinality analysis and unique counts.
    """
    
    def __init__(self, fields: List[str]):
        """
        Initializes the distinct count aggregator.
        
        Args:
            fields: List of field names to track distinct values for
        """
        self.fields = fields
        self.value_sets: Dict[str, Set[Any]] = {field: set() for field in fields}
    
    def add_item(self, item: DataItem) -> None:
        """
        Adds an item to the distinct value tracking.
        
        Args:
            item: Item to process
        """
        for field in self.fields:
            if field in item.data:
                value = item.data[field]
                
                # Only hashable values can be added to a set
                # Try to convert non-hashable values to strings
                try:
                    self.value_sets[field].add(value)
                except TypeError:
                    try:
                        # Convert to string
                        self.value_sets[field].add(str(value))
                    except Exception as e:
                        logger.error(f"Error adding value for field '{field}': {e}")
    
    def get_results(self) -> List[AggregationResult[Dict[str, int]]]:
        """
        Computes the distinct count for each field.
        
        Returns:
            List containing a single aggregation result with distinct counts
        """
        try:
            # Count distinct values for each field
            distinct_counts = {field: len(values) for field, values in self.value_sets.items()}
            
            # Create result
            result = AggregationResult(
                value=distinct_counts,
                count=sum(distinct_counts.values()),  # Total distinct values across all fields
                metadata={
                    'fields': self.fields
                }
            )
            
            return [result]
            
        except Exception as e:
            logger.error(f"Error computing distinct counts: {e}")
            return [AggregationResult(
                value={},
                count=0,
                metadata={'error': str(e)}
            )]
    
    def reset(self) -> None:
        """
        Resets the aggregator state.
        """
        self.value_sets = {field: set() for field in self.fields}