"""Plugin management commands for XSOAR CLI."""

import logging
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

_EXAMPLE_PLUGIN = '''\
# Example xsoar-cli plugin.
#
# Plugin files are Python modules placed in this directory. Each file is
# discovered and loaded automatically when the CLI starts. To create your
# own plugin, copy this file or replace it entirely.
#
# For more details see: xsoar-cli plugins --help

import click

# Every plugin must explicitly import the base class.
from xsoar_cli.plugins import XSOARPlugin


# Define a class that inherits from XSOARPlugin. The CLI will find it
# automatically (you can name the class anything you like).
class HelloPlugin(XSOARPlugin):

    # Unique identifier for this plugin. Used as the key in "plugins list"
    # and "plugins info <name>".
    @property
    def name(self) -> str:
        return "hello"

    # Version string shown in "plugins list" and "plugins info".
    @property
    def version(self) -> str:
        return "1.0.0"

    # Optional human-readable summary. Shown in "plugins info" and in
    # verbose output of "plugins list". Return None (or omit entirely)
    # if you do not need a description.
    @property
    def description(self) -> str:
        return "Example plugin. Modify or replace this file."

    # Return a Click command (or group) to register on the CLI. The
    # command name becomes the top-level subcommand users invoke, e.g.
    # "xsoar-cli hello --name Alice".
    def get_command(self) -> click.Command:
        @click.command()
        @click.option("--name", default="World", help="Name to greet")
        def hello(name: str) -> None:
            """Say hello."""
            click.echo(f"Hello, {name}!")

        return hello

    def initialize(self) -> None:
        """Optional setup hook. Called once, right after the plugin is instantiated.

        In this method you might want to add setup work like opening files, checking
        credentials, etc. It's safe to remove this method if you don't need it.
        """
        pass
'''

_NOT_INITIALIZED_MSG = 'Plugin directory not initialized. Run "xsoar-cli plugins init" to set up the plugins directory.'


def _get_plugin_manager():  # noqa: ANN202
    """Return the module-level plugin_manager from cli.py.

    This import is deferred into the function body to avoid a circular import
    (cli.py imports this module at module level via _register_commands).
    """
    from xsoar_cli.cli import plugin_manager  # Lazy import for performance reasons

    return plugin_manager


@click.group()
def plugins() -> None:
    """Manage XSOAR CLI plugins."""
    pass


@click.command()
def init() -> None:
    """Initialize the plugins directory and write an example plugin."""
    from xsoar_cli.plugins.manager import PluginManager  # Lazy import for performance reasons

    plugins_dir: Path = PluginManager.DEFAULT_PLUGINS_DIR
    example_file = plugins_dir / "hello.py"

    if plugins_dir.exists():
        if example_file.exists():
            click.confirm(
                f"Example plugin already exists at {example_file}. Overwrite?",
                abort=True,
            )
    else:
        plugins_dir.mkdir(parents=True, exist_ok=True)
        click.echo(f"Created plugins directory: {plugins_dir}")

    example_file.write_text(_EXAMPLE_PLUGIN)
    click.echo(f"Wrote example plugin: {example_file}")


@click.command()
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
def list_plugins(verbose: bool) -> None:
    """List all plugins in the plugins directory."""
    plugin_manager = _get_plugin_manager()

    if not plugin_manager.plugins_dir_exists:
        click.echo(_NOT_INITIALIZED_MSG, err=True)
        raise SystemExit(1)

    loaded_info = plugin_manager.get_plugin_info()
    failed_info = plugin_manager.get_failed_plugins()

    if not loaded_info and not failed_info:
        click.echo(f"No plugins found in {plugin_manager.plugins_dir}")
        return

    click.echo(f"Plugins directory: {plugin_manager.plugins_dir}")

    # Show loaded plugins
    if loaded_info:
        click.echo("\nLoaded Plugins:")
        for plugin_name, info in loaded_info.items():
            if verbose:
                click.echo(f"  {plugin_name}")
                click.echo(f"    Name: {info['name']}")
                click.echo(f"    Version: {info['version']}")
                click.echo(f"    Description: {info['description']}")
            else:
                click.echo(f"  {plugin_name} (v{info['version']})")

    # Show failed plugins
    if failed_info:
        click.echo("\nFailed Plugins:")
        for plugin_name, error in failed_info.items():
            if verbose:
                click.echo(f"  {plugin_name}: {error}")
            else:
                click.echo(f"  {plugin_name}")

    # Show command conflicts
    conflicts = plugin_manager.get_command_conflicts()
    if conflicts:
        click.echo("\nCommand Conflicts:")
        for conflict in conflicts:
            click.echo(f"  Plugin '{conflict['plugin_name']}' command '{conflict['command_name']}' conflicts with core command")
            click.echo(f"    Plugin version: {conflict['plugin_version']}")
            click.echo("    Solution: Rename the command in your plugin or use a command group")


