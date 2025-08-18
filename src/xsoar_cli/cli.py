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


@click.group()
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

# Load and register plugins after all core commands are added
plugin_manager = PluginManager()
try:
    plugin_manager.load_all_plugins(ignore_errors=True)
    plugin_manager.register_plugin_commands(cli)
except Exception:
    # Silently ignore plugin loading errors to not break the CLI
    pass
