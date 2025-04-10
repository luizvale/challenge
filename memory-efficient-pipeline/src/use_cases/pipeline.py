"""
Main use case that coordinates the data pipeline.
"""
import logging
from typing import List, Iterable, Dict, Any, Generator, Optional
from ..core.entities.data_item import DataItem
from ..core.interfaces.transformer import TransformerInterface
from ..core.interfaces.output_sink import OutputSinkInterface

logger = logging.getLogger(__name__)

class DataPipeline:
    """
    Central coordinator of the data pipeline.
    Manages the data flow from input to output.
    """
    
    def __init__(
        self,
        transformers: Optional[List[TransformerInterface]] = None,
        outputs: Optional[List[OutputSinkInterface]] = None,
        buffer_size: int = 100
    ):
        """
        Initializes the pipeline.
        
        Args:
            transformers: List of transformers to apply
            outputs: List of destinations for sending data
            buffer_size: Size of the buffer for batch processing
        """
        self.transformers = transformers or []
        self.outputs = outputs or []
        self.buffer_size = buffer_size
        self.total_processed = 0
        self.total_output = 0
    
    def add_transformer(self, transformer: TransformerInterface) -> None:
        """
        Adds a transformer to the pipeline.
        
        Args:
            transformer: The transformer to add
        """
        self.transformers.append(transformer)
    
    def add_output(self, output: OutputSinkInterface) -> None:
        """
        Adds an output destination to the pipeline.
        
        Args:
            output: The output sink to add
        """
        self.outputs.append(output)
    
    def process_data(self, 
                   data_stream: Iterable[Dict[str, Any]]
                   ) -> Generator[DataItem, None, None]:
        """
        Processes a data stream through the pipeline.
        
        Args:
            data_stream: Stream of data in JSON format
            
        Yields:
            Processed items after all transformations
        """
        # Convert JSON data to entities
        items_stream = self._convert_to_items(data_stream)
        
        # Apply all transformations
        processed_items = self._apply_transformations(items_stream)
        
        # Process in batches for memory efficiency
        for batch in self._batch_items(processed_items, self.buffer_size):
            # Send to all configured destinations
            for output in self.outputs:
                try:
                    sent_count = output.send_batch(batch)
                    self.total_output += sent_count
                    logger.info(f"Sent {sent_count} items to {output.__class__.__name__}")
                except Exception as e:
                    logger.error(f"Error sending to {output.__class__.__name__}: {e}")
            
            # Return processed items (allowing additional chaining)
            for item in batch:
                self.total_processed += 1
                yield item

    def _convert_to_items(self,
                          data_stream: Iterable[Dict[str, Any]]
                          ) -> Generator[DataItem, None, None]:
        """
        Converts raw data to DataItem entities.

        Args:
            data_stream: Stream of raw data dictionaries

        Yields:
            DataItem instances
        """
        for data in data_stream:
            try:
                # Skip None values
                if data is None:
                    continue
                yield DataItem(data=data)
            except Exception as e:
                logger.error(f"Error converting data to DataItem: {e}")
    
    def _apply_transformations(self, 
                             items: Iterable[DataItem]
                             ) -> Generator[DataItem, None, None]:
        """
        Applies all transformations to the item stream.
        
        Args:
            items: Stream of items to transform
            
        Yields:
            Transformed items
        """
        current_stream = items
        for transformer in self.transformers:
            try:
                current_stream = transformer.transform_stream(current_stream)
            except Exception as e:
                logger.error(f"Error in transformer {transformer.__class__.__name__}: {e}")
                # Continue with current stream in case of error
        
        # Return the result after all transformations
        for item in current_stream:
            yield item
    
    def _batch_items(self, 
                   items: Iterable[DataItem], 
                   size: int
                   ) -> Generator[List[DataItem], None, None]:
        """
        Groups items into fixed-size batches.
        
        Args:
            items: Stream of items to batch
            size: Size of each batch
            
        Yields:
            Lists of items in batches
        """
        batch: List[DataItem] = []
        for item in items:
            batch.append(item)
            if len(batch) >= size:
                yield batch
                batch = []
        
        # Last batch (which may be smaller than the specified size)
        if batch:
            yield batch