# core/metaclasses/contract_meta.py

import inspect
import logging
from typing import get_type_hints

logger = logging.getLogger(__name__)


class ContractMeta(type):
    """
    Metaclass to enforce API contract and automatic class registration,
    including method signature validation (type hints).
    """
    REGISTRY = {}

    def __new__(mcs, name, bases, attrs):
        # Validate mandatory class docstring
        if not attrs.get('__doc__'):
            raise TypeError(f"Class {name} must include a descriptive docstring")

        # Required methods
        required_methods = ['validate', 'process']
        for method in required_methods:
            if method not in attrs or not callable(attrs[method]):
                raise TypeError(f"Class must implement method '{method}'")

            # Validate method docstring
            method_doc = attrs[method].__doc__
            if not method_doc or len(method_doc.strip()) < 10:
                raise TypeError(f"Method {method} must have a detailed docstring")

            # Validate type hints (optional)
            mcs._check_type_hints(name, attrs[method], method)

        new_class = super().__new__(mcs, name, bases, attrs)

        # Automatically register the class (excluding base classes)
        if bases and bases[0] is not object:
            mcs.REGISTRY[name] = new_class

        return new_class

    @staticmethod
    def _check_type_hints(class_name: str, method_obj, method_name: str) -> None:
        """
        Checks whether the method has valid type annotations.
        Example: 'validate(self, data: dict) -> bool'
        """
        sig = inspect.signature(method_obj)
        hints = get_type_hints(method_obj)

        # Example check: 'data' must be a dict, 'validate' must return a bool
        if method_name == 'validate':
            if 'data' not in hints:
                logger.warning(f"{class_name}.{method_name} is missing type hint for 'data'.")
            else:
                expected_data_type = dict
                if hints['data'] is not expected_data_type:
                    raise TypeError(
                        f"{class_name}.{method_name} must have 'data: dict', but found {hints['data']}"
                    )

            if 'return' not in hints or hints['return'] is not bool:
                logger.warning(f"{class_name}.{method_name} does not return a bool or return type is incorrect.")
