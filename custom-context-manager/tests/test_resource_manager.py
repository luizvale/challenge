"""
Tests for the ResourceManager class.

This module contains test cases for the ResourceManager implementation.
"""
import unittest
from unittest.mock import MagicMock, patch

from src.core.interfaces.resource import Resource
from src.use_cases.resource_manager import ResourceManager, ResourceRegistry


class MockResource(Resource):
    """Mock resource implementation for testing."""
    
    def __init__(self, name="MockResource"):
        self._name = name
        self._acquired = False
        self.acquire_called = 0
        self.release_called = 0
    
    @property
    def name(self):
        return self._name
    
    def acquire(self):
        self.acquire_called += 1
        self._acquired = True
    
    def release(self):
        self.release_called += 1
        self._acquired = False
    
    @property
    def is_acquired(self):
        return self._acquired


class FailingResource(Resource):
    """Mock resource that fails during acquisition or release."""
    
    def __init__(self, fail_on_acquire=False, fail_on_release=False):
        self._acquired = False
        self.fail_on_acquire = fail_on_acquire
        self.fail_on_release = fail_on_release
    
    def acquire(self):
        if self.fail_on_acquire:
            raise ValueError("Simulated acquisition failure")
        self._acquired = True
    
    def release(self):
        if self.fail_on_release:
            raise ValueError("Simulated release failure")
        self._acquired = False
    
    @property
    def is_acquired(self):
        return self._acquired


class TestResourceRegistry(unittest.TestCase):
    """Tests for the ResourceRegistry class."""
    
    def test_add_and_get_resource(self):
        """Test adding and retrieving resources."""
        registry = ResourceRegistry()
        resource = MockResource()
        
        registry.add("test", resource)
        retrieved = registry.get("test")
        
        self.assertEqual(resource, retrieved)
    
    def test_add_duplicate_resource(self):
        """Test adding a resource with a duplicate name."""
        registry = ResourceRegistry()
        resource1 = MockResource("Resource1")
        resource2 = MockResource("Resource2")
        
        registry.add("test", resource1)
        
        with self.assertRaises(ValueError):
            registry.add("test", resource2)
    
    def test_get_nonexistent_resource(self):
        """Test retrieving a nonexistent resource."""
        registry = ResourceRegistry()
        
        with self.assertRaises(KeyError):
            registry.get("nonexistent")
    
    def test_has_resource(self):
        """Test checking if a resource exists."""
        registry = ResourceRegistry()
        resource = MockResource()
        
        registry.add("test", resource)
        
        self.assertTrue(registry.has("test"))
        self.assertFalse(registry.has("nonexistent"))
    
    def test_mark_acquired_and_released(self):
        """Test marking resources as acquired and released."""
        registry = ResourceRegistry()
        resource = MockResource()
        
        registry.add("test", resource)
        
        self.assertFalse(registry.is_acquired("test"))
        
        registry.mark_acquired("test")
        self.assertTrue(registry.is_acquired("test"))
        
        registry.mark_released("test")
        self.assertFalse(registry.is_acquired("test"))
    
    def test_get_resource_collections(self):
        """Test getting collections of resources."""
        registry = ResourceRegistry()
        resource1 = MockResource("Resource1")
        resource2 = MockResource("Resource2")
        
        registry.add("res1", resource1)
        registry.add("res2", resource2)
        
        registry.mark_acquired("res1")
        
        all_resources = registry.get_all_resources()
        acquired_resources = registry.get_acquired_resources()
        resource_names = registry.get_resource_names()
        
        self.assertEqual(len(all_resources), 2)
        self.assertEqual(len(acquired_resources), 1)
        self.assertEqual(set(resource_names), set(["res1", "res2"]))
        self.assertEqual(acquired_resources["res1"], resource1)


