"""
Plugin Manager for XSOAR CLI

This module handles the discovery, loading, and management of plugins
for the xsoar-cli application from a local directory.
"""

import importlib.util
import logging
import sys
import types
from pathlib import Path

import click

from . import PluginLoadError, PluginRegistrationError, XSOARPlugin

logger = logging.getLogger(__name__)


class PluginManager:
    """Manages the discovery, loading, and registration of XSOAR CLI plugins from the plugins directory."""

    def __init__(self, plugins_dir: Path | None = None) -> None:
        """Defaults to ~/.local/xsoar-cli/plugins if no directory is provided."""
        if plugins_dir is None:
            self.plugins_dir = Path.home() / ".local" / "xsoar-cli" / "plugins"
        else:
            self.plugins_dir = plugins_dir

        self.loaded_plugins: dict[str, XSOARPlugin] = {}
        self.failed_plugins: dict[str, Exception] = {}
        self.command_conflicts: list[dict[str, str]] = []

        # Ensure plugins directory exists
        self.plugins_dir.mkdir(parents=True, exist_ok=True)

        # Add plugins directory to Python path if not already there
        plugins_dir_str = str(self.plugins_dir)
        if plugins_dir_str not in sys.path:
            sys.path.insert(0, plugins_dir_str)

    def discover_plugins(self) -> list[str]:
        """Scans the plugins directory for Python files and returns their module names."""
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

    def _load_module_from_file(self, module_name: str, file_path: Path) -> types.ModuleType:
        """Loads a Python module from disk and injects XSOARPlugin into its namespace so plugins do not need to import it explicitly."""
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            raise PluginLoadError(f"Could not load module spec for {file_path}")

        module = importlib.util.module_from_spec(spec)

        # Inject XSOARPlugin class into the module's namespace
        # This allows plugins to use XSOARPlugin without complex imports
        from . import XSOARPlugin

        setattr(module, "XSOARPlugin", XSOARPlugin)

        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    def _find_plugin_classes(self, module: types.ModuleType) -> list[type[XSOARPlugin]]:
        """Returns all XSOARPlugin subclasses found in the given module."""
        plugin_classes = []

        for attr_name in dir(module):
            attr = getattr(module, attr_name)

            # Check if it's a class that inherits from XSOARPlugin
            if isinstance(attr, type) and issubclass(attr, XSOARPlugin) and attr is not XSOARPlugin:
                plugin_classes.append(attr)

        return plugin_classes

    def load_plugin(self, plugin_name: str) -> XSOARPlugin | None:
        """Loads and initializes a single plugin by module name. Raises PluginLoadError on failure."""
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
            logger.debug(f"Failed to load plugin '{plugin_name}': {e}")
            raise PluginLoadError(f"Failed to load plugin '{plugin_name}': {e}")

    def load_all_plugins(self, *, ignore_errors: bool = True) -> dict[str, XSOARPlugin]:
        """Loads all discovered plugins. By default, a failed plugin is recorded and skipped so remaining plugins can still load. Pass ignore_errors=False to abort on the first failure."""
        discovered_plugins = self.discover_plugins()

        for plugin_name in discovered_plugins:
            try:
                self.load_plugin(plugin_name)
            except PluginLoadError as e:
                if not ignore_errors:
                    raise
                logger.debug(f"Skipping failed plugin: {e}")

        return self.loaded_plugins.copy()

    def register_plugin_commands(self, cli_group: click.Group) -> None:
        """Registers each loaded plugin's command with the given Click group. Commands that conflict with an existing command are skipped and recorded in command_conflicts."""
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
                logger.debug(error_msg)
                raise PluginRegistrationError(error_msg)

        # Store conflicts for later reporting
        self.command_conflicts = conflicts

    def unload_plugin(self, plugin_name: str) -> None:
        """Calls the plugin's cleanup method and removes it from the loaded plugins registry."""
        if plugin_name in self.loaded_plugins:
            plugin = self.loaded_plugins[plugin_name]
            try:
                plugin.cleanup()
            except Exception as e:
                logger.warning(f"Plugin '{plugin_name}' cleanup failed: {e}")
            del self.loaded_plugins[plugin_name]
            logger.info(f"Unloaded plugin: {plugin_name}")

    def unload_all_plugins(self) -> None:
        """Unloads all loaded plugins."""
        plugin_names = list(self.loaded_plugins.keys())
        for plugin_name in plugin_names:
            self.unload_plugin(plugin_name)

    def get_plugin_info(self) -> dict[str, dict[str, str]]:
        """Returns name, version, and description for each loaded plugin."""
        info = {}
        for plugin_name, plugin in self.loaded_plugins.items():
            info[plugin_name] = {
                "name": plugin.name,
                "version": plugin.version,
                "description": plugin.description or "No description provided",
            }
        return info

    def get_failed_plugins(self) -> dict[str, str]:
        """Returns a mapping of plugin names to their load error messages."""
        return {name: str(error) for name, error in self.failed_plugins.items()}

    def get_command_conflicts(self) -> list[dict[str, str]]:
        """Returns any command conflicts detected during the last call to register_plugin_commands."""
        return self.command_conflicts.copy()

    def reload_plugin(self, plugin_name: str) -> XSOARPlugin | None:
        """Unloads and reloads a plugin, clearing any previous load failure. Useful for picking up changes to a plugin file without restarting."""
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
