"""
Plugin management commands for XSOAR CLI

This module provides CLI commands for managing plugins, including
listing, loading, reloading, and creating example plugins.
"""

import logging

import click

from .manager import PluginManager

logger = logging.getLogger(__name__)


@click.group(help="Manage XSOAR CLI plugins")
def plugins():
    """Plugin management commands."""


@click.command(help="List all available and loaded plugins")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
@click.pass_context
def list_plugins(ctx: click.Context, verbose: bool):
    """List all plugins in the plugins directory."""
    plugin_manager = PluginManager()

    # Discover all plugins
    discovered = plugin_manager.discover_plugins()

    # Load all plugins to get their info
    plugin_manager.load_all_plugins(ignore_errors=True)

    loaded_info = plugin_manager.get_plugin_info()
    failed_info = plugin_manager.get_failed_plugins()

    if not discovered:
        return

    click.echo(f"Plugins directory: {plugin_manager.plugins_dir}")
    click.echo(f"Discovered {len(discovered)} plugin files\n")

    # Show loaded plugins
    if loaded_info:
        click.echo("Loaded Plugins:")
        for plugin_name, info in loaded_info.items():
            if verbose:
                click.echo(f"  {plugin_name}")
                click.echo(f"    Name: {info['name']}")
                click.echo(f"    Version: {info['version']}")
                click.echo(f"    Description: {info['description']}")
            else:
                click.echo(f"  {plugin_name} (v{info['version']})")
        click.echo()

    # Show failed plugins
    if failed_info:
        click.echo("Failed Plugins:")
        for plugin_name, error in failed_info.items():
            if verbose:
                click.echo(f"  {plugin_name}: {error}")
            else:
                click.echo(f"  {plugin_name}")
        click.echo()

    # Show unloaded plugins (discovered but not loaded and not failed)
    unloaded = set(discovered) - set(loaded_info.keys()) - set(failed_info.keys())
    if unloaded:
        click.echo("Unloaded Plugins:")
        for plugin_name in unloaded:
            click.echo(f"  {plugin_name}")

    # Show command conflicts
    conflicts = plugin_manager.get_command_conflicts()
    if conflicts:
        click.echo()
        click.echo("Command Conflicts:")
        for conflict in conflicts:
            click.echo(f"  Plugin '{conflict['plugin_name']}' command '{conflict['command_name']}' conflicts with core command")
            click.echo(f"    Plugin version: {conflict['plugin_version']}")
            click.echo("    Solution: Rename the command in your plugin or use a command group")


@click.command(help="Reload a specific plugin")
@click.argument("plugin_name", type=str)
def reload(plugin_name: str):
    """Reload a specific plugin."""
    plugin_manager = PluginManager()

    try:
        click.echo(f"Reloading plugin: {plugin_name}...")
        plugin = plugin_manager.reload_plugin(plugin_name)

        if plugin:
            click.echo(f"Successfully reloaded plugin: {plugin_name}")
            click.echo(f"   Name: {plugin.name}")
            click.echo(f"   Version: {plugin.version}")
        else:
            click.echo(f"Failed to reload plugin: {plugin_name}")

    except Exception as e:
        click.echo(f"Error reloading plugin {plugin_name}: {e}")


@click.command(help="Show information about a specific plugin")
@click.argument("plugin_name", type=str)
def info(plugin_name: str):
    """Show detailed information about a plugin."""
    plugin_manager = PluginManager()

    try:
        plugin = plugin_manager.load_plugin(plugin_name)

        if plugin:
            click.echo("Plugin Information:")
            click.echo(f"  File: {plugin_manager.plugins_dir / plugin_name}.py")
            click.echo(f"  Name: {plugin.name}")
            click.echo(f"  Version: {plugin.version}")
            click.echo(f"  Description: {plugin.description or 'No description provided'}")

            # Try to get command info
            try:
                command = plugin.get_command()
                click.echo(f"  Command: {command.name}")
                if hasattr(command, "commands"):
                    subcommands = list(command.commands.keys())
                    if subcommands:
                        click.echo(f"  Subcommands: {', '.join(subcommands)}")
            except Exception as e:
                click.echo(f"  Command: Error loading command ({e})")
        else:
            click.echo(f"Plugin not found or failed to load: {plugin_name}")

    except Exception as e:
        click.echo(f"Error loading plugin {plugin_name}: {e}")


