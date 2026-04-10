"""Plugin manager: discovery, loading, and registration of CLI plugins."""

from __future__ import annotations

import importlib.util
import logging
import types
from pathlib import Path
from typing import TYPE_CHECKING

from . import PluginLoadError, PluginRegistrationError, XSOARPlugin

if TYPE_CHECKING:
    import click

logger = logging.getLogger(__name__)


class PluginManager:
    """Discovers, loads, and registers plugins from a local directory."""

    DEFAULT_PLUGINS_DIR: Path = Path.home() / ".local" / "xsoar-cli" / "plugins"

    def __init__(self, plugins_dir: Path | None = None) -> None:
        """Defaults to ``DEFAULT_PLUGINS_DIR`` if no directory is provided."""
        self.plugins_dir = plugins_dir if plugins_dir is not None else self.DEFAULT_PLUGINS_DIR
        self.loaded_plugins: dict[str, XSOARPlugin] = {}
        self.failed_plugins: dict[str, Exception] = {}
        self.command_conflicts: list[dict[str, str]] = []

    @property
    def plugins_dir_exists(self) -> bool:
        """Return ``True`` if the plugins directory exists on disk."""
        return self.plugins_dir.exists()

    def discover_plugins(self) -> list[str]:
        """Scan the plugins directory for Python files and return their module names."""
        if not self.plugins_dir_exists:
            logger.debug("Plugins directory does not exist: %s", self.plugins_dir)
            return []

        plugin_names = []
        for file_path in self.plugins_dir.glob("*.py"):
            if file_path.name.startswith("__"):
                continue  # Skip __init__.py, __pycache__, etc.
            plugin_names.append(file_path.stem)

        logger.debug("Discovered %d plugin file(s): %s", len(plugin_names), plugin_names)
        return plugin_names

    def _load_module_from_file(self, module_name: str, file_path: Path) -> types.ModuleType:
        """Load a Python module from a file path."""
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            raise PluginLoadError(f"Could not load module spec for {file_path}")

        module = importlib.util.module_from_spec(spec)

        try:
            spec.loader.exec_module(module)
        except NameError as e:
            if "XSOARPlugin" in str(e):
                raise PluginLoadError(
                    f"Plugin '{module_name}' uses XSOARPlugin without importing it. "
                    "Add 'from xsoar_cli.plugins import XSOARPlugin' to your plugin file."
                ) from e
            raise

        return module

    def _find_plugin_classes(self, module: types.ModuleType) -> list[type[XSOARPlugin]]:
        """Return all XSOARPlugin subclasses found in the given module."""
        plugin_classes = []
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, XSOARPlugin) and attr is not XSOARPlugin:
                plugin_classes.append(attr)
        return plugin_classes

    def load_plugin(self, plugin_name: str) -> XSOARPlugin | None:
        """Load and initialize a single plugin by module name."""
        if plugin_name in self.loaded_plugins:
            return self.loaded_plugins[plugin_name]

        try:
            file_path = self.plugins_dir / f"{plugin_name}.py"
            if not file_path.exists():
                raise PluginLoadError(f"Plugin file not found: {file_path}")

            module = self._load_module_from_file(plugin_name, file_path)

            plugin_classes = self._find_plugin_classes(module)
            if not plugin_classes:
                raise PluginLoadError(f"No XSOARPlugin classes found in {plugin_name}.py")

            if len(plugin_classes) > 1:
                logger.warning(
                    "Multiple plugin classes found in %s.py, using the first one",
                    plugin_name,
                )

            plugin_instance = plugin_classes[0]()

            try:
                plugin_instance.initialize()
            except Exception as e:
                raise PluginLoadError(f"Plugin '{plugin_name}' initialization failed: {e}")

            self.loaded_plugins[plugin_name] = plugin_instance
            logger.debug("Successfully loaded plugin: %s", plugin_name)
            return plugin_instance

        except Exception as e:
            self.failed_plugins[plugin_name] = e
            logger.debug("Failed to load plugin '%s': %s", plugin_name, e)
            raise PluginLoadError(f"Failed to load plugin '{plugin_name}': {e}")

    def load_all_plugins(self, *, ignore_errors: bool = True) -> dict[str, XSOARPlugin]:
        """Load all discovered plugins.

        By default, a failed plugin is recorded and skipped so remaining plugins
        can still load. Pass ``ignore_errors=False`` to abort on the first failure.
        """
        discovered_plugins = self.discover_plugins()

        for plugin_name in discovered_plugins:
            try:
                self.load_plugin(plugin_name)
            except PluginLoadError as e:
                if not ignore_errors:
                    raise
                logger.debug("Skipping failed plugin: %s", e)

        return self.loaded_plugins.copy()

    def register_plugin_commands(self, cli_group: click.Group) -> None:
        """Register each loaded plugin's command with the given Click group.

        Commands that conflict with an existing command are skipped and recorded
        in ``command_conflicts``. Registration failures are logged and recorded
        in ``failed_plugins`` so remaining plugins can still register.
        """
        import click as _click  # Lazy import for performance reasons

        conflicts: list[dict[str, str]] = []

        for plugin_name, plugin in list(self.loaded_plugins.items()):
            try:
                command = plugin.get_command()
                if not isinstance(command, (_click.Command, _click.Group)):
                    raise PluginRegistrationError(
                        f"Plugin '{plugin_name}' get_command() must return a Click Command or Group",
                    )

                if command.name in cli_group.commands:
                    conflict_info = {
                        "plugin_name": plugin_name,
                        "command_name": command.name,
                        "plugin_version": plugin.version,
                    }
                    conflicts.append(conflict_info)
                    logger.warning(
                        "Plugin '%s' command '%s' conflicts with existing command",
                        plugin_name,
                        command.name,
                    )
                    continue

                cli_group.add_command(command)
                logger.debug("Registered command '%s' from plugin '%s'", command.name, plugin_name)

            except Exception as e:
                self.failed_plugins[plugin_name] = e
                logger.warning("Failed to register plugin '%s': %s", plugin_name, e)

        self.command_conflicts = conflicts

    def get_plugin_info(self) -> dict[str, dict[str, str]]:
        """Return name, version, and description for each loaded plugin."""
        info = {}
        for plugin_name, plugin in self.loaded_plugins.items():
            info[plugin_name] = {
                "name": plugin.name,
                "version": plugin.version,
                "description": plugin.description or "No description provided",
            }
        return info

    def get_failed_plugins(self) -> dict[str, str]:
        """Return a mapping of plugin names to their error messages."""
        return {name: str(error) for name, error in self.failed_plugins.items()}

    def get_command_conflicts(self) -> list[dict[str, str]]:
        """Return command conflicts detected during the last registration."""
        return self.command_conflicts.copy()
