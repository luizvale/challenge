"""
Interface for metrics collection in the resource manager.

This module defines the interfaces for collecting performance metrics
about resource usage and operations.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class MetricsCollector(ABC):
    """
    Interface for collecting metrics about resource usage.
    
    Implementations of this interface are responsible for collecting,
    storing, and potentially reporting metrics about resource acquisition,
    usage, and release.
    """
    
    @abstractmethod
    def record_acquisition(self, resource_name: str, elapsed_time: float) -> None:
        """
        Record the acquisition of a resource.
        
        Args:
            resource_name: Name of the resource being acquired
            elapsed_time: Time in seconds taken to acquire the resource
        """
        pass
    
    @abstractmethod
    def record_release(self, resource_name: str, elapsed_time: float) -> None:
        """
        Record the release of a resource.
        
        Args:
            resource_name: Name of the resource being released
            elapsed_time: Time in seconds taken to release the resource
        """
        pass
    
    @abstractmethod
    def record_operation(self, resource_name: str, operation: str, elapsed_time: float) -> None:
        """
        Record an operation performed on a resource.
        
        Args:
            resource_name: Name of the resource
            operation: Name of the operation performed
            elapsed_time: Time in seconds taken to perform the operation
        """
        pass
    
    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get all collected metrics.
        
        Returns:
            Dict[str, Any]: Dictionary containing all collected metrics
        """
        pass
    
    @abstractmethod
    def reset(self) -> None:
        """
        Reset all metrics.
        
        This will clear all collected metrics data.
        """
        pass