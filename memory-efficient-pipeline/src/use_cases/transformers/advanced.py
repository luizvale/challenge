"""
Advanced transformer implementations for complex data processing needs.
"""
import logging
import re
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable, Pattern, Union, Set

from ...core.entities.data_item import DataItem
from ...core.interfaces.transformer import BaseTransformer

logger = logging.getLogger(__name__)


class JsonPathTransformer(BaseTransformer):
    """
    Transformer that can modify nested JSON structures using paths.
    
    Allows accessing and updating deeply nested JSON structures
    using dot notation (e.g., "user.contact.email").
    """
    
    def __init__(self, 
                updates: Dict[str, Union[Any, Callable[[Any], Any]]]):
        """
        Initializes the JSON path transformer.
        
        Args:
            updates: Dictionary mapping paths to values or transform functions
        """
        self.updates = updates
    
    def transform(self, item: DataItem) -> Optional[DataItem]:
        """
        Applies path-based updates to the item.
        
        Args:
            item: Item to transform
            
        Returns:
            Transformed item
        """
        try:
            # Create a copy of the data
            new_data = dict(item.data)
            
            # Apply each path update
            for path, value_or_func in self.updates.items():
                self._apply_update(new_data, path, value_or_func)
            
            return item.with_transformation(new_data)
        except Exception as e:
            logger.error(f"Error in JsonPathTransformer: {e}")
            return item  # Return original item on error
    
    def _apply_update(self, 
                     data: Dict[str, Any], 
                     path: str, 
                     value_or_func: Union[Any, Callable[[Any], Any]]) -> None:
        """
        Applies an update to a specific path in the data.
        
        Args:
            data: Data dictionary to update
            path: Dot-notation path to update
            value_or_func: Value or function to apply
        """
        # Split the path into parts
        parts = path.split('.')
        
        # Navigate to the second-to-last part
        current = data
        for part in parts[:-1]:
            # Create nested dictionaries if they don't exist
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]
        
        # Get the last part (the key to update)
        last_part = parts[-1]
        
        # Apply the update
        if callable(value_or_func):
            # If it's a function, call it with the current value
            current_value = current.get(last_part)
            try:
                current[last_part] = value_or_func(current_value)
            except Exception as e:
                logger.error(f"Error applying function to {path}: {e}")
        else:
            # Otherwise just set the value
            current[last_part] = value_or_func


class RegexTransformer(BaseTransformer):
    """
    Transformer that applies regular expression transformations.
    
    Can be used for pattern matching, extraction, and replacement
    operations on string fields.
    """
    
    def __init__(self, 
                field_name: str,
                pattern: str,
                replacement: str,
                create_if_missing: bool = False):
        """
        Initializes the regex transformer.
        
        Args:
            field_name: Name of the field to transform
            pattern: Regular expression pattern to match
            replacement: Replacement string (can include group refs like \\1)
            create_if_missing: Whether to create the field if missing
        """
        self.field_name = field_name
        self.pattern = re.compile(pattern)
        self.replacement = replacement
        self.create_if_missing = create_if_missing
    
    def transform(self, item: DataItem) -> Optional[DataItem]:
        """
        Applies regex transformation to the specified field.
        
        Args:
            item: Item to transform
            
        Returns:
            Transformed item
        """
        try:
            # Create a copy of the data
            new_data = dict(item.data)
            
            # Check if the field exists
            if self.field_name in new_data or self.create_if_missing:
                value = new_data.get(self.field_name, '')
                
                # Only process string values
                if isinstance(value, str):
                    # Apply the regular expression
                    new_value = self.pattern.sub(self.replacement, value)
                    new_data[self.field_name] = new_value
            
            return item.with_transformation(new_data)
        except Exception as e:
            logger.error(f"Error in RegexTransformer: {e}")
            return item  # Return original item on error


