import logging
from typing import TYPE_CHECKING

import click

from xsoar_cli.utilities import get_xsoar_config, load_config, validate_xsoar_connectivity

if TYPE_CHECKING:
    from xsoar_client.xsoar_client import Client

logger = logging.getLogger(__name__)


@click.group()
@click.pass_context
def integration(ctx: click.Context) -> None:
    """Save/load integration configuration for an integration instance."""


@click.option("--environment", default=None, help="Default environment set in config file.")
@click.command()
@click.argument("name", type=str)
@click.pass_context
@load_config
@validate_xsoar_connectivity()
def dumpconfig(ctx: click.Context, environment: str | None, name: str, instance_name: str) -> None:
    """Dumps integration config to JSON file."""
    config = get_xsoar_config(ctx)
    xsoar_client: Client = config.get_client(environment)
    logger.debug(
        "Dumping integration config for instance name '%s' (environment: '%s')", environment or config.default_environment, instance_name
    )
    click.echo("Placeholder")


@click.option("--environment", default=None, help="Default environment set in config file.")
@click.command()
@click.argument("name", type=str)
@click.pass_context
@load_config
@validate_xsoar_connectivity()
def loadconfig(ctx: click.Context, environment: str | None, name: str, instance_name: str) -> None:
    """Loads integration config from JSON file."""
    config = get_xsoar_config(ctx)
    xsoar_client: Client = config.get_client(environment)
    logger.debug(
        "Loading integration config for instance name '%s' (environment: '%s')", environment or config.default_environment, instance_name
    )
    click.echo("Placeholder")


integration.add_command(dumpconfig)
integration.add_command(loadconfig)
