"""
Performance and memory usage monitoring system.
"""
import logging
import time
import os
import psutil
import threading
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class MetricPoint:
    """
    Represents a single metric measurement.
    """
    timestamp: datetime
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class PerformanceMetrics:
    """
    Collects and reports performance metrics for the pipeline.
    
    Tracks memory usage, throughput, and processing times
    to ensure the pipeline maintains constant memory usage.
    """
    
    def __init__(self, 
                sampling_interval: float = 1.0,
                history_size: int = 100,
                alert_threshold: Optional[Dict[str, float]] = None):
        """
        Initializes the metrics collector.
        
        Args:
            sampling_interval: Time between measurements in seconds
            history_size: Number of historical values to keep
            alert_threshold: Optional thresholds for alerts
        """
        self.sampling_interval = sampling_interval
        self.history_size = history_size
        self.alert_threshold = alert_threshold or {
            'memory_percent': 90.0,  # Alert if memory usage exceeds 90%
            'cpu_percent': 80.0,     # Alert if CPU usage exceeds 80%
            'processing_time': 5.0   # Alert if processing time exceeds 5 seconds
        }
        
        # Metrics storage
        self.metrics: Dict[str, List[MetricPoint]] = {
            'memory_usage': [],
            'cpu_usage': [],
            'throughput': [],
            'processing_time': [],
            'queue_size': []
        }
        
        # Alert callbacks
        self.alert_callbacks: List[Callable[[str, float], None]] = []
        
        # Monitoring state
        self.monitoring = False
        self.monitor_thread = None
        self.process = psutil.Process(os.getpid())
    
    def start_monitoring(self) -> bool:
        """
        Starts the background monitoring thread.
        
        Returns:
            True if monitoring started successfully, False otherwise
        """
        if self.monitoring:
            logger.warning("Monitoring already started")
            return False
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self.monitor_thread.start()
        logger.info("Performance monitoring started")
        return True
    
    def stop_monitoring(self) -> None:
        """
        Stops the background monitoring thread.
        """
        if not self.monitoring:
            logger.warning("Monitoring not running")
            return
        
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
            logger.info("Performance monitoring stopped")
    
    def _monitoring_loop(self) -> None:
        """
        Background thread function that collects metrics periodically.
        """
        while self.monitoring:
            try:
                # Collect current metrics
                self._collect_system_metrics()
                
                # Check for alerts
                self._check_alerts()
                
                # Sleep until next collection
                time.sleep(self.sampling_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
    
    def _collect_system_metrics(self) -> None:
        """
        Collects current system metrics.
        """
        timestamp = datetime.now()
        
        # Memory usage (resident set size in MB)
        memory_info = self.process.memory_info()
        memory_mb = memory_info.rss / (1024 * 1024)
        self._add_metric('memory_usage', memory_mb)
        
        # CPU usage (percent)
        cpu_percent = self.process.cpu_percent()
        self._add_metric('cpu_usage', cpu_percent)
    
    def _add_metric(self, 
                  metric_name: str, 
                  value: float, 
                  metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Adds a metric measurement to the history.
        
        Args:
            metric_name: Name of the metric
            value: Measured value
            metadata: Optional additional information
        """
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        
        point = MetricPoint(
            timestamp=datetime.now(),
            value=value,
            metadata=metadata or {}
        )
        
        self.metrics[metric_name].append(point)
        
        # Limit history size
        if len(self.metrics[metric_name]) > self.history_size:
            self.metrics[metric_name].pop(0)
    
    def record_processing_time(self, seconds: float, item_count: int = 1) -> None:
        """
        Records the time taken to process items.
        
        Args:
            seconds: Processing time in seconds
            item_count: Number of items processed
        """
        self._add_metric(
            'processing_time', 
            seconds,
            {'items': item_count}
        )
        
        # Calculate and record throughput (items/second)
        if seconds > 0:
            throughput = item_count / seconds
            self._add_metric('throughput', throughput)
    
    def record_queue_size(self, size: int, queue_name: str = 'default') -> None:
        """
        Records the current size of a processing queue.
        
        Args:
            size: Current queue size
            queue_name: Name of the queue being measured
        """
        self._add_metric(
            'queue_size',
            float(size),
            {'queue': queue_name}
        )
    
    def _check_alerts(self) -> None:
        """
        Checks if any metrics exceed alert thresholds.
        """
        if not self.alert_callbacks:
            return
        
        # Check memory usage
        if self.metrics['memory_usage'] and self.alert_threshold.get('memory_percent'):
            # Get total system memory
            system_memory = psutil.virtual_memory().total / (1024 * 1024)  # MB
            latest_memory = self.metrics['memory_usage'][-1].value
            memory_percent = (latest_memory / system_memory) * 100
            
            if memory_percent > self.alert_threshold['memory_percent']:
                self._trigger_alert('memory_percent', memory_percent)
        
        # Check CPU usage
        if self.metrics['cpu_usage'] and self.alert_threshold.get('cpu_percent'):
            latest_cpu = self.metrics['cpu_usage'][-1].value
            if latest_cpu > self.alert_threshold['cpu_percent']:
                self._trigger_alert('cpu_percent', latest_cpu)
        
        # Check processing time
        if self.metrics['processing_time'] and self.alert_threshold.get('processing_time'):
            latest_time = self.metrics['processing_time'][-1].value
            if latest_time > self.alert_threshold['processing_time']:
                self._trigger_alert('processing_time', latest_time)
    
    def _trigger_alert(self, metric_name: str, value: float) -> None:
        """
        Triggers alert callbacks for a metric.
        
        Args:
            metric_name: Name of the metric exceeding threshold
            value: Current value of the metric
        """
        for callback in self.alert_callbacks:
            try:
                callback(metric_name, value)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
    
    def add_alert_callback(self, callback: Callable[[str, float], None]) -> None:
        """
        Adds a callback to be triggered on alerts.
        
        Args:
            callback: Function to call with (metric_name, value)
        """
        self.alert_callbacks.append(callback)
    
    def get_metric_summary(self, metric_name: str) -> Dict[str, Any]:
        """
        Generates a statistical summary of a metric.
        
        Args:
            metric_name: Name of the metric to summarize
            
        Returns:
            Dictionary with summary statistics
        """
        if metric_name not in self.metrics or not self.metrics[metric_name]:
            return {'error': 'No data available'}
        
        values = [point.value for point in self.metrics[metric_name]]
        
        return {
            'current': values[-1],
            'min': min(values),
            'max': max(values),
            'average': sum(values) / len(values),
            'samples': len(values),
            'last_updated': self.metrics[metric_name][-1].timestamp.isoformat()
        }
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """
        Generates summaries for all metrics.
        
        Returns:
            Dictionary with summaries for all metrics
        """
        return {
            metric_name: self.get_metric_summary(metric_name)
            for metric_name in self.metrics
            if self.metrics[metric_name]
        }