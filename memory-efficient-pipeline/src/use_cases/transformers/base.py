"""
Base implementations for transformers.
"""
import logging
from typing import Optional, Dict, Any, Callable, List, TypeVar
from ...core.entities.data_item import DataItem
from ...core.interfaces.transformer import BaseTransformer

logger = logging.getLogger(__name__)

T = TypeVar('T')

class MapTransformer(BaseTransformer):
    """
    Transforms each item by applying a mapping function.
    Similar to Python's map(), but maintains metadata.
    """
    
    def __init__(self, mapper_func: Callable[[Dict[str, Any]], Dict[str, Any]]):
        """
        Initializes the transformer.
        
        Args:
            mapper_func: Function that takes a dictionary and returns a transformed dictionary
        """
        self.mapper_func = mapper_func
    
    def transform(self, item: DataItem) -> Optional[DataItem]:
        """
        Applies the mapping function to the item.
        
        Args:
            item: Item to be transformed
            
        Returns:
            New item with transformed data or None on error
        """
        try:
            transformed_data = self.mapper_func(item.data)
            return item.with_transformation(transformed_data)
        except Exception as e:
            logger.error(f"Error in MapTransformer: {e}")
            # Log error and return None to discard the item
            return None


class FilterTransformer(BaseTransformer):
    """
    Filters items based on a predicate.
    Similar to Python's filter().
    """
    
    def __init__(self, predicate: Callable[[Dict[str, Any]], bool]):
        """
        Initializes the filter.
        
        Args:
            predicate: Function that returns True for items to keep, False to discard
        """
        self.predicate = predicate
    
    def transform(self, item: DataItem) -> Optional[DataItem]:
        """
        Applies the predicate to decide whether to keep or discard the item.
        
        Args:
            item: Item to evaluate
            
        Returns:
            The original item if it passes the predicate, None otherwise
        """
        try:
            if self.predicate(item.data):
                return item
            return None
        except Exception as e:
            logger.error(f"Error in FilterTransformer: {e}")
            return None


class ChainTransformer(BaseTransformer):
    """
    Combines multiple transformers in sequence.
    """
    
    def __init__(self, transformers: List[BaseTransformer]):
        """
        Initializes with a list of transformers.
        
        Args:
            transformers: List of transformers to apply in sequence
        """
        self.transformers = transformers
    
    def transform(self, item: DataItem) -> Optional[DataItem]:
        """
        Applies each transformer in sequence.
        
        Args:
            item: Initial item
            
        Returns:
            Final transformed item or None if any transformer returns None
        """
        current_item = item
        for transformer in self.transformers:
            if current_item is None:
                return None
            current_item = transformer.transform(current_item)
        return current_item


class KeyTransformer(BaseTransformer):
    """
    Applies a transformation to a specific key in the data.
    """
    
    def __init__(self, 
                key: str, 
                transform_func: Callable[[Any], Any],
                create_if_missing: bool = False):
        """
        Initializes the key transformer.
        
        Args:
            key: The key to transform
            transform_func: Function to apply to the key's value
            create_if_missing: Whether to create the key if it doesn't exist
        """
        self.key = key
        self.transform_func = transform_func
        self.create_if_missing = create_if_missing
    
    def transform(self, item: DataItem) -> Optional[DataItem]:
        """
        Applies the transformation to the specified key.
        
        Args:
            item: Item to transform
            
        Returns:
            Transformed item or same item if key doesn't exist
        """
        try:
            new_data = dict(item.data)
            
            if self.key in new_data or self.create_if_missing:
                value = new_data.get(self.key)
                new_data[self.key] = self.transform_func(value)
                return item.with_transformation(new_data)
            
            # Key doesn't exist and we're not creating it
            return item
            
        except Exception as e:
            logger.error(f"Error in KeyTransformer for key '{self.key}': {e}")
            return item  # Return original item on error to avoid data loss