class TestResourceManager(unittest.TestCase):
    """Tests for the ResourceManager class."""
    
    def test_add_resource(self):
        """Test adding a resource to the manager."""
        manager = ResourceManager()
        resource = MockResource()
        
        result = manager.add_resource("test", resource)
        
        self.assertEqual(result, manager)  # Should return self for chaining
        self.assertTrue(manager.registry.has("test"))
    
    def test_context_manager_acquisition(self):
        """Test resource acquisition when entering context."""
        manager = ResourceManager()
        resource1 = MockResource("Resource1")
        resource2 = MockResource("Resource2")
        
        manager.add_resource("res1", resource1)
        manager.add_resource("res2", resource2)
        
        with manager as resources:
            self.assertEqual(resource1.acquire_called, 1)
            self.assertEqual(resource2.acquire_called, 1)
            self.assertTrue(manager.registry.is_acquired("res1"))
            self.assertTrue(manager.registry.is_acquired("res2"))
    
    def test_context_manager_release(self):
        """Test resource release when exiting context."""
        manager = ResourceManager()
        resource1 = MockResource("Resource1")
        resource2 = MockResource("Resource2")
        
        manager.add_resource("res1", resource1)
        manager.add_resource("res2", resource2)
        
        with manager:
            pass  # Just enter and exit the context
        
        self.assertEqual(resource1.release_called, 1)
        self.assertEqual(resource2.release_called, 1)
        self.assertFalse(manager.registry.is_acquired("res1"))
        self.assertFalse(manager.registry.is_acquired("res2"))
    
    def test_resource_proxy_access(self):
        """Test accessing resources through the proxy."""
        manager = ResourceManager()
        resource = MockResource()
        
        manager.add_resource("test", resource)
        
        with manager as resources:
            # Access by attribute
            self.assertEqual(resources.test, resource)
            
            # Access by get method
            self.assertEqual(resources.get("test"), resource)
    
    def test_resource_proxy_nonexistent(self):
        """Test accessing a nonexistent resource through the proxy."""
        manager = ResourceManager()
        
        with manager as resources:
            # Access by attribute
            with self.assertRaises(AttributeError):
                _ = resources.nonexistent
            
            # Access by get method
            with self.assertRaises(KeyError):
                resources.get("nonexistent")
    
    def test_acquisition_failure(self):
        """Test failure during resource acquisition."""
        manager = ResourceManager()
        resource1 = MockResource("Resource1")
        resource2 = FailingResource(fail_on_acquire=True)
        resource3 = MockResource("Resource3")
        
        manager.add_resource("res1", resource1)
        manager.add_resource("res2", resource2)
        manager.add_resource("res3", resource3)
        
        with self.assertRaises(ValueError):
            with manager:
                pass  # Should not reach here
        
        # res1 should be acquired and then released during cleanup
        self.assertEqual(resource1.acquire_called, 1)
        self.assertEqual(resource1.release_called, 1)
        
        # res2 should attempt acquisition and fail
        self.assertFalse(manager.registry.is_acquired("res2"))
        
        # res3 should not be acquired since res2 failed first
        self.assertEqual(resource3.acquire_called, 0)
    
    def test_release_failure(self):
        """Test failure during resource release."""
        manager = ResourceManager()
        resource1 = MockResource("Resource1")
        resource2 = FailingResource(fail_on_release=True)
        
        manager.add_resource("res1", resource1)
        manager.add_resource("res2", resource2)
        
        # Should not raise an exception, but log the error
        with patch('logging.Logger.error') as mock_error:
            with manager:
                pass  # Just enter and exit the context
            
            # Verify error was logged
            mock_error.assert_called()
        
        # Both resources should be marked as released
        self.assertFalse(manager.registry.is_acquired("res1"))
        self.assertFalse(manager.registry.is_acquired("res2"))
    
    def test_exception_propagation(self):
        """Test exception propagation from within the context."""
        manager = ResourceManager()
        resource = MockResource()
        
        manager.add_resource("test", resource)
        
        with self.assertRaises(ValueError):
            with manager:
                raise ValueError("Test exception")
        
        # Resource should be released despite the exception
        self.assertEqual(resource.release_called, 1)
        self.assertFalse(manager.registry.is_acquired("test"))
    
    def test_use_resource_context_manager(self):
        """Test the use_resource context manager."""
        manager = ResourceManager()
        resource = MockResource()
        
        manager.add_resource("test", resource)
        
        with manager.use_resource("test") as res:
            self.assertEqual(res, resource)
            self.assertEqual(resource.acquire_called, 1)
            self.assertTrue(resource.is_acquired)
        
        self.assertEqual(resource.release_called, 1)
        self.assertFalse(resource.is_acquired)
    
    def test_use_resource_with_nonexistent(self):
        """Test use_resource with a nonexistent resource."""
        manager = ResourceManager()
        
        with self.assertRaises(KeyError):
            with manager.use_resource("nonexistent"):
                pass
    
    def test_metrics_collection(self):
        """Test metrics collection during resource operations."""
        metrics_collector = MagicMock()
        manager = ResourceManager(metrics_collector=metrics_collector)
        resource = MockResource()
        
        manager.add_resource("test", resource)
        
        with manager:
            pass
        
        # Verify metrics were recorded
        metrics_collector.record_acquisition.assert_called()
        metrics_collector.record_release.assert_called()
    
    def test_get_status(self):
        """Test getting the resource manager status."""
        manager = ResourceManager()
        resource1 = MockResource("Resource1")
        resource2 = MockResource("Resource2")
        
        manager.add_resource("res1", resource1)
        manager.add_resource("res2", resource2)
        
        # Status before acquisition
        status = manager.get_status()
        self.assertEqual(status["total_resources"], 2)
        self.assertEqual(status["acquired_resources"], 0)
        
        # Mark one resource as acquired
        manager.registry.mark_acquired("res1")
        
        # Status after acquisition
        status = manager.get_status()
        self.assertEqual(status["total_resources"], 2)
        self.assertEqual(status["acquired_resources"], 1)


if __name__ == "__main__":
    unittest.main()