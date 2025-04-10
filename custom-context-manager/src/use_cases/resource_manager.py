"""
Resource Manager implementation.

This module contains the main ResourceManager class that implements
the context manager protocol for managing multiple resources.
"""
import logging
import time
from typing import Any, Dict, List, Optional, Set, Union
from types import TracebackType
from contextlib import ExitStack, contextmanager

from ..core import Resource, MetricsCollector
from ..external.logger import ResourceManagerLogger


class ResourceRegistry:
    """
    Registry to keep track of resources and their state.

    This class is responsible for storing resources and providing
    access to them in a controlled manner.
    """

    def __init__(self):
        """Initialize an empty resource registry."""
        self._resources: Dict[str, Resource] = {}
        self._acquired_resources: Set[str] = set()

    def add(self, name: str, resource: Resource) -> None:
        """
        Add a resource to the registry.

        Args:
            name: Unique name for the resource
            resource: The resource object to add

        Raises:
            ValueError: If a resource with the same name already exists
        """
        if name in self._resources:
            raise ValueError(f"Resource with name '{name}' already exists")
        self._resources[name] = resource

    def get(self, name: str) -> Resource:
        """
        Get a resource by name.

        Args:
            name: Name of the resource to get

        Returns:
            Resource: The requested resource

        Raises:
            KeyError: If no resource with the given name exists
        """
        if name not in self._resources:
            raise KeyError(f"No resource with name '{name}' exists")
        return self._resources[name]

    def has(self, name: str) -> bool:
        """
        Check if a resource with the given name exists.

        Args:
            name: Name of the resource to check

        Returns:
            bool: True if the resource exists, False otherwise
        """
        return name in self._resources

    def mark_acquired(self, name: str) -> None:
        """
        Mark a resource as acquired.

        Args:
            name: Name of the resource to mark

        Raises:
            KeyError: If no resource with the given name exists
        """
        if name not in self._resources:
            raise KeyError(f"No resource with name '{name}' exists")
        self._acquired_resources.add(name)

    def mark_released(self, name: str) -> None:
        """
        Mark a resource as released.

        Args:
            name: Name of the resource to mark

        Raises:
            KeyError: If no resource with the given name exists
        """
        if name not in self._resources:
            raise KeyError(f"No resource with name '{name}' exists")
        if name in self._acquired_resources:
            self._acquired_resources.remove(name)

    def is_acquired(self, name: str) -> bool:
        """
        Check if a resource is currently acquired.

        Args:
            name: Name of the resource to check

        Returns:
            bool: True if the resource is acquired, False otherwise

        Raises:
            KeyError: If no resource with the given name exists
        """
        if name not in self._resources:
            raise KeyError(f"No resource with name '{name}' exists")
        return name in self._acquired_resources

    def get_all_resources(self) -> Dict[str, Resource]:
        """
        Get all registered resources.

        Returns:
            Dict[str, Resource]: Dictionary of all registered resources
        """
        return self._resources.copy()

    def get_acquired_resources(self) -> Dict[str, Resource]:
        """
        Get all currently acquired resources.

        Returns:
            Dict[str, Resource]: Dictionary of all acquired resources
        """
        return {name: self._resources[name] for name in self._acquired_resources}

    def get_resource_names(self) -> List[str]:
        """
        Get names of all registered resources.

        Returns:
            List[str]: List of resource names
        """
        return list(self._resources.keys())


