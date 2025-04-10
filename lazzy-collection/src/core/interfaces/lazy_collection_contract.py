from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Callable, Generic, TypeVar, Iterable

T = TypeVar('T')
U = TypeVar('U')

class ILazyCollection(ABC, Generic[T]):

    @abstractmethod
    def __iter__(self) -> Iterable[T]:
        pass

    @abstractmethod
    def filter(self, predicate: Callable[[T], bool]) -> ILazyCollection[T]:
        pass

    @abstractmethod
    def map(self, func: Callable[[T], U]) -> ILazyCollection[U]:
        pass

    @abstractmethod
    def reduce(self, func: Callable[[U, T], U], initializer: U) -> U:
        pass

    @abstractmethod
    def paginate(self, page_size: int, page_number: int) -> ILazyCollection[T]:
        pass

    @abstractmethod
    def chunk(self, size: int) -> ILazyCollection[list[T]]:
        pass

    @abstractmethod
    def take(self, n: int) -> ILazyCollection[T]:
        pass

    @abstractmethod
    def to_list(self) -> list[T]:
        pass