class SchemaValidationTransformer(BaseTransformer):
    """
    Transformer that validates data against a schema.
    
    Ensures data conforms to expected structure and types.
    Items that don't pass validation can be filtered out.
    """
    
    def __init__(self, 
                schema: Dict[str, Dict[str, Any]],
                drop_invalid: bool = True,
                add_validation_info: bool = True):
        """
        Initializes the schema validation transformer.
        
        Args:
            schema: Dictionary defining expected fields and their properties
            drop_invalid: If True, return None for invalid items
            add_validation_info: If True, add validation info to metadata
        """
        self.schema = schema
        self.drop_invalid = drop_invalid
        self.add_validation_info = add_validation_info
    
    def transform(self, item: DataItem) -> Optional[DataItem]:
        """
        Validates the item against the schema.
        
        Args:
            item: Item to validate
            
        Returns:
            Validated item, potentially with validation info added,
            or None if invalid and drop_invalid is True
        """
        try:
            # Perform validation
            validation_errors: List[str] = []
            
            # Check required fields and types
            for field_name, field_spec in self.schema.items():
                # Check if required
                if field_spec.get('required', False) and field_name not in item.data:
                    validation_errors.append(f"Required field '{field_name}' is missing")
                    continue
                
                # If field exists, check type
                if field_name in item.data:
                    value = item.data[field_name]
                    
                    # Get expected type
                    expected_type = field_spec.get('type')
                    if expected_type:
                        # Check type
                        type_valid = False
                        
                        # Handle various type specifications
                        if expected_type == 'string' and isinstance(value, str):
                            type_valid = True
                        elif expected_type == 'number' and isinstance(value, (int, float)):
                            type_valid = True
                        elif expected_type == 'integer' and isinstance(value, int):
                            type_valid = True
                        elif expected_type == 'boolean' and isinstance(value, bool):
                            type_valid = True
                        elif expected_type == 'object' and isinstance(value, dict):
                            type_valid = True
                        elif expected_type == 'array' and isinstance(value, list):
                            type_valid = True
                        
                        if not type_valid:
                            validation_errors.append(
                                f"Field '{field_name}' has incorrect type, expected {expected_type}"
                            )
                    
                    # Check pattern if applicable
                    pattern = field_spec.get('pattern')
                    if pattern and isinstance(value, str):
                        if not re.match(pattern, value):
                            validation_errors.append(
                                f"Field '{field_name}' does not match pattern {pattern}"
                            )
                    
                    # Check min/max if applicable for numbers
                    if isinstance(value, (int, float)):
                        if 'minimum' in field_spec and value < field_spec['minimum']:
                            validation_errors.append(
                                f"Field '{field_name}' is less than minimum {field_spec['minimum']}"
                            )
                        if 'maximum' in field_spec and value > field_spec['maximum']:
                            validation_errors.append(
                                f"Field '{field_name}' is greater than maximum {field_spec['maximum']}"
                            )
                    
                    # Check min/max length for strings
                    if isinstance(value, str):
                        if 'minLength' in field_spec and len(value) < field_spec['minLength']:
                            validation_errors.append(
                                f"Field '{field_name}' is shorter than minLength {field_spec['minLength']}"
                            )
                        if 'maxLength' in field_spec and len(value) > field_spec['maxLength']:
                            validation_errors.append(
                                f"Field '{field_name}' is longer than maxLength {field_spec['maxLength']}"
                            )
                    
                    # Check enum values
                    if 'enum' in field_spec and value not in field_spec['enum']:
                        validation_errors.append(
                            f"Field '{field_name}' value is not in allowed enum values"
                        )
            
            # Process validation results
            if validation_errors:
                if self.drop_invalid:
                    logger.warning(f"Validation failed: {', '.join(validation_errors)}")
                    return None
                
                if self.add_validation_info:
                    # Add validation info to metadata
                    new_metadata = dict(item.metadata)
                    new_metadata['validation'] = {
                        'valid': False,
                        'errors': validation_errors,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Create a new item with updated metadata
                    return DataItem(
                        data=item.data,
                        id=item.id,
                        timestamp=item.timestamp,
                        metadata=new_metadata
                    )
            
            # If valid and add_validation_info is True, add validation success info
            if self.add_validation_info:
                new_metadata = dict(item.metadata)
                new_metadata['validation'] = {
                    'valid': True,
                    'timestamp': datetime.now().isoformat()
                }
                
                return DataItem(
                    data=item.data,
                    id=item.id,
                    timestamp=item.timestamp,
                    metadata=new_metadata
                )
            
            # If everything passed and we don't need to add validation info
            return item
            
        except Exception as e:
            logger.error(f"Error in SchemaValidationTransformer: {e}")
            if self.drop_invalid:
                return None
            return item


class DataEnrichmentTransformer(BaseTransformer):
    """
    Transformer that enriches data with additional information.
    
    Can add calculated fields, lookups, or generate derivative data.
    """
    
    def __init__(self, 
                enrichment_functions: Dict[str, Callable[[Dict[str, Any]], Any]],
                skip_errors: bool = True):
        """
        Initializes the data enrichment transformer.
        
        Args:
            enrichment_functions: Dictionary mapping field names to functions
                                 that calculate their values
            skip_errors: If True, continue even if some enrichment functions fail
        """
        self.enrichment_functions = enrichment_functions
        self.skip_errors = skip_errors
    
    def transform(self, item: DataItem) -> Optional[DataItem]:
        """
        Enriches the item with additional data.
        
        Args:
            item: Item to enrich
            
        Returns:
            Enriched item
        """
        try:
            # Create a copy of the data
            new_data = dict(item.data)
            
            # Apply each enrichment function
            for field_name, func in self.enrichment_functions.items():
                try:
                    new_data[field_name] = func(new_data)
                except Exception as e:
                    logger.error(f"Error enriching field '{field_name}': {e}")
                    if not self.skip_errors:
                        raise
            
            return item.with_transformation(new_data)
        except Exception as e:
            logger.error(f"Error in DataEnrichmentTransformer: {e}")
            return item  # Return original item on error


class FieldRemovalTransformer(BaseTransformer):
    """
    Transformer that removes specified fields from data.
    
    Useful for cleaning data before sending to output destinations
    or removing sensitive information.
    """
    
    def __init__(self, fields_to_remove: Set[str]):
        """
        Initializes the field removal transformer.
        
        Args:
            fields_to_remove: Set of field names to remove
        """
        self.fields_to_remove = fields_to_remove
    
    def transform(self, item: DataItem) -> Optional[DataItem]:
        """
        Removes specified fields from the item.
        
        Args:
            item: Item to process
            
        Returns:
            Item with fields removed
        """
        try:
            # Create a copy of the data without the specified fields
            new_data = {
                k: v for k, v in item.data.items() 
                if k not in self.fields_to_remove
            }
            
            return item.with_transformation(new_data)
        except Exception as e:
            logger.error(f"Error in FieldRemovalTransformer: {e}")
            return item  # Return original item on error