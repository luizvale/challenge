import functools
import time
import matplotlib.pyplot as plt

from src.core.entites.lazy_collection import LazyCollection


@functools.lru_cache(maxsize=None)
def expensive_computation(x):
    time.sleep(0.001)
    return x * x

def measure_time(use_cache):
    data = LazyCollection(range(1, 2001))
    start = time.time()
    results = data.map(expensive_computation).take(1000).to_list()
    return time.time() - start

if __name__ == "__main__":
    first_run = measure_time(use_cache=False)
    second_run = measure_time(use_cache=True)

    plt.bar(['First Run (no cache)', 'Second Run (cache)'], [first_run, second_run], color=['red', 'green'])
    plt.ylabel('Time (seconds)')
    plt.title('Performance Impact of Lazy Caching')
    plt.grid(True, axis='y')
    plt.savefig('time_comparison_caching.png')
    plt.show()
