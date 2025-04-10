"""
Basic metrics collection implementation.

This module provides a simple implementation of the MetricsCollector
interface for tracking resource usage and performance metrics.
"""
import statistics
import threading
import time
from collections import defaultdict
from contextlib import contextmanager
from typing import Any, Dict, List, Optional
from statistics import mean, median

from ..core import MetricsCollector


class BasicMetricsCollector(MetricsCollector):
    """
    Simple implementation of MetricsCollector that stores metrics in memory.

    This class collects basic performance metrics for resources, including
    acquisition time, release time, and operation times.
    """

    def __init__(self):
        """Initialize a new metrics collector with empty metrics."""
        self.reset()

    def record_acquisition(self, resource_name: str, elapsed_time: float) -> None:
        """
        Record the acquisition of a resource.

        Args:
            resource_name: Name of the resource being acquired
            elapsed_time: Time in seconds taken to acquire the resource
        """
        self._acquisition_times[resource_name].append(elapsed_time)
        self._record_timestamp(resource_name, "acquisition")

    def record_release(self, resource_name: str, elapsed_time: float) -> None:
        """
        Record the release of a resource.

        Args:
            resource_name: Name of the resource being released
            elapsed_time: Time in seconds taken to release the resource
        """
        self._release_times[resource_name].append(elapsed_time)
        self._record_timestamp(resource_name, "release")

    def record_operation(self, resource_name: str, operation: str, elapsed_time: float) -> None:
        """
        Record an operation performed on a resource.

        Args:
            resource_name: Name of the resource
            operation: Name of the operation performed
            elapsed_time: Time in seconds taken to perform the operation
        """
        self._operation_times[(resource_name, operation)].append(elapsed_time)
        self._operations_count[(resource_name, operation)] += 1
        self._record_timestamp(resource_name, f"operation:{operation}")

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get all collected metrics.

        Returns:
            Dict[str, Any]: Dictionary containing all collected metrics
        """
        resources = set(list(self._acquisition_times.keys()) +
                        list(self._release_times.keys()))

        operations = {}
        for (resource_name, operation), times in self._operation_times.items():
            if resource_name not in operations:
                operations[resource_name] = {}

            count = self._operations_count.get((resource_name, operation), 0)

            operations[resource_name][operation] = {
                "count": count,
                "total_time": sum(times),
                "average_time": sum(times) / count if count > 0 else 0,
                "min_time": min(times) if times else 0,
                "max_time": max(times) if times else 0,
                "median_time": median(times) if times else 0
            }

        result = {
            "resources": {},
            "total_acquisition_time": sum(sum(times) for times in self._acquisition_times.values()),
            "total_release_time": sum(sum(times) for times in self._release_times.values()),
            "total_operations": sum(self._operations_count.values())
        }

        for resource_name in resources:
            acquisition_times = self._acquisition_times.get(resource_name, [])
            release_times = self._release_times.get(resource_name, [])

            result["resources"][resource_name] = {
                "acquisitions": len(acquisition_times),
                "releases": len(release_times),
                "acquisition_time": {
                    "total": sum(acquisition_times),
                    "average": mean(acquisition_times) if acquisition_times else 0,
                    "min": min(acquisition_times) if acquisition_times else 0,
                    "max": max(acquisition_times) if acquisition_times else 0
                },
                "release_time": {
                    "total": sum(release_times),
                    "average": mean(release_times) if release_times else 0,
                    "min": min(release_times) if release_times else 0,
                    "max": max(release_times) if release_times else 0
                },
                "operations": operations.get(resource_name, {}),
                "timeline": self._timestamps.get(resource_name, [])
            }

        return result

    def reset(self) -> None:
        """
        Reset all metrics.

        This will clear all collected metrics data.
        """
        self._acquisition_times: Dict[str, List[float]] = defaultdict(list)
        self._release_times: Dict[str, List[float]] = defaultdict(list)
        self._operation_times: Dict[tuple, List[float]] = defaultdict(list)
        self._operations_count: Dict[tuple, int] = defaultdict(int)
        self._timestamps: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._start_time = time.time()

    def _record_timestamp(self, resource_name: str, event_type: str) -> None:
        """
        Record a timestamp for an event.

        Args:
            resource_name: Name of the resource
            event_type: Type of event (acquisition, release, operation)
        """
        self._timestamps[resource_name].append({
            "time": time.time() - self._start_time,
            "event": event_type
        })


"""
Advanced Metrics Collector for Resource Management

This module provides an enhanced implementation of the MetricsCollector
that captures comprehensive performance and usage metrics.
"""

"""
Advanced Metrics Collector for Resource Management