@click.command(help="Validate all plugins")
def validate():
    """Validate all plugins in the plugins directory."""
    plugin_manager = PluginManager()

    discovered = plugin_manager.discover_plugins()

    if not discovered:
        click.echo(f"No plugins found in {plugin_manager.plugins_dir}")
        return

    click.echo(f"Validating {len(discovered)} plugins...\n")

    all_valid = True

    for plugin_name in discovered:
        try:
            plugin = plugin_manager.load_plugin(plugin_name)
            if plugin:
                # Test that the plugin can provide a command
                command = plugin.get_command()
                if not isinstance(command, (click.Command, click.Group)):
                    raise ValueError("get_command() must return a Click Command or Group")

                click.echo(f"{plugin_name}: Valid")
            else:
                click.echo(f"{plugin_name}: Failed to load")
                all_valid = False

        except Exception as e:
            click.echo(f"{plugin_name}: {e}")
            all_valid = False

    # Check for command conflicts by attempting registration
    try:
        from xsoar_cli.cli import cli

        temp_plugin_manager = PluginManager()
        temp_plugin_manager.load_all_plugins(ignore_errors=True)
        temp_plugin_manager.register_plugin_commands(cli)

        conflicts = temp_plugin_manager.get_command_conflicts()
        if conflicts:
            click.echo("\nCommand Conflicts Detected:")
            for conflict in conflicts:
                click.echo(f"  Plugin '{conflict['plugin_name']}' command '{conflict['command_name']}' conflicts with core command")
                click.echo("    Solution: Rename the command or use a command group")
            all_valid = False
    except Exception as e:
        click.echo(f"\nCould not check for command conflicts: {e}")

    click.echo()
    if all_valid:
        click.echo("All plugins are valid!")
    else:
        click.echo("Some plugins have validation errors.")


@click.command(help="Open the plugins directory")
def open_dir():
    """Open the plugins directory in the system file manager."""
    plugin_manager = PluginManager()
    plugins_dir = plugin_manager.plugins_dir

    click.echo(f"Plugins directory: {plugins_dir}")

    # Try to open the directory
    import subprocess
    import sys

    try:
        if sys.platform == "win32":
            subprocess.run(["explorer", str(plugins_dir)], check=True)
        elif sys.platform == "darwin":
            subprocess.run(["open", str(plugins_dir)], check=True)
        else:
            subprocess.run(["xdg-open", str(plugins_dir)], check=True)

        click.echo("Opened plugins directory in file manager.")

    except (subprocess.CalledProcessError, FileNotFoundError):
        click.echo("Could not open directory automatically.")
        click.echo(f"Please navigate to: {plugins_dir}")


# Add all commands to the plugins group
@click.command(help="Check for command conflicts with core CLI")
def check_conflicts():
    """Check for command conflicts between plugins and core CLI."""
    plugin_manager = PluginManager()

    # Load all plugins
    plugin_manager.load_all_plugins(ignore_errors=True)

    # Check conflicts by attempting registration with a temporary CLI group
    import click

    temp_cli = click.Group()

    # Add core commands to temp CLI to simulate real conflicts
    core_commands = ["case", "config", "graph", "manifest", "pack", "playbook", "plugins"]
    for cmd_name in core_commands:
        temp_cli.add_command(click.Command(cmd_name, callback=lambda: None))

    # Attempt to register plugin commands
    plugin_manager.register_plugin_commands(temp_cli)

    conflicts = plugin_manager.get_command_conflicts()

    if not conflicts:
        click.echo("No command conflicts detected!")
        click.echo("All plugin commands have unique names.")
        return

    click.echo(f"Found {len(conflicts)} command conflict(s):")
    click.echo()

    for conflict in conflicts:
        click.echo(f"Plugin: {conflict['plugin_name']} (v{conflict['plugin_version']})")
        click.echo(f"   Command: '{conflict['command_name']}'")
        click.echo("   Conflicts with: Core CLI command")
        click.echo()

    click.echo("Solutions:")
    click.echo("  Rename the conflicting command in your plugin")
    click.echo("  Use a command group to namespace your commands")
    click.echo("  Example: Instead of 'case', use 'mycase' or 'myplugin case'")


plugins.add_command(list_plugins, name="list")
plugins.add_command(reload)
plugins.add_command(info)
plugins.add_command(validate)
plugins.add_command(check_conflicts, name="check-conflicts")
plugins.add_command(open_dir, name="open")
