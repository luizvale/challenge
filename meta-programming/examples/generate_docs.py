"""
generate_docs.py - Generates a plugins_doc.md file listing all classes implementing BaseContract.
"""

import logging
import os

from src.external.plugin_loader import PluginLoader
from src.core.metaclasses.contract_meta import ContractMeta

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Load plugins to populate the REGISTRY
    plugin_dir = os.path.join(os.path.dirname(__file__), "..", "src", "plugins")
    PluginLoader.load_plugins(plugin_dir)
    output_file = "plugins_doc.md"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# Registered Classes List\n\n")
        for class_name, cls_obj in ContractMeta.REGISTRY.items():
            f.write(f"## {class_name}\n\n")
            doc = cls_obj.__doc__ or "No class docstring"
            f.write(f"**Docstring:** {doc.strip()}\n\n")

            for method_name in ["validate", "process"]:
                if hasattr(cls_obj, method_name):
                    method_obj = getattr(cls_obj, method_name)
                    method_doc = method_obj.__doc__ or "No method docstring"
                    f.write(f"- **{method_name}**: {method_doc.strip()}\n\n")

            f.write("\n---\n\n")

    logger.info(f"Documentation generated at {output_file}")
