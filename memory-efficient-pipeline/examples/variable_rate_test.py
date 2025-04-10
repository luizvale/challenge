"""
Variable-rate influx test for the data pipeline.

This example demonstrates how the pipeline handles variable-rate data influx,
including bursts of data and applying backpressure when needed.
"""
import time
import random
import threading
import json
import matplotlib.pyplot as plt
from queue import Queue
from src.use_cases import DataPipeline
from src.use_cases.transformers import MapTransformer
from src.external import WebhookAdapter
from src.external import DatabaseOutputSink

# Configure a smaller buffer to demonstrate backpressure
WEBHOOK_BUFFER_SIZE = 50
# Number of data items to generate
TOTAL_ITEMS = 1000

def variable_rate_test():
    """
    Tests the pipeline's ability to handle variable-rate data influx.
    """
    print("Starting variable-rate influx test...")
    print("=" * 50)

    # Create a webhook adapter with small buffer
    webhook = WebhookAdapter(buffer_size=WEBHOOK_BUFFER_SIZE)

    # Create a pipeline
    pipeline = DataPipeline(buffer_size=20)

    # Add a simple transformer
    def simple_transform(data):
        time.sleep(0.001)  # Small delay to simulate processing
        result = dict(data)
        result['processed'] = True
        return result

    pipeline.add_transformer(MapTransformer(simple_transform))

    # Add mock database output
    db_sink = DatabaseOutputSink(
        connection_params={"host": "localhost", "port": 5432},
        table_name="test_data"
    )
    pipeline.add_output(db_sink)

    # Create queues for tracking accepted and rejected items
    accepted_queue = Queue()
    rejected_queue = Queue()

    # Metrics for visualization
    metrics_lock = threading.Lock()
    inflow_metrics = []  # (timestamp, count) tuples for input rate
    buffer_metrics = []  # (timestamp, buffer_size) tuples for buffer usage
    backpressure_metrics = []  # (timestamp, rejected_count) tuples for rejections
    processed_metrics = []  # (timestamp, processed_count) tuples for processing rate

    # Variable to track buffer size
    current_buffer_size = 0

    # Producer thread - simulates variable rate data influx
    def producer():
        nonlocal current_buffer_size
        items_sent = 0
        items_in_period = 0
        period_start = time.time()

        for i in range(TOTAL_ITEMS):
            now = time.time()

            # Record inflow rate every second
            if now - period_start >= 1.0:
                with metrics_lock:
                    inflow_metrics.append((now, items_in_period))
                items_in_period = 0
                period_start = now

            data = {
                "id": i,
                "value": f"test-{i}",
                "timestamp": now
            }

            # Simulate variable rates by introducing bursts
            if i % 100 == 0:
                print(f"[Producer] Starting burst at item {i}")
                # Burst of data (many items quickly)
                burst_size = 30
                burst_start = now
                burst_accepted = 0
                burst_rejected = 0

                for j in range(burst_size):
                    if i + j < TOTAL_ITEMS:
                        burst_data = {
                            "id": i + j,
                            "value": f"burst-{i + j}",
                            "timestamp": time.time()
                        }

                        success = webhook.receive_webhook_data(json.dumps(burst_data))
                        if success:
                            accepted_queue.put(i + j)
                            burst_accepted += 1
                            items_sent += 1
                            items_in_period += 1

                            with metrics_lock:
                                current_buffer_size += 1
                                buffer_metrics.append((time.time(), current_buffer_size))
                        else:
                            rejected_queue.put(i + j)
                            burst_rejected += 1

                            with metrics_lock:
                                backpressure_metrics.append((time.time(), 1))  # 1 rejection

                        # No delay during burst to test backpressure

                print(f"[Producer] Burst completed: {burst_accepted} accepted, {burst_rejected} rejected")
                i += burst_size - 1  # Adjust counter (minus 1 since loop increments)
            else:
                # Normal rate (random delay between items)
                success = webhook.receive_webhook_data(json.dumps(data))
                if success:
                    accepted_queue.put(i)
                    items_sent += 1
                    items_in_period += 1

                    with metrics_lock:
                        current_buffer_size += 1
                        buffer_metrics.append((time.time(), current_buffer_size))
                else:
                    rejected_queue.put(i)

                    with metrics_lock:
                        backpressure_metrics.append((time.time(), 1))  # 1 rejection

                # Random delay between items
                time.sleep(random.uniform(0.001, 0.01))

        print(f"[Producer] Completed sending {items_sent} items")

    # Consumer thread - processes data through pipeline
    def consumer():
        nonlocal current_buffer_size
        processed_count = 0
        items_in_period = 0
        period_start = time.time()
        start_time = time.time()

        # Process available data in batches
        while processed_count < TOTAL_ITEMS and time.time() - start_time < 60:  # 60 sec timeout
            now = time.time()

            # Record processing rate every second
            if now - period_start >= 1.0:
                with metrics_lock:
                    processed_metrics.append((now, items_in_period))
                items_in_period = 0
                period_start = now

            # Get current data stream
            data_stream = webhook.get_data_stream()
            items_processed_batch = 0

            for _ in pipeline.process_data(data_stream):
                processed_count += 1
                items_in_period += 1
                items_processed_batch += 1

                if processed_count % 100 == 0:
                    print(f"[Consumer] Processed {processed_count} items")

            # Update buffer size based on items processed
            with metrics_lock:
                current_buffer_size -= items_processed_batch
                if current_buffer_size < 0:
                    current_buffer_size = 0
                if items_processed_batch > 0:
                    buffer_metrics.append((time.time(), current_buffer_size))

            # If no data available, small wait before trying again
            if processed_count < TOTAL_ITEMS:
                time.sleep(0.01)

        elapsed = time.time() - start_time
        print(f"[Consumer] Completed processing {processed_count} items in {elapsed:.2f} seconds")

    # Start producer and consumer threads
    producer_thread = threading.Thread(target=producer)
    consumer_thread = threading.Thread(target=consumer)

    print("Starting producer and consumer threads...")
    producer_thread.start()
    consumer_thread.start()

    # Wait for both threads to complete
    producer_thread.join()
    consumer_thread.join()

    # Analyze results
    accepted_count = accepted_queue.qsize()
    rejected_count = rejected_queue.qsize()

    print("\nRESULTS:")
    print(f"Total items sent: {TOTAL_ITEMS}")
    print(f"Accepted items: {accepted_count}")
    print(f"Rejected items (backpressure): {rejected_count}")

    # Calculate acceptance rate during bursts vs. normal
    print("\nCONCLUSION:")
    if rejected_count > 0:
        print("✅ Backpressure mechanism worked correctly!")
        print(f"   {rejected_count} items were rejected when buffer was full.")
        print("   This demonstrates the pipeline's ability to handle variable-rate data influx.")
    else:
        print("⚠️ No backpressure was observed.")
        print("   Either the buffer was large enough to handle all bursts,")
        print("   or the producer rate wasn't high enough to fill the buffer.")

    # Return metrics for plotting
    return {
        'inflow': inflow_metrics,
        'buffer': buffer_metrics,
        'backpressure': backpressure_metrics,
        'processed': processed_metrics,
        'accepted': accepted_count,
        'rejected': rejected_count
    }

