"""
Aggregators package.

Contains implementations of the Aggregator interface
for data summarization and analysis.
"""

# Import from window module
from .window import AggregationResult, SlidingWindowAggregator, TumblingWindowAggregator

# Import from advanced module
from .advanced import (
    TimeWindowAggregator,
    TopNAggregator,
    GroupByAggregator,
    StatisticalAggregator,
    DistinctCountAggregator
)