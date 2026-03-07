import json
import logging
from typing import TYPE_CHECKING

import click

from xsoar_cli.utilities.config_file import get_xsoar_config, load_config
from xsoar_cli.utilities.validators import validate_xsoar_connectivity

if TYPE_CHECKING:
    from xsoar_client.xsoar_client import Client

logger = logging.getLogger(__name__)


@click.group()
@click.pass_context
def integration(ctx: click.Context) -> None:
    """(BETA) Save/load integration configuration for an integration instance."""


@click.option("--environment", default=None, help="Default environment set in config file.")
@click.option("--flag", is_flag=True, default=False)
@click.command()
@click.argument("name", type=str, required=False, default=None)
@click.pass_context
@load_config
@validate_xsoar_connectivity()
def dump(ctx: click.Context, environment: str | None, name: str | None, all: bool) -> None:
    """Dump integration instance configuration to stdout as JSON."""
    config = get_xsoar_config(ctx)
    xsoar_client: Client = config.get_client(environment)
    logger.debug("Dumping integration config (environment: '%s')", environment or config.default_environment)
    response = xsoar_client.get_integrations()
    integrations = json.loads(response)
    if all:
        logger.debug("Fetching config for all integrations (environment: '%s')", environment or config.default_environment)
        integration_data = integrations
    else:
        logger.debug("Fetching config for integration name '%s'(environment: '%s')", name, environment or config.default_environment)
        integration_data = next((i for i in integrations if i["name"] == name), None)
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
def load(ctx: click.Context, environment: str | None, name: str, instance_name: str) -> None:
    """Load integration instance configuration into XSOAR from a JSON file. Not yet implemented."""
    logger.debug("integration loadconfig command not implemented")
    click.echo("Command not implemented")


integration.add_command(save)
integration.add_command(load)