This module provides an enhanced implementation of the MetricsCollector
that captures comprehensive performance and usage metrics.
"""
class AdvancedMetricsCollector(MetricsCollector):
    """
    Comprehensive metrics collector for resource management.

    Provides in-depth tracking of resource usage, performance,
    and operational characteristics with thread-safe operations.
    """

    def __init__(self):
        """Initialize an advanced metrics collector with thread-safe data structures."""
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        """
        Reset all collected metrics.

        Ensures thread-safe reset of all metric collections.
        """
        with self._lock:
            # Detailed time tracking for different metric types
            self._resource_metrics = defaultdict(lambda: {
                'acquisitions': [],
                'releases': [],
                'operations': defaultdict(list),
                'operation_counts': defaultdict(int),
                'errors': [],
                'error_details': []
            })

            # Performance bottleneck tracking
            self._bottleneck_metrics = {
                'longest_acquisition': (None, 0),
                'longest_release': (None, 0),
                'most_frequent_operations': {}
            }

            # System-wide metrics
            self._system_metrics = {
                'total_resources_managed': 0,
                'total_operations': 0,
                'total_errors': 0,
                'start_time': time.time(),
                'last_reset_time': time.time()
            }

    def record_acquisition(
            self,
            resource_name: str,
            elapsed_time: float,
            details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record resource acquisition with comprehensive details.

        Args:
            resource_name: Name of the resource being acquired
            elapsed_time: Time taken to acquire the resource
            details: Optional additional details about the acquisition
        """
        with self._lock:
            # Record acquisition time
            self._resource_metrics[resource_name]['acquisitions'].append(elapsed_time)

            # Update bottleneck tracking
            if elapsed_time > self._bottleneck_metrics['longest_acquisition'][1]:
                self._bottleneck_metrics['longest_acquisition'] = (resource_name, elapsed_time)

            # System-wide tracking
            self._system_metrics['total_resources_managed'] += 1

    def record_release(
            self,
            resource_name: str,
            elapsed_time: float,
            details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record resource release with comprehensive details.

        Args:
            resource_name: Name of the resource being released
            elapsed_time: Time taken to release the resource
            details: Optional additional details about the release
        """
        with self._lock:
            # Record release time
            self._resource_metrics[resource_name]['releases'].append(elapsed_time)


            # Update bottleneck tracking
            if elapsed_time > self._bottleneck_metrics['longest_release'][1]:
                self._bottleneck_metrics['longest_release'] = (resource_name, elapsed_time)

    def record_operation(
            self,
            resource_name: str,
            operation: str,
            elapsed_time: float,
            success: bool = True,
            error_details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record an operation performed on a resource with detailed tracking.

        Args:
            resource_name: Name of the resource
            operation: Name of the operation performed
            elapsed_time: Time taken to perform the operation
            success: Whether the operation was successful
            error_details: Details of any error that occurred
        """
        with self._lock:
            # Record operation time
            self._resource_metrics[resource_name]['operations'][operation].append(elapsed_time)

            # Increment operation count
            self._resource_metrics[resource_name]['operation_counts'][operation] += 1

            # Update system-wide operation count
            self._system_metrics['total_operations'] += 1

            # Track errors
            if not success:
                self._resource_metrics[resource_name]['errors'].append(elapsed_time)
                self._resource_metrics[resource_name]['error_details'].append(error_details)
                self._system_metrics['total_errors'] += 1

            # Update most frequent operations tracking
            if operation not in self._bottleneck_metrics['most_frequent_operations']:
                self._bottleneck_metrics['most_frequent_operations'][operation] = 0
            self._bottleneck_metrics['most_frequent_operations'][operation] += 1

    def get_metrics(self) -> Dict[str, Any]:
        """
        Generate a comprehensive metrics report.

        Returns:
            Dict containing detailed performance and usage metrics
        """
        with self._lock:
            # Prepare detailed metrics for each resource
            resource_details = {}
            for resource_name, metrics in self._resource_metrics.items():
                resource_details[resource_name] = {
                    'acquisition_stats': self._calculate_stat_summary(metrics['acquisitions']),
                    'release_stats': self._calculate_stat_summary(metrics['releases']),
                    'operations': {
                        op: {
                            'count': self._resource_metrics[resource_name]['operation_counts'][op],
                            'performance': self._calculate_stat_summary(times)
                        }
                        for op, times in metrics['operations'].items()
                    },
                    'error_stats': {
                        'count': len(metrics['errors']),
                        'performance': self._calculate_stat_summary(metrics['errors']),
                        'error_details': metrics['error_details']
                    }
                }

            # Prepare final metrics report
            report = {
                'system_metrics': {
                    'total_resources_managed': self._system_metrics['total_resources_managed'],
                    'total_operations': self._system_metrics['total_operations'],
                    'total_errors': self._system_metrics['total_errors'],
                    'uptime': time.time() - self._system_metrics['start_time']
                },
                'bottlenecks': {
                    'longest_acquisition': {
                        'resource': self._bottleneck_metrics['longest_acquisition'][0],
                        'time': self._bottleneck_metrics['longest_acquisition'][1]
                    },
                    'longest_release': {
                        'resource': self._bottleneck_metrics['longest_release'][0],
                        'time': self._bottleneck_metrics['longest_release'][1]
                    },
                    'most_frequent_operations': dict(
                        sorted(
                            self._bottleneck_metrics['most_frequent_operations'].items(),
                            key=lambda x: x[1],
                            reverse=True
                        )[:5]  # Top 5 most frequent operations
                    )
                },
                'resource_details': resource_details
            }

            return report

    def _calculate_stat_summary(self, values: List[float]) -> Dict[str, float]:
        """
        Calculate statistical summary for a list of values.

        Args:
            values: List of time values to analyze

        Returns:
            Dictionary with statistical metrics
        """
        if not values:
            return {
                'count': 0,
                'total': 0,
                'average': 0,
                'min': 0,
                'max': 0,
                'median': 0,
                'std_dev': 0
            }

        return {
            'count': len(values),
            'total': sum(values),
            'average': statistics.mean(values),
            'min': min(values),
            'max': max(values),
            'median': statistics.median(values),
            'std_dev': statistics.stdev(values) if len(values) > 1 else 0
        }

    @contextmanager
    def track_operation(
            self,
            resource_name: str,
            operation: str
    ):
        """
        Context manager for tracking an operation's performance.

        Args:
            resource_name: Name of the resource
            operation: Name of the operation

        Yields:
            Context for additional error tracking if needed
        """
        start_time = time.time()
        error_details = None
        success = True

        try:
            yield self
        except Exception as e:
            success = False
            error_details = {
                'type': type(e).__name__,
                'message': str(e)
            }
            raise
        finally:
            elapsed_time = time.time() - start_time
            self.record_operation(
                resource_name,
                operation,
                elapsed_time,
                success,
                error_details
            )