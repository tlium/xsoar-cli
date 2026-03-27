# CLI entry point and module initialization.
#
# Initialization order matters here. Command registration and plugin loading
# happen at module level so that the CLI group is fully populated before any
# invocation. Logging setup is intentionally deferred to main() so that
# importing this module (e.g. from tests) does not create a RotatingFileHandler
# on the real log file or write "Executing:" entries for test invocations.

import logging
import logging.handlers
import sys

import click

from .commands.case import commands as case_commands
from .commands.config import commands as config_commands
from .commands.content import commands as content_commands
from .commands.graph import commands as graph_commands
from .commands.integration import commands as integration_commands
from .commands.manifest import commands as manifest_commands
from .commands.pack import commands as pack_commands
from .commands.playbook import commands as playbook_commands
from .commands.plugins import commands as plugin_commands
from .commands.rbac import commands as rbac_commands
from .log import LoggingSetup, setup_logging
from .plugins.manager import PluginManager
from .utilities.config_file import get_config_file_contents, get_config_file_path
from .utilities.generic import check_for_update


class XSOARCliGroup(click.Group):
    """Custom Click group that surfaces plugin load failures when a command is not found.

    Without this, a failed plugin silently disappears and the user gets a generic
    "No such command" error with no indication that a plugin was involved.
    """

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
@click.version_option(package_name="xsoar-cli")
@click.option("--debug", is_flag=True, help="Enable debug logging")
def cli(ctx: click.Context, debug: bool) -> None:
    """XSOAR CLI - Command line interface for XSOAR operations."""
    # _setup is None when cli() is invoked directly (e.g. from tests via
    # CliRunner) rather than through main(). In that case logging is not
    # configured and --debug is a no-op.
    if debug and _setup is not None:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.DEBUG)
        stream_handler.setFormatter(logging.Formatter("%(name)s %(levelname)s %(message)s"))
        _setup.logger.addHandler(stream_handler)
        _setup.handler.setLevel(logging.DEBUG)


def _register_commands() -> None:
    cli.add_command(config_commands.config)
    cli.add_command(case_commands.case)
    cli.add_command(content_commands.content)
    cli.add_command(pack_commands.pack)
    cli.add_command(integration_commands.integration)
    cli.add_command(manifest_commands.manifest)
    cli.add_command(playbook_commands.playbook)
    cli.add_command(graph_commands.graph)
    cli.add_command(plugin_commands.plugins)
    cli.add_command(rbac_commands.rbac)


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


# Module-level initialization: register core commands and load plugins so the
# CLI group is fully assembled before any invocation. Logging is NOT set up
# here -- see main(). Deferring it prevents test imports from opening a file
# handler against the real log file and writing unwanted "Executing:" /
# "Exit:" entries for pytest invocations.
_register_commands()
CORE_COMMANDS, plugin_manager = _load_plugins()

# Initialized in main(). None when the module is imported without calling main(),
# which is the case during test runs.
_setup: LoggingSetup | None = None


def main() -> None:
    """Entry point (pyproject.toml console_scripts). Sets up logging, invokes
    the CLI, and ensures the exit code is logged before the process exits."""
    # Start by setting up logging facilitites
    global _setup  # noqa: PLW0603
    _setup = _configure_logging()
    # Check for updates to xsoar-cli
    try:
        config_file = get_config_file_path()
        skip_version_check = True
        if config_file.is_file():
            config_data = get_config_file_contents(config_file)
            skip_version_check = config_data.get("skip_version_check", True)
        update_message = check_for_update(skip_version_check=skip_version_check)
        if update_message:
            click.echo(update_message, err=True)
    except Exception:
        # Ignore errors during update check (network issues, missing metadata, etc.)
        pass
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
