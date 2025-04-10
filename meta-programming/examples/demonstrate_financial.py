"""
Demonstrates how to use FinancialContract in a real scenario (with logging).
"""
import logging
from src.plugins.financial_contract import FinancialContract

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)  # config log level

    # Valid scenario
    valid_data = {
        'value': 10000,
        'risk_level': 0.4
    }

    # Invalid scenario (missing 'risk_level', negative value, etc.)
    invalid_data = {
        'value': -500
    }

    contract = FinancialContract()

    logger.info("== Valid Scenario ==")
    if contract.validate(valid_data):
        contract.process(valid_data)
    else:
        logger.warning("Validation unexpectedly failed for supposedly valid data.")

    logger.info("\n== Invalid Scenario ==")
    if not contract.validate(invalid_data):
        logger.info("Validation correctly failed for invalid data.")
    else:
        logger.warning("Validation unexpectedly passed for invalid data; processing anyway.")
        contract.process(invalid_data)
