"""
Core package initialization.

This package contains the core domain entities and interfaces
that define the fundamental contracts of the system.
"""

# Import main entities
from .interfaces.resource import Resource
# Import interfaces
from .interfaces.metrics_collector import MetricsCollector

# Version information
__version__ = '0.1.0'