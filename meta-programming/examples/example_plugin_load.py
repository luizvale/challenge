"""
Demonstrates how to dynamically load plugin classes using PluginLoader,
then validate and process sample data using logging.
"""

import logging
import os
from src.external.plugin_loader import PluginLoader

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    plugin_dir = os.path.join(os.path.dirname(__file__), "..", "src", "plugins")
    logger.info(f"Loading plugins from directory: {plugin_dir}")

    loaded_plugins = PluginLoader.load_plugins(plugin_dir)

    logger.info("\nPlugins found:")
    for class_name in loaded_plugins:
        logger.info(f"  - {class_name}")

    # If 'FinancialContract' was found, let's test it:
    if 'FinancialContract' in loaded_plugins:
        Financial = loaded_plugins['FinancialContract']
        instance = Financial()

        data_test = {'value': 5000, 'risk_level': 0.3}
        logger.info("\n== Testing FinancialContract via plugin loader ==")
        if instance.validate(data_test):
            instance.process(data_test)
        else:
            logger.warning("Validation failed (unexpected)")

    # Similarly for HRDocument, if present:
    if 'HRDocument' in loaded_plugins:
        HRDocClass = loaded_plugins['HRDocument']
        hr_instance = HRDocClass()

        data_test = {'name': 'Paula', 'employee_id': '789', 'department': 'TI'}
        logger.info("\n== Testing HRDocument via plugin loader ==")
        if hr_instance.validate(data_test):
            hr_instance.process(data_test)
        else:
            logger.warning("Validation failed (unexpected)")