@click.command()
@click.argument("plugin_name", type=str)
@click.pass_context
def info(ctx: click.Context, plugin_name: str) -> None:
    """Show detailed information about a plugin."""
    plugin_manager = _get_plugin_manager()

    if not plugin_manager.plugins_dir_exists:
        click.echo(_NOT_INITIALIZED_MSG, err=True)
        ctx.exit(1)
        return

    if plugin_name not in plugin_manager.loaded_plugins:
        failed = plugin_manager.get_failed_plugins()
        if plugin_name in failed:
            click.echo(f"Plugin '{plugin_name}' failed to load: {failed[plugin_name]}")
        else:
            click.echo(f"Plugin not found: {plugin_name}")
        ctx.exit(1)
        return

    plugin = plugin_manager.loaded_plugins[plugin_name]

    click.echo("Plugin Information:")
    click.echo(f"  File: {plugin_manager.plugins_dir / f'{plugin_name}.py'}")
    click.echo(f"  Name: {plugin.name}")
    click.echo(f"  Version: {plugin.version}")
    click.echo(f"  Description: {plugin.description or 'No description provided'}")

    try:
        command = plugin.get_command()
        click.echo(f"  Command: {command.name}")
        if hasattr(command, "commands"):
            subcommands = list(command.commands.keys())
            if subcommands:
                click.echo(f"  Subcommands: {', '.join(subcommands)}")
    except Exception as e:
        click.echo(f"  Command: Error loading command ({e})")


@click.command()
@click.pass_context
def validate(ctx: click.Context) -> None:
    """Validate all plugins in the plugins directory."""
    plugin_manager = _get_plugin_manager()

    if not plugin_manager.plugins_dir_exists:
        click.echo(_NOT_INITIALIZED_MSG, err=True)
        ctx.exit(1)
        return

    loaded = plugin_manager.loaded_plugins
    failed = plugin_manager.get_failed_plugins()

    if not loaded and not failed:
        click.echo(f"No plugins found in {plugin_manager.plugins_dir}")
        return

    all_valid = True

    for plugin_name, plugin in loaded.items():
        try:
            command = plugin.get_command()
            if not isinstance(command, (click.Command, click.Group)):
                raise ValueError("get_command() must return a Click Command or Group")
            click.echo(f"{plugin_name}: Valid")
        except Exception as e:
            click.echo(f"{plugin_name}: {e}")
            all_valid = False

    for plugin_name, error in failed.items():
        click.echo(f"{plugin_name}: {error}")
        all_valid = False

    # Report conflicts recorded at startup
    conflicts = plugin_manager.get_command_conflicts()
    if conflicts:
        click.echo("\nCommand Conflicts Detected:")
        for conflict in conflicts:
            click.echo(f"  Plugin '{conflict['plugin_name']}' command '{conflict['command_name']}' conflicts with core command")
            click.echo("    Solution: Rename the command or use a command group")
        all_valid = False

    click.echo()
    if all_valid:
        click.echo("All plugins are valid!")
    else:
        click.echo("Some plugins have validation errors.")


# Register subcommands
plugins.add_command(init)
plugins.add_command(list_plugins, name="list")
plugins.add_command(info)
plugins.add_command(validate)
