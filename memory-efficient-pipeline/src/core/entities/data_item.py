"""
Central entity representing a data item in the pipeline.
"""
from dataclasses import dataclass, field
from typing import Dict, Any
from datetime import datetime
import json
import uuid

@dataclass
class DataItem:
    """
    Represents an individual data item in the pipeline.
    Immutable to ensure thread safety and prevent accidental modifications.
    """
    data: Dict[str, Any]
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """
        Ensures immutability by creating copies of dictionaries.
        Called automatically after initialization.
        """
        # Create copies of dictionaries to ensure immutability
        self.data = dict(self.data)
        self.metadata = dict(self.metadata)
    
    def with_transformation(self, new_data: Dict[str, Any]) -> 'DataItem':
        """
        Creates a new item with transformed data, preserving history.
        
        Args:
            new_data: New data after transformation
            
        Returns:
            New DataItem with updated data and transformation history
        """
        new_metadata = dict(self.metadata)
        new_metadata.setdefault('transformations', [])
        new_metadata['transformations'].append({
            'timestamp': datetime.now(),
            'previous_state_summary': str(self.data)[:100] + '...' if len(str(self.data)) > 100 else str(self.data)
        })
        
        return DataItem(
            data=new_data,
            id=self.id,
            timestamp=self.timestamp,
            metadata=new_metadata
        )
    
    def to_json(self) -> str:
        """
        Converts the item to serialized JSON.
        
        Returns:
            JSON string representation of the item
        """
        obj = {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'data': self.data,
            'metadata': self.metadata
        }
        return json.dumps(obj)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'DataItem':
        """
        Creates a DataItem from a JSON string.
        
        Args:
            json_str: JSON string to parse
            
        Returns:
            New DataItem instance
            
        Raises:
            json.JSONDecodeError: If the string is not valid JSON
        """
        obj = json.loads(json_str)
        
        # Extract required fields
        data = obj.get('data', {})
        
        # Extract optional fields with defaults
        item_id = obj.get('id', str(uuid.uuid4()))
        
        # Parse timestamp if present
        timestamp_str = obj.get('timestamp')
        timestamp = datetime.fromisoformat(timestamp_str) if timestamp_str else datetime.now()
        
        metadata = obj.get('metadata', {})
        
        return cls(
            data=data,
            id=item_id,
            timestamp=timestamp,
            metadata=metadata
        )