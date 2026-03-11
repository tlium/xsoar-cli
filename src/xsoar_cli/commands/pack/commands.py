import logging
from typing import TYPE_CHECKING

import click

from xsoar_cli.utilities.config_file import get_xsoar_config, load_config
from xsoar_cli.utilities.validators import validate_artifacts_provider, validate_xsoar_connectivity

if TYPE_CHECKING:
    from xsoar_client.xsoar_client import Client

logger = logging.getLogger(__name__)


@click.group()
@click.pass_context
def pack(ctx: click.Context) -> None:
    """Various content pack related commands."""


@click.command()
@click.option("--environment", default=None, help="Default environment set in config file.")
@click.argument("pack_id", type=str)
@click.pass_context
@load_config
@validate_xsoar_connectivity()
def delete(ctx: click.Context, environment: str | None, pack_id: str) -> None:
    """Delete a content pack from the server."""
    config = get_xsoar_config(ctx)
    active_env = environment or config.default_environment
    logger.info("Deleting pack '%s' from environment '%s'", pack_id, active_env)
    xsoar_client: Client = config.get_client(environment)
    if not xsoar_client.is_installed(pack_id=pack_id):
        logger.info("Pack '%s' is not installed on '%s', aborting delete", pack_id, active_env)
        click.echo(f"Pack ID {pack_id} is not installed. Cannot delete.")
        ctx.exit(1)
    logger.debug("Pack '%s' confirmed installed, proceeding with deletion", pack_id)
    xsoar_client.delete(pack_id=pack_id)
    logger.info("Successfully deleted pack '%s' from environment '%s'", pack_id, active_env)
    click.echo(f"Deleted pack {pack_id} from XSOAR {active_env}")


@click.command()
@click.option("--environment", default=None, help="Default environment set in config file.")
@click.pass_context
@load_config
@validate_artifacts_provider
@validate_xsoar_connectivity()
def get_outdated(ctx: click.Context, environment: str | None) -> None:
    """Print a list of outdated content packs."""
    config = get_xsoar_config(ctx)
    active_env = environment or config.default_environment
    logger.info("Fetching outdated packs (environment: '%s')", active_env)
    xsoar_client: Client = config.get_client(environment)
    click.echo("Fetching outdated packs. This may take a little while...", err=True)
    outdated_packs = xsoar_client.get_outdated_packs()
    logger.debug("Found %d outdated pack(s)", len(outdated_packs))
    if not outdated_packs:
        logger.info("No outdated packs found on '%s'", active_env)
        click.echo("No outdated packs found")
        return
    id_header = "Pack ID"
    installed_header = "Installed"
    latest_header = "Latest"
    click.echo(f"{id_header:<52}{installed_header:>14}{latest_header:>14}")
    for pack in outdated_packs:
        msg = f"{pack['id']:<52}{pack['currentVersion']:>14}{pack['latest']:>14}"
        click.echo(msg)


pack.add_command(delete)
pack.add_command(get_outdated)
