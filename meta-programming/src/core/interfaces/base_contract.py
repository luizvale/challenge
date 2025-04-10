# core/base_contract.py
from abc import ABC, abstractmethod
from src.core.metaclasses.contract_meta import ContractMeta


class BaseContract(metaclass=ContractMeta):
    """
    Base contract for validating different types of documents.
    """

    @abstractmethod
    def validate(self, data: dict) -> bool:
        """
        Validate the document.

        :param data: Data of the document to be validated.
        :return: Boolean indicating whether the document is valid.
        """
        pass

    @abstractmethod
    def process(self, data: dict):
        """
        Process the document after validation.

        :param data: Data of the document to be processed.
        """
        pass
