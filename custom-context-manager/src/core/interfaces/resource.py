"""
Base resource interface for the resource manager.

This module defines the fundamental Resource interface that all
managed resources must implement.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class Resource(ABC):
    """
    Abstract base class for all resources that can be managed by the resource manager.
    
    Resources represent external connections or services such as databases,
    APIs, file handles, etc., that need proper initialization and cleanup.
    """
    
    @abstractmethod
    def acquire(self) -> None:
        """
        Acquire and initialize the resource.
        
        This method is called when the resource needs to be initialized.
        It should establish connections, open files, etc.
        
        Raises:
            Exception: If the resource cannot be acquired
        """
        pass
    
    @abstractmethod
    def release(self) -> None:
        """
        Release and cleanup the resource.
        
        This method is called when the resource is no longer needed.
        It should close connections, release file handles, etc.
        
        Raises:
            Exception: If the resource cannot be released properly
        """
        pass
    
    @property
    @abstractmethod
    def is_acquired(self) -> bool:
        """
        Check if the resource is currently acquired.
        
        Returns:
            bool: True if the resource is acquired, False otherwise
        """
        pass
    
    @property
    def name(self) -> str:
        """
        Get the name of the resource.
        
        Returns:
            str: The name of the resource
        """
        return self.__class__.__name__
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the resource.
        
        Returns:
            Dict[str, Any]: A dictionary containing status information
        """
        return {
            "name": self.name,
            "acquired": self.is_acquired,
        }