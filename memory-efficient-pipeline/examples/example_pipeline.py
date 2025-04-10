"""
Example usage of the memory-efficient data pipeline.

This example demonstrates a complete pipeline that:
1. Receives JSON data from a webhook
2. Transforms and filters the data
3. Outputs to both a database and a message queue
4. Maintains constant memory usage regardless of input volume
"""
import logging
import json
import time
from typing import Dict, Any, List
from src.use_cases import DataPipeline
from src.use_cases.transformers import MapTransformer, FilterTransformer, ChainTransformer
from src.use_cases.aggregators import SlidingWindowAggregator
from src.external import WebhookAdapter
from src.external import DatabaseOutputSink, MessageQueueOutputSink
from src.external import PerformanceMetrics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Example transformation functions
def normalize_user_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalizes user data fields.

    Args:
        data: Raw user data

    Returns:
        Normalized user data
    """
    result = dict(data)

    # Normalize name fields
    if 'name' in result:
        result['name'] = result['name'].strip().title()

    if 'email' in result:
        result['email'] = result['email'].lower()

    # Convert string numeric values to actual numbers
    for field in ['age', 'score', 'visits']:
        if field in result and isinstance(result[field], str):
            try:
                result[field] = float(result[field])
                # Convert to int if it's a whole number
                if result[field].is_integer():
                    result[field] = int(result[field])
            except ValueError:
                # Keep as string if conversion fails
                pass

    # Add derived fields
    if 'email' in result:
        # Extract domain from email
        result['email_domain'] = result['email'].split('@')[-1]

    return result

def enrich_user_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enriches user data with additional information.

    Args:
        data: User data

    Returns:
        Enriched user data
    """
    result = dict(data)

    # Add a user category based on score
    if 'score' in result and isinstance(result['score'], (int, float)):
        score = result['score']
        if score >= 90:
            result['category'] = 'premium'
        elif score >= 70:
            result['category'] = 'standard'
        else:
            result['category'] = 'basic'

    # Add a timestamp
    result['processed_at'] = time.time()

    return result

def is_valid_user(data: Dict[str, Any]) -> bool:
    """
    Validates if a user record is valid.

    Args:
        data: User data

    Returns:
        True if the user data is valid, False otherwise
    """
    # Check required fields
    if not all(field in data for field in ['name', 'email']):
        return False

    # Validate email format (basic check)
    if '@' not in data.get('email', ''):
        return False

    # Validate age if present
    if 'age' in data and isinstance(data['age'], (int, float)) and data['age'] < 0:
        return False

    return True

# Example aggregation function
def calculate_average_score(data_list: List[Dict[str, Any]]) -> float:
    """
    Calculates the average score from a list of user data.

    Args:
        data_list: List of user data dictionaries

    Returns:
        Average score
    """
    scores = [
        item.get('score', 0)
        for item in data_list
        if 'score' in item and isinstance(item.get('score'), (int, float))
    ]

    if not scores:
        return 0.0

    return sum(scores) / len(scores)

def domain_key_selector(data: Dict[str, Any]) -> str:
    """
    Extracts email domain for grouping.

    Args:
        data: User data

    Returns:
        Email domain or 'unknown'
    """
    return data.get('email_domain', 'unknown')

# Sample alert handler
def handle_metric_alert(metric_name: str, value: float) -> None:
    """
    Handles metric alerts from the monitoring system.

    Args:
        metric_name: Name of the metric triggering the alert
        value: Current value of the metric
    """
    logger.warning(f"ALERT: {metric_name} exceeded threshold with value {value}")

def main() -> None:
    """
    Main function demonstrating a complete pipeline implementation.
    """
    logger.info("Initializing memory-efficient data pipeline")

    # Initialize monitoring
    metrics = PerformanceMetrics(sampling_interval=2.0)
    metrics.add_alert_callback(handle_metric_alert)
    metrics.start_monitoring()

    # Initialize input adapter
    webhook = WebhookAdapter(
        buffer_size=200,
        validator=lambda data: isinstance(data, dict)
    )

    # Initialize transformers
    normalizer = MapTransformer(normalize_user_data)
    enricher = MapTransformer(enrich_user_data)
    validator = FilterTransformer(is_valid_user)

    # Chain transformers for readability
    transform_chain = ChainTransformer([normalizer, validator, enricher])

    # Initialize aggregator
    score_aggregator = SlidingWindowAggregator(
        window_size=50,
        aggregation_func=calculate_average_score,
        key_selector=domain_key_selector
    )

    # Initialize output sinks
    db_sink = DatabaseOutputSink(
        connection_params={"host": "localhost", "port": 5432, "db": "users"},
        table_name="processed_users"
    )

    queue_sink = MessageQueueOutputSink(
        connection_params={"host": "localhost", "port": 5672},
        queue_name="user_updates"
    )

    # Create and configure the pipeline
    pipeline = DataPipeline(buffer_size=50)
    pipeline.add_transformer(transform_chain)
    pipeline.add_output(db_sink)
    pipeline.add_output(queue_sink)

    # Simulate webhook data (for demonstration)
    sample_data = [
        {"name": "john doe", "email": "john@example.com", "age": "32", "score": "85"},
        {"name": "jane smith", "email": "jane@example.com", "age": "28", "score": "92"},
        {"name": "bob johnson", "email": "bob@othersite.com", "age": "45", "score": "78"},
        {"name": "alice brown", "email": "alice@example.com", "age": "36", "score": "95"},
        {"name": "invalid user", "age": "-5"},  # This should be filtered out
        {"name": "chris green", "email": "chris@othersite.com", "age": "31", "score": "88"}
    ]

    # Process some test data
    logger.info(f"Processing {len(sample_data)} sample records")
    start_time = time.time()

    # Add data to webhook (in a real scenario, this would happen via HTTP)
    for data in sample_data:
        webhook.receive_webhook_data(json.dumps(data))

    # Get the data stream from the webhook
    data_stream = webhook.get_data_stream()

    # Process the data through the pipeline
    processed_items = list(pipeline.process_data(data_stream))

    # Record processing time
    processing_time = time.time() - start_time
    metrics.record_processing_time(processing_time, len(processed_items))

    logger.info(f"Processed {len(processed_items)} items in {processing_time:.3f} seconds")

    # Demonstrate aggregation
    logger.info("Calculating aggregated statistics")

    # Create a new stream from the processed items
    for item in processed_items:
        score_aggregator.add_item(item)

    # Get aggregation results
    results = score_aggregator.get_results()

    for result in results:
        domain = result.metadata.get('key', 'unknown')
        logger.info(f"Domain: {domain}, Average Score: {result.value:.2f}, Users: {result.count}")

    # Print memory usage metrics
    memory_stats = metrics.get_metric_summary('memory_usage')
    logger.info(f"Memory usage: Current: {memory_stats['current']:.2f} MB, "
               f"Max: {memory_stats['max']:.2f} MB")

    # Stop monitoring
    metrics.stop_monitoring()
    logger.info("Pipeline demonstration completed")


if __name__ == "__main__":
    main()