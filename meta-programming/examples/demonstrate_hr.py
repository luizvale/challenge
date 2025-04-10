"""
Demonstrates how to use HRDocument in a real scenario (with logging).
"""

import logging
from src.plugins.hr_document import HRDocument

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    valid_hr_doc = {
        'name': 'João da Silva',
        'employee_id': '12345',
        'department': 'Financeiro'
    }

    invalid_hr_doc = {
        'name': 'Maria Oliveira',
        'employee_id': 'ABC'  # not numeric
    }

    hr_doc = HRDocument()

    logger.info("== Valid Scenario ==")
    if hr_doc.validate(valid_hr_doc):
        hr_doc.process(valid_hr_doc)
    else:
        logger.warning("Unexpected failure in HR doc validation for valid data.")

    logger.info("\n== Invalid Scenario ==")
    if not hr_doc.validate(invalid_hr_doc):
        logger.info("Validation failed as expected for invalid HR doc.")
    else:
        logger.warning("Validation passed unexpectedly; continuing to process.")
        hr_doc.process(invalid_hr_doc)