def plot_metrics(metrics):
    """
    Creates visualizations of the variable-rate test results.

    Args:
        metrics: Dictionary of metrics collected during the test
    """
    try:
        plt.figure(figsize=(15, 10))

        # Normalize timestamps to start at 0
        if metrics['inflow'] and metrics['buffer'] and metrics['processed']:
            start_time = min(
                metrics['inflow'][0][0] if metrics['inflow'] else float('inf'),
                metrics['buffer'][0][0] if metrics['buffer'] else float('inf'),
                metrics['processed'][0][0] if metrics['processed'] else float('inf')
            )
        else:
            start_time = time.time()

        # Aggregate backpressure events by second
        backpressure_by_second = {}
        for timestamp, count in metrics['backpressure']:
            second = int(timestamp - start_time)
            backpressure_by_second[second] = backpressure_by_second.get(second, 0) + count

        # Plot 1: Buffer Size Over Time
        plt.subplot(2, 2, 1)
        if metrics['buffer']:
            x_vals = [(t - start_time) for t, _ in metrics['buffer']]
            y_vals = [s for _, s in metrics['buffer']]
            plt.plot(x_vals, y_vals, 'b-', label='Buffer Size')
            plt.axhline(y=WEBHOOK_BUFFER_SIZE, color='r', linestyle='--',
                       label=f'Max Buffer Size ({WEBHOOK_BUFFER_SIZE})')
            plt.xlabel('Time (seconds)')
            plt.ylabel('Items in Buffer')
            plt.title('Buffer Usage Over Time')
            plt.legend()
            plt.grid(True)
        else:
            plt.text(0.5, 0.5, 'No buffer data collected',
                    horizontalalignment='center', verticalalignment='center')

        # Plot 2: Input vs Output Rates
        plt.subplot(2, 2, 2)

        # Aggregate rates by second
        inflow_by_second = {}
        for timestamp, count in metrics['inflow']:
            second = int(timestamp - start_time)
            inflow_by_second[second] = count

        processed_by_second = {}
        for timestamp, count in metrics['processed']:
            second = int(timestamp - start_time)
            processed_by_second[second] = count

        # Get all seconds
        all_seconds = sorted(set(list(inflow_by_second.keys()) +
                                list(processed_by_second.keys())))

        if all_seconds:
            x_vals = all_seconds
            inflow_vals = [inflow_by_second.get(s, 0) for s in all_seconds]
            processed_vals = [processed_by_second.get(s, 0) for s in all_seconds]

            plt.bar(x_vals, inflow_vals, alpha=0.6, label='Items Received/sec')
            plt.bar(x_vals, processed_vals, alpha=0.6, label='Items Processed/sec')
            plt.xlabel('Time (seconds)')
            plt.ylabel('Items per Second')
            plt.title('Input vs Processing Rate')
            plt.legend()
            plt.grid(True)
        else:
            plt.text(0.5, 0.5, 'No rate data collected',
                    horizontalalignment='center', verticalalignment='center')

        # Plot 3: Backpressure Events
        plt.subplot(2, 2, 3)
        if backpressure_by_second:
            x_vals = sorted(backpressure_by_second.keys())
            y_vals = [backpressure_by_second[s] for s in x_vals]

            plt.bar(x_vals, y_vals, color='r', alpha=0.7)
            plt.xlabel('Time (seconds)')
            plt.ylabel('Rejected Items')
            plt.title('Backpressure Events (Rejected Items)')
            plt.grid(True)
        else:
            plt.text(0.5, 0.5, 'No backpressure events recorded',
                    horizontalalignment='center', verticalalignment='center')

        # Plot 4: Summary Pie Chart
        plt.subplot(2, 2, 4)
        labels = ['Accepted', 'Rejected (Backpressure)']
        sizes = [metrics['accepted'], metrics['rejected']]
        colors = ['#66b3ff', '#ff9999']

        if sum(sizes) > 0:
            plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            plt.axis('equal')
            plt.title('Item Processing Summary')
        else:
            plt.text(0.5, 0.5, 'No data to display',
                    horizontalalignment='center', verticalalignment='center')

        plt.tight_layout()
        plt.savefig("variable_rate_test.png")
        print("\nPlot saved as 'variable_rate_test.png'")

        # Display the plot if running in interactive environment
        plt.show()

    except ImportError:
        print("\nMatplotlib not available. Install it to generate plots.")
    except Exception as e:
        print(f"\nError generating plot: {e}")

def main():
    """Main function to run the variable-rate test."""
    metrics = variable_rate_test()

    try:
        plot_metrics(metrics)
    except Exception as e:
        print(f"Error plotting results: {e}")

    print("\nTest completed!")

if __name__ == "__main__":
    main()