class ResourceManager:
    """
    Context manager for managing multiple resources.

    This class implements the context manager protocol to ensure proper
    acquisition and release of resources, with error handling and metrics.
    """

    def __init__(self, metrics_collector: Optional[MetricsCollector] = None,
                 logger: Optional[Union[logging.Logger, ResourceManagerLogger]] = None):
        """
        Initialize a new resource manager.

        Args:
            metrics_collector: Optional metrics collector for performance monitoring
            logger: Optional logger for detailed logging (standard Logger or ResourceManagerLogger)
        """
        self.registry = ResourceRegistry()
        self.metrics_collector = metrics_collector
        self.logger = logger or logging.getLogger(__name__)
        self._acquisition_order: List[str] = []

    def add_resource(self, name: str, resource: Resource) -> 'ResourceManager':
        """
        Add a resource to be managed.

        Args:
            name: Unique name for the resource
            resource: The resource to manage

        Returns:
            ResourceManager: Self for chaining

        Raises:
            ValueError: If a resource with the same name already exists
        """
        self.registry.add(name, resource)
        self._acquisition_order.append(name)
        self.logger.debug(f"Added resource '{name}' of type {resource.__class__.__name__}")
        return self

    def __enter__(self) -> 'ResourceProxy':
        """
        Enter the context manager, acquiring all resources.

        Returns:
            ResourceProxy: Proxy object providing access to all acquired resources

        Raises:
            Exception: If any resource fails to be acquired
        """
        self.logger.info("Entering resource manager context, acquiring resources")

        # Use ExitStack to handle nested context managers and proper cleanup
        self._exit_stack = ExitStack()
        self._exit_stack.__enter__()

        # Acquire resources in the order they were added
        for name in self._acquisition_order:
            resource = self.registry.get(name)

            try:
                self.logger.debug(f"Acquiring resource '{name}'")
                start_time = time.time()

                resource.acquire()

                elapsed = time.time() - start_time
                self.registry.mark_acquired(name)

                if self.metrics_collector:
                    self.metrics_collector.record_acquisition(name, elapsed)

                self.logger.debug(f"Resource '{name}' acquired in {elapsed:.6f} seconds")

                # Register resource release with exit stack
                self._exit_stack.callback(self._release_resource, name)

            except Exception as e:
                self.logger.error(f"Failed to acquire resource '{name}': {e}")
                # Let the exit stack handle cleanup of already acquired resources
                self._exit_stack.__exit__(type(e), e, e.__traceback__)
                raise

        return ResourceProxy(self)

    def __exit__(
            self,
            exc_type: Optional[type],
            exc_val: Optional[Exception],
            exc_tb: Optional[TracebackType]
    ) -> bool:
        """
        Exit the context manager, releasing all resources.

        Args:
            exc_type: Type of the exception that occurred, if any
            exc_val: Exception instance that occurred, if any
            exc_tb: Traceback of the exception that occurred, if any

        Returns:
            bool: True if the exception was handled, False otherwise
        """
        self.logger.info("Exiting resource manager context")

        if exc_type:
            self.logger.warning(
                f"Exception occurred: {exc_type.__name__}: {exc_val}"
            )

        # Let the exit stack handle resource release in reverse order
        self._exit_stack.__exit__(exc_type, exc_val, exc_tb)

        return False  # Let the exception propagate

    def _release_resource(self, name: str) -> None:
        """
        Release a specific resource.

        Args:
            name: Name of the resource to release
        """
        # More robust checking to prevent releasing non-existent resources
        if not self.registry.has(name):
            self.logger.debug(f"No resource with name '{name}' exists, skipping release")
            return

        if not self.registry.is_acquired(name):
            self.logger.debug(f"Resource '{name}' is not acquired, skipping release")
            return

        resource = self.registry.get(name)

        # Additional check to prevent releasing already released resources
        # This is a belt-and-suspenders approach to ensure we don't attempt to release twice
        if not resource.is_acquired:
            self.logger.debug(f"Resource '{name}' reports it's already released, updating registry")
            self.registry.mark_released(name)
            return

        try:
            self.logger.debug(f"Releasing resource '{name}'")
            start_time = time.time()

            resource.release()

            elapsed = time.time() - start_time
            self.registry.mark_released(name)

            if self.metrics_collector:
                self.metrics_collector.record_release(name, elapsed)

            self.logger.debug(f"Resource '{name}' released in {elapsed:.6f} seconds")

        except Exception as e:
            self.logger.error(f"Error releasing resource '{name}': {e}")
            # Important: ensure the resource is marked as released in our registry
            # even if the release operation itself failed
            self.registry.mark_released(name)

    def get_resource(self, name: str) -> Resource:
        """
        Get a resource by name.

        Args:
            name: Name of the resource to get

        Returns:
            Resource: The requested resource

        Raises:
            KeyError: If no resource with the given name exists
        """
        return self.registry.get(name)

    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the resource manager.

        Returns:
            Dict[str, Any]: Dictionary with status information
        """
        resources = self.registry.get_all_resources()
        acquired = self.registry.get_acquired_resources()

        return {
            "total_resources": len(resources),
            "acquired_resources": len(acquired),
            "resources": {
                name: resource.get_status()
                for name, resource in resources.items()
            }
        }

    @contextmanager
    def use_resource(self, name: str):
        """
        Context manager for using a single resource.

        Args:
            name: Name of the resource to use

        Yields:
            Resource: The acquired resource

        Raises:
            KeyError: If no resource with the given name exists
            Exception: If the resource fails to be acquired
        """
        resource = self.registry.get(name)

        try:
            self.logger.debug(f"Acquiring resource '{name}'")
            start_time = time.time()

            resource.acquire()

            elapsed = time.time() - start_time
            self.registry.mark_acquired(name)

            if self.metrics_collector:
                self.metrics_collector.record_acquisition(name, elapsed)

            self.logger.debug(f"Resource '{name}' acquired in {elapsed:.6f} seconds")

            yield resource

        except Exception as e:
            self.logger.error(f"Failed to acquire or use resource '{name}': {e}")
            raise

        finally:
            if self.registry.is_acquired(name):
                try:
                    self.logger.debug(f"Releasing resource '{name}'")
                    start_time = time.time()

                    resource.release()

                    elapsed = time.time() - start_time
                    self.registry.mark_released(name)

                    if self.metrics_collector:
                        self.metrics_collector.record_release(name, elapsed)

                    self.logger.debug(f"Resource '{name}' released in {elapsed:.6f} seconds")

                except Exception as e:
                    self.logger.error(f"Error releasing resource '{name}': {e}")


class ResourceProxy:
    """
    Proxy for accessing managed resources.

    This class provides a convenient interface for accessing resources
    managed by a ResourceManager.
    """

    def __init__(self, manager: ResourceManager):
        """
        Initialize the resource proxy.

        Args:
            manager: The resource manager this proxy provides access to
        """
        self._manager = manager

    def __getattr__(self, name: str) -> Resource:
        """
        Get a resource by attribute access.

        This allows resources to be accessed using dot notation:
        `resources.database` instead of `resources.get('database')`.

        Args:
            name: Name of the resource to get

        Returns:
            Resource: The requested resource

        Raises:
            AttributeError: If no resource with the given name exists
        """
        try:
            return self._manager.get_resource(name)
        except KeyError:
            raise AttributeError(f"No resource named '{name}'")

    def get(self, name: str) -> Resource:
        """
        Get a resource by name.

        Args:
            name: Name of the resource to get

        Returns:
            Resource: The requested resource

        Raises:
            KeyError: If no resource with the given name exists
        """
        return self._manager.get_resource(name)

    def status(self) -> Dict[str, Any]:
        """
        Get the current status of all resources.

        Returns:
            Dict[str, Any]: Dictionary with status information for all resources
        """
        return self._manager.get_status()