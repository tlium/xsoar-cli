import logging

import click

from .__about__ import __version__
from .case import commands as case_commands
from .config import commands as config_commands
from .graph import commands as graph_commands
from .manifest import commands as manifest_commands
from .pack import commands as pack_commands
from .playbook import commands as playbook_commands
from .plugins import commands as plugin_commands
from .plugins.manager import PluginManager


class XSOARCliGroup(click.Group):
    def resolve_command(self, ctx: click.Context, args: list) -> tuple:
        try:
            return super().resolve_command(ctx, args)
        except click.UsageError:
            failed = plugin_manager.get_failed_plugins()
            if failed:
                names = ", ".join(failed.keys())
                raise click.ClickException(f"Command not found. The following plugins failed to load: {names}")
            raise


@click.group(cls=XSOARCliGroup)
@click.pass_context
@click.version_option(__version__)
@click.option("--debug", is_flag=True, help="Enable debug logging")
def cli(ctx: click.Context, debug: bool) -> None:
    """XSOAR CLI - Command line interface for XSOAR operations."""
    if debug:
        logging.basicConfig(level=logging.DEBUG)


cli.add_command(config_commands.config)
cli.add_command(case_commands.case)
cli.add_command(pack_commands.pack)
cli.add_command(manifest_commands.manifest)
cli.add_command(playbook_commands.playbook)
cli.add_command(graph_commands.graph)
cli.add_command(plugin_commands.plugins)

# Capture core command names before any plugins are registered
CORE_COMMANDS = list(cli.commands.keys())

# Load and register plugins after all core commands are added
plugin_manager = PluginManager()
try:
    plugin_manager.load_all_plugins(ignore_errors=True)
    for plugin_name, error in plugin_manager.get_failed_plugins().items():
        click.echo(f"Warning: plugin '{plugin_name}' failed to load: {error}", err=True)
    plugin_manager.register_plugin_commands(cli)
except Exception as e:
    click.echo(f"Warning: failed to register plugin commands: {e}", err=True)
