import logging
import logging.handlers
import sys

import click

from .__about__ import __version__
from .case import commands as case_commands
from .config import commands as config_commands
from .graph import commands as graph_commands
from .log import LoggingSetup, setup_logging
from .manifest import commands as manifest_commands
from .pack import commands as pack_commands
from .playbook import commands as playbook_commands
from .plugins import commands as plugin_commands
from .plugins.manager import PluginManager
from .utilities import get_config_file_contents, get_config_file_path


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
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.DEBUG)
        stream_handler.setFormatter(logging.Formatter("%(name)s %(levelname)s %(message)s"))
        _setup.logger.addHandler(stream_handler)
        _setup.handler.setLevel(logging.DEBUG)


def _register_commands() -> None:
    cli.add_command(config_commands.config)
    cli.add_command(case_commands.case)
    cli.add_command(pack_commands.pack)
    cli.add_command(manifest_commands.manifest)
    cli.add_command(playbook_commands.playbook)
    cli.add_command(graph_commands.graph)
    cli.add_command(plugin_commands.plugins)


def _load_plugins() -> tuple[list[str], PluginManager]:
    """Captures core command names, then loads and registers plugins. Returns both."""
    core_commands = list(cli.commands.keys())
    manager = PluginManager()
    try:
        manager.load_all_plugins(ignore_errors=True)
        for plugin_name, error in manager.get_failed_plugins().items():
            click.echo(f"Warning: plugin '{plugin_name}' failed to load: {error}", err=True)
        manager.register_plugin_commands(cli)
    except Exception as e:
        click.echo(f"Warning: failed to register plugin commands: {e}", err=True)
    return core_commands, manager


def _configure_logging() -> LoggingSetup:
    """Sets up logging, applies log_level from config if present, and logs the invocation."""
    setup = setup_logging()
    config_file = get_config_file_path()
    if config_file.is_file():
        config_data = get_config_file_contents(config_file)
        if "log_level" in config_data:
            log_level_str = config_data["log_level"]
            if log_level_str not in ("DEBUG", "INFO"):
                click.echo(f"Error: invalid log_level '{log_level_str}' in config file. Valid values are: DEBUG, INFO", err=True)
                sys.exit(1)
            setup.handler.setLevel(getattr(logging, log_level_str))
    setup.logger.info("Executing: %s", " ".join(sys.argv[1:]))
    return setup


_register_commands()
CORE_COMMANDS, plugin_manager = _load_plugins()
_setup = _configure_logging()


def main() -> None:
    """Entry point that wraps cli() to capture and log the exit code."""
    try:
        cli()
    except SystemExit as e:
        exit_code = e.code if e.code is not None else 0
        # Remove any StreamHandlers added by --debug before logging the exit line.
        # The exit line belongs in the file only, and cli() has already returned
        # so the StreamHandler has served its purpose.
        for h in list(_setup.logger.handlers):
            if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.handlers.RotatingFileHandler):
                _setup.logger.removeHandler(h)
        _setup.logger.info("Exit: %s", exit_code)
        raise
