import json
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
    """(BETA) Save/load integration configuration for an integration instance."""


@click.option("--environment", default=None, help="Default environment set in config file.")
@click.command()
@click.argument("name", type=str)
@click.pass_context
@load_config
@validate_xsoar_connectivity()
def dumpconfig(ctx: click.Context, environment: str | None, name: str | None) -> None:
    """Dump integration instance configuration to stdout as JSON."""
    config = get_xsoar_config(ctx)
    xsoar_client: Client = config.get_client(environment)
    logger.debug("Dumping integration config (environment: '%s')", environment or config.default_environment)
    response = xsoar_client.get_integrations()
    integrations = json.loads(response)
    integration_data = next((i for i in integrations if i["name"] == name), None)
    logger.debug("Fetching config for integration name '%s'(environment: '%s')", name, environment or config.default_environment)
    if not integration_data:
        click.echo(f"Cannot find integration instance '{name}'")
        ctx.exit(1)
    click.echo(json.dumps(integration_data, sort_keys=True, indent=4) + "\n")


@click.option("--environment", default=None, help="Default environment set in config file.")
@click.command()
@click.argument("name", type=str)
@click.pass_context
@load_config
@validate_xsoar_connectivity()
def loadconfig(ctx: click.Context, environment: str | None, name: str, instance_name: str) -> None:
    """Load integration instance configuration from a JSON file. Not yet implemented."""
    logger.debug("integration loadconfig command not implemented")
    click.echo("Command not implemented")


integration.add_command(dumpconfig)
integration.add_command(loadconfig)
