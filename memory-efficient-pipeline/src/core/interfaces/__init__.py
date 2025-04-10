"""
Core interfaces package.

Contains interfaces (abstract base classes) that define
the contracts between different layers of the application.
"""

# Import interfaces for easier access
from .transformer import BaseTransformer, TransformerInterface
from .aggregator import Aggregator
from .input_source import InputSource
from .output_sink import BaseOutputSink, OutputSinkInterface