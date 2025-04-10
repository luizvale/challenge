"""
Interface for transformation components.
"""
import logging
from abc import ABC, abstractmethod
from typing import Optional, Generator, Iterable
from ..entities.data_item import DataItem

logger = logging.getLogger(__name__)

class TransformerInterface(ABC):
    """
    Contract for data transformers in the pipeline.
    Each transformer must implement the transform method.
    """
    @abstractmethod
    def transform(self, item: DataItem) -> Optional[DataItem]:
        """Transforma um único item de dados."""
        pass

    @abstractmethod
    def transform_stream(self, stream: Iterable[DataItem]) -> Generator[DataItem, None, None]:
        """Transforma um fluxo de itens."""
        pass

class BaseTransformer(TransformerInterface):
    """Implementação base para transformadores."""

    @abstractmethod
    def transform(self, item: DataItem) -> Optional[DataItem]:
        """Continua sendo abstrato, deve ser implementado pelas subclasses."""
        pass

    def transform_stream(self, stream: Iterable[DataItem]) -> Generator[DataItem, None, None]:
        """Implementação padrão com tratamento de erros."""
        for item in stream:
            try:
                transformed = self.transform(item)
                if transformed is not None:
                    yield transformed
            except Exception as e:
                logger.error(f"Error in transformer {self.__class__.__name__}: {e}")
                continue