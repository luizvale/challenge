from itertools import islice
from typing import Iterable

from ..interfaces.lazy_collection_contract import ILazyCollection, T

class LazyCollection(ILazyCollection[T]):

    def __init__(self, source: Iterable[T]):
        self._iter_factory = lambda: iter(source)

    def __iter__(self):
        return self._iter_factory()

    def filter(self, predicate):
        return LazyCollection(x for x in self if predicate(x))

    def map(self, func):
        return LazyCollection(func(x) for x in self)

    def reduce(self, func, initializer):
        acc = initializer
        for x in self:
            acc = func(acc, x)
        return acc

    def paginate(self, page_size, page_number):
        start = page_size * (page_number - 1)
        return LazyCollection(islice(self, start, start + page_size))

    def chunk(self, size):
        def generator():
            it = iter(self)
            while True:
                chunk = list(islice(it, size))
                if not chunk:
                    break
                yield chunk
        return LazyCollection(generator())

    def take(self, n):
        return LazyCollection(islice(self, n))

    def to_list(self):
        return list(self)