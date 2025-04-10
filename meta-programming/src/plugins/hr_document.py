# plugins/hr_document.py
from src.core.interfaces.base_contract import BaseContract


class HRDocument(BaseContract):
    """
    Human Resources Document Validator
    Applies compliance rules to HR documents
    """

    def validate(self, data: dict) -> bool:
        """
        Validate HR document

        Checks the integrity of employee data

        :param data: HR document data
        :return: Boolean indicating if the document is valid
        """
        # Example validations
        required_fields = ['name', 'employee_id', 'department']
        for field in required_fields:
            if field not in data:
                print(f"Missing required field: {field}")
                return False

        # Validate employee ID
        if not str(data['employee_id']).isdigit():
            print("Employee ID must be numeric")
            return False

        return True

    def process(self, data: dict):
        """
        Process approved HR document

        Simulates recording and processing of the document

        :param data: HR document data
        """
        print(f"Processing HR document for {data['name']}")
        print(f"Department: {data['department']}")
