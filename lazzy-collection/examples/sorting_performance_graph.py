import heapq
import random
import time
import matplotlib.pyplot as plt

from src.core.entites.lazy_collection import LazyCollection


def generate_large_dataset(size):
    return (random.randint(0, size) for _ in range(size))

# Lazy top-k eficiente
def lazy_top_k(k, size):
    data = LazyCollection(generate_large_dataset(size))
    heap = []

    for num in data:
        if len(heap) < k:
            heapq.heappush(heap, num)
        else:
            heapq.heappushpop(heap, num)
    return sorted(heap, reverse=True)

# Eager sorting tradicional (menos eficiente para top-k)
def eager_top_k(k, size):
    data = list(generate_large_dataset(size))
    data.sort(reverse=True)
    return data[:k]

if __name__ == "__main__":
    sizes = [10**5, 5*10**5, 10**6, 5*10**6, 10**7]
    lazy_times = []
    eager_times = []

    for size in sizes:
        start = time.time()
        lazy_top_k(5, size)
        lazy_times.append(time.time() - start)

        start = time.time()
        eager_top_k(5, size)
        eager_times.append(time.time() - start)

    plt.plot(sizes, lazy_times, label='Lazy Sorting (Top-K)', marker='o')
    plt.plot(sizes, eager_times, label='Eager Sorting (Full sort)', marker='o')
    plt.xlabel('Dataset Size')
    plt.ylabel('Time (seconds)')
    plt.title('Lazy Sorting vs Eager Sorting Performance')
    plt.legend()
    plt.grid(True)
    plt.savefig('sorting_comparison.png')
    plt.show()
