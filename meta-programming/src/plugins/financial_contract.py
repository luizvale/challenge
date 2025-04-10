from ..core.interfaces.base_contract import BaseContract


class FinancialContract(BaseContract):
    """
    Validator for financial contracts.
    Applies specific financial compliance rules.
    """

    def validate(self, data: dict) -> bool:
        """
        Validate financial contract.

        Checks the integrity and compliance of the document.

        :param data: Financial contract data.
        :return: Boolean indicating whether the contract is valid.
        """
        # Example validations
        required_fields = ['value', 'risk_level']
        for field in required_fields:
            if field not in data:
                print(f"Missing required field: {field}")
                return False

        # Value validation
        if data['value'] <= 0:
            print("Contract value must be positive")
            return False

        # Risk level validation
        if data['risk_level'] > 0.8:
            print("Risk level is too high")
            return False

        return True

    def process(self, data: dict):
        """
        Process approved financial contract.

        Simulates registration and handling of the contract.

        :param data: Financial contract data.
        """
        print(f"Processing financial contract worth R$ {data['value']}")
        print(f"Risk level: {data['risk_level']}")
