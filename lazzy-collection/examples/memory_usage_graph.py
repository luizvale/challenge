from memory_profiler import memory_usage
import matplotlib.pyplot as plt

from src.core.entites.lazy_collection import LazyCollection


def eager_processing():
    data = [x**2 for x in range(1, 5_000_001)]
    filtered = [x for x in data if x % 2 == 0]
    return sum(filtered)

def lazy_processing():
    data = LazyCollection(range(1, 5_000_001))
    result = data.map(lambda x: x**2).filter(lambda x: x % 2 == 0).reduce(lambda acc, val: acc + val, 0)
    return result

if __name__ == "__main__":
    mem_eager = memory_usage((eager_processing, ), interval=0.1)
    mem_lazy = memory_usage((lazy_processing, ), interval=0.1)

    plt.plot(mem_eager, label='Eager Processing', linewidth=2)
    plt.plot(mem_lazy, label='Lazy Processing', linewidth=2)
    plt.xlabel('Time (0.1s intervals)')
    plt.ylabel('Memory Usage (MiB)')
    plt.title('Memory Usage: Lazy vs Eager Evaluation')
    plt.legend()
    plt.grid(True)
    plt.savefig('memory_comparison.png')
    plt.show()
