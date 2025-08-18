"""
Plugin Manager for XSOAR CLI

This module handles the discovery, loading, and management of plugins
for the xsoar-cli application from a local directory.
"""

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Type

import click

from . import PluginLoadError, PluginRegistrationError, XSOARPlugin

logger = logging.getLogger(__name__)


class PluginManager:
    """
    Manages the discovery, loading, and registration of XSOAR CLI plugins
    from the ~/.local/xsoar-cli/plugins directory.
    """

    def __init__(self, plugins_dir: Optional[Path] = None):
        """
        Initialize the plugin manager.

        Args:
            plugins_dir: Custom plugins directory. If None, uses ~/.local/xsoar-cli/plugins
        """
        if plugins_dir is None:
            self.plugins_dir = Path.home() / ".local" / "xsoar-cli" / "plugins"
        else:
            self.plugins_dir = plugins_dir

        self.loaded_plugins: Dict[str, XSOARPlugin] = {}
        self.failed_plugins: Dict[str, Exception] = {}
        self.command_conflicts: List[Dict[str, str]] = []

        # Ensure plugins directory exists
        self.plugins_dir.mkdir(parents=True, exist_ok=True)

        # Add plugins directory to Python path if not already there
        plugins_dir_str = str(self.plugins_dir)
        if plugins_dir_str not in sys.path:
            sys.path.insert(0, plugins_dir_str)

    def discover_plugins(self) -> List[str]:
        """
        Discover available plugins by scanning the plugins directory for Python files.

        Returns:
            List of plugin module names found
        """
        plugin_names = []

        if not self.plugins_dir.exists():
            logger.info(f"Plugins directory does not exist: {self.plugins_dir}")
            return plugin_names

        for file_path in self.plugins_dir.glob("*.py"):
            if file_path.name.startswith("__"):
                continue  # Skip __init__.py, __pycache__, etc.

            module_name = file_path.stem
            plugin_names.append(module_name)

        logger.info(f"Discovered {len(plugin_names)} plugin files: {plugin_names}")
        return plugin_names

    def _load_module_from_file(self, module_name: str, file_path: Path):
        """
        Load a Python module from a file path.

        Args:
            module_name: Name to give the module
            file_path: Path to the Python file

        Returns:
            The loaded module
        """
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            raise PluginLoadError(f"Could not load module spec for {file_path}")

        module = importlib.util.module_from_spec(spec)

        # Inject XSOARPlugin class into the module's namespace
        # This allows plugins to use XSOARPlugin without complex imports
        from . import XSOARPlugin

        module.XSOARPlugin = XSOARPlugin

        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    def _find_plugin_classes(self, module) -> List[Type[XSOARPlugin]]:
        """
        Find all XSOARPlugin classes in a module.

        Args:
            module: The module to search

        Returns:
            List of plugin classes found
        """
        plugin_classes = []

        for attr_name in dir(module):
            attr = getattr(module, attr_name)

            # Check if it's a class that inherits from XSOARPlugin
            if isinstance(attr, type) and issubclass(attr, XSOARPlugin) and attr is not XSOARPlugin:
                plugin_classes.append(attr)

        return plugin_classes

    def load_plugin(self, plugin_name: str) -> Optional[XSOARPlugin]:
        """
        Load a single plugin by name.

        Args:
            plugin_name: Name of the plugin module to load

        Returns:
            The loaded plugin instance, or None if loading failed

        Raises:
            PluginLoadError: If the plugin fails to load
        """
        if plugin_name in self.loaded_plugins:
            return self.loaded_plugins[plugin_name]

        try:
            file_path = self.plugins_dir / f"{plugin_name}.py"
            if not file_path.exists():
                raise PluginLoadError(f"Plugin file not found: {file_path}")

            # Load the module
            module = self._load_module_from_file(plugin_name, file_path)

            # Find plugin classes in the module
            plugin_classes = self._find_plugin_classes(module)

            if not plugin_classes:
                raise PluginLoadError(
                    f"No XSOARPlugin classes found in {plugin_name}.py",
                )

            if len(plugin_classes) > 1:
                logger.warning(
                    f"Multiple plugin classes found in {plugin_name}.py, using the first one",
                )

            # Instantiate the first plugin class found
            plugin_class = plugin_classes[0]
            plugin_instance = plugin_class()

            # Initialize the plugin
            try:
                plugin_instance.initialize()
            except Exception as e:
                raise PluginLoadError(f"Plugin '{plugin_name}' initialization failed: {e}")

            # Store the loaded plugin
            self.loaded_plugins[plugin_name] = plugin_instance
            logger.info(f"Successfully loaded plugin: {plugin_name}")

            return plugin_instance

        except Exception as e:
            self.failed_plugins[plugin_name] = e
            logger.error(f"Failed to load plugin '{plugin_name}': {e}")
            raise PluginLoadError(f"Failed to load plugin '{plugin_name}': {e}")

    def load_all_plugins(self, ignore_errors: bool = True) -> Dict[str, XSOARPlugin]:
        """
        Load all discovered plugins.

        Args:
            ignore_errors: If True, continue loading other plugins when one fails

        Returns:
            Dictionary of successfully loaded plugins

        Raises:
            PluginLoadError: If ignore_errors is False and any plugin fails to load
        """
        discovered_plugins = self.discover_plugins()

        for plugin_name in discovered_plugins:
            try:
                self.load_plugin(plugin_name)
            except PluginLoadError as e:
                if not ignore_errors:
                    raise
                logger.warning(f"Skipping failed plugin: {e}")

        return self.loaded_plugins.copy()

    def register_plugin_commands(self, cli_group: click.Group) -> None:
        """
        Register all loaded plugin commands with the CLI group.

        Args:
            cli_group: The Click group to register commands with

        Raises:
            PluginRegistrationError: If a plugin command fails to register
        """
        conflicts = []

        for plugin_name, plugin in self.loaded_plugins.items():
            try:
                command = plugin.get_command()
                if not isinstance(command, (click.Command, click.Group)):
                    raise PluginRegistrationError(
                        f"Plugin '{plugin_name}' get_command() must return a Click Command or Group",
                    )

                # Ensure the command name doesn't conflict with existing commands
                if command.name in cli_group.commands:
                    conflict_info = {
                        "plugin_name": plugin_name,
                        "command_name": command.name,
                        "plugin_version": plugin.version,
                    }
                    conflicts.append(conflict_info)
                    logger.warning(
                        f"Plugin '{plugin_name}' command '{command.name}' conflicts with existing command",
                    )
                    continue

                cli_group.add_command(command)
                logger.info(f"Registered command '{command.name}' from plugin '{plugin_name}'")

            except Exception as e:
                error_msg = f"Failed to register plugin '{plugin_name}': {e}"
                logger.error(error_msg)
                raise PluginRegistrationError(error_msg)

        # Store conflicts for later reporting
        self.command_conflicts = conflicts

    def unload_plugin(self, plugin_name: str) -> None:
        """
        Unload a plugin and call its cleanup method.

        Args:
            plugin_name: Name of the plugin to unload
        """
        if plugin_name in self.loaded_plugins:
            plugin = self.loaded_plugins[plugin_name]
            try:
                plugin.cleanup()
            except Exception as e:
                logger.warning(f"Plugin '{plugin_name}' cleanup failed: {e}")
            del self.loaded_plugins[plugin_name]
            logger.info(f"Unloaded plugin: {plugin_name}")

    def unload_all_plugins(self) -> None:
        """Unload all plugins and call their cleanup methods."""
        plugin_names = list(self.loaded_plugins.keys())
        for plugin_name in plugin_names:
            self.unload_plugin(plugin_name)

    def get_plugin_info(self) -> Dict[str, Dict[str, str]]:
        """
        Get information about all loaded plugins.

        Returns:
            Dictionary with plugin information
        """
        info = {}
        for plugin_name, plugin in self.loaded_plugins.items():
            info[plugin_name] = {
                "name": plugin.name,
                "version": plugin.version,
                "description": plugin.description or "No description provided",
            }
        return info

    def get_failed_plugins(self) -> Dict[str, str]:
        """
        Get information about plugins that failed to load.

        Returns:
            Dictionary with plugin names and error messages
        """
        return {name: str(error) for name, error in self.failed_plugins.items()}

    def get_command_conflicts(self) -> List[Dict[str, str]]:
        """
        Get information about command conflicts.

        Returns:
            List of dictionaries with conflict information
        """
        return self.command_conflicts.copy()

    def reload_plugin(self, plugin_name: str) -> Optional[XSOARPlugin]:
        """
        Reload a plugin by unloading and loading it again.

        Args:
            plugin_name: Name of the plugin to reload

        Returns:
            The reloaded plugin instance, or None if reloading failed
        """
        # Unload if already loaded
        if plugin_name in self.loaded_plugins:
            self.unload_plugin(plugin_name)

        # Remove from failed plugins if it was there
        if plugin_name in self.failed_plugins:
            del self.failed_plugins[plugin_name]

        # Remove from sys.modules to force reload
        if plugin_name in sys.modules:
            del sys.modules[plugin_name]

        # Load again
        return self.load_plugin(plugin_name)

    def create_example_plugin(self) -> None:
        """
        Create an example plugin file in the plugins directory.
        """
        example_content = '''"""
Example XSOAR CLI Plugin

This is an example plugin that demonstrates how to create custom commands
for the xsoar-cli application.

The XSOARPlugin class is automatically injected into the plugin namespace,
so you don't need to import it.
"""

import click


class ExamplePlugin(XSOARPlugin):
    """Example plugin implementation."""

    @property
    def name(self) -> str:
        return "example"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "An example plugin demonstrating the plugin system"

    def get_command(self) -> click.Command:
        """Return the Click command for this plugin."""

        @click.group(help="Example plugin commands")
        def example():
            pass

        @click.command(help="Say hello")
        @click.option("--name", default="World", help="Name to greet")
        def hello(name: str):
            click.echo(f"Hello, {name}! This is from the example plugin.")

        @click.command(help="Show plugin info")
        def info():
            click.echo(f"Plugin: {self.name}")
            click.echo(f"Version: {self.version}")
            click.echo(f"Description: {self.description}")

        example.add_command(hello)
        example.add_command(info)

        return example

    def initialize(self):
        """Initialize the plugin."""
        click.echo("Example plugin initialized!")

    def cleanup(self):
        """Cleanup plugin resources."""
        pass
'''

        example_file = self.plugins_dir / "example_plugin.py"
        if not example_file.exists():
            example_file.write_text(example_content)
            logger.info(f"Created example plugin at: {example_file}")
        else:
            logger.info(f"Example plugin already exists at: {example_file}")
