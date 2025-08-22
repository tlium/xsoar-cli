import sys
from typing import TYPE_CHECKING

import click

from xsoar_cli.utilities import load_config

if TYPE_CHECKING:
    from xsoar_client.xsoar_client import Client


@click.group()
@click.pass_context
def pack(ctx: click.Context) -> None:
    """Various content pack related commands."""


@click.option("--environment", default=None, help="Default environment set in config file.")
@click.command()
@click.argument("pack_id", type=str)
@click.pass_context
@load_config
def delete(ctx: click.Context, environment: str | None, pack_id: str) -> None:
    """Deletes a content pack from the XSOAR server."""
    if not environment:
        environment = ctx.obj["default_environment"]
    xsoar_client: Client = ctx.obj["server_envs"][environment]["xsoar_client"]
    if not xsoar_client.is_installed(pack_id=pack_id):
        click.echo(f"Pack ID {pack_id} is not installed. Cannot delete.")
        sys.exit(1)
    xsoar_client.delete(pack_id=pack_id)
    click.echo(f"Deleted pack {pack_id} from XSOAR {environment}")


@click.option("--environment", default=None, help="Default environment set in config file.")
@click.command()
@click.pass_context
@load_config
def get_outdated(ctx: click.Context, environment: str | None) -> None:
    """Prints out a list of outdated content packs."""
    if not environment:
        environment = ctx.obj["default_environment"]
    xsoar_client: Client = ctx.obj["server_envs"][environment]["xsoar_client"]
    click.echo("Fetching outdated packs. This may take a little while...", err=True)
    outdated_packs = xsoar_client.get_outdated_packs()
    if not outdated_packs:
        click.echo("No outdated packs found")
        sys.exit(0)
    id_header = "Pack ID"
    installed_header = "Installed version"
    latest_header = "Latest version"
    click.echo(f"{id_header:<50}{installed_header:>17}{latest_header:>17}")
    for pack in outdated_packs:
        msg = f"{pack['id']:<50}{pack['currentVersion']:>17}{pack['latest']:>17}"
        click.echo(msg)


pack.add_command(delete)
pack.add_command(get_outdated)
