# external/plugin_loader.py
import os
import importlib
import sys


class PluginLoader:
    """
    Dynamic plugin loader.
    """

    @staticmethod
    def load_plugins(plugin_dir):
        """
        Load plugins from a given directory.

        :param plugin_dir: Directory containing plugin modules.
        :return: Dictionary of loaded plugin classes.
        """
        plugins = {}

        # Ensure the directory exists
        os.makedirs(plugin_dir, exist_ok=True)

        # Add directory to the import path
        sys.path.insert(0, plugin_dir)

        try:
            # List files in the plugin directory
            for filename in os.listdir(plugin_dir):
                if filename.endswith('.py') and not filename.startswith('__'):
                    # Remove .py extension
                    module_name = filename[:-3]

                    try:
                        # Dynamically import the module
                        module = importlib.import_module(module_name)

                        # Find classes that inherit from BaseContract
                        for name, obj in vars(module).items():
                            if (
                                isinstance(obj, type)
                                and hasattr(obj, '__base__')
                                and obj.__base__.__name__ == 'BaseContract'
                            ):
                                plugins[name] = obj

                    except Exception as e:
                        print(f"Error importing plugin {module_name}: {e}")

        finally:
            # Remove added directory from import path
            sys.path.pop(0)

        return plugins
