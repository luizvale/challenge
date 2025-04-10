"""
External layer package.

Contains adapters for external systems and frameworks.
"""

from .webhook import WebhookAdapter
from .database import DatabaseOutputSink
from .metrics import PerformanceMetrics
from .queue import MessageQueueOutputSink