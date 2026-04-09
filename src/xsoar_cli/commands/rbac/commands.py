import json
import logging
from typing import TYPE_CHECKING

import click

from xsoar_cli.utilities.config_file import get_xsoar_config, load_config
from xsoar_cli.utilities.validators import validate_xsoar_connectivity

if TYPE_CHECKING:
    from xsoar_cli.xsoar_client.client import Client

logger = logging.getLogger(__name__)


@click.group()
def rbac() -> None:
    """Dump roles, users and user groups"""
    pass


@click.command()
@click.option("--environment", default=None, help="Default environment set in config file.")
@click.pass_context
@load_config
@validate_xsoar_connectivity
def getroles(ctx: click.Context, environment: str | None) -> None:
    """Dump all roles in your environment."""
    config = get_xsoar_config(ctx)
    xsoar_client: Client = config.get_client(environment)
    roles = xsoar_client.rbac.get_roles()
    click.echo(json.dumps(roles, sort_keys=True, indent=4))


@click.command()
@click.option("--environment", default=None, help="Default environment set in config file.")
@click.pass_context
@load_config
@validate_xsoar_connectivity
def getusers(ctx: click.Context, environment: str | None) -> None:
    """Dump all users in your environment."""
    config = get_xsoar_config(ctx)
    xsoar_client: Client = config.get_client(environment)
    users = xsoar_client.rbac.get_users()
    click.echo(json.dumps(users, sort_keys=True, indent=4))


@click.command()
@click.option("--environment", default=None, help="Default environment set in config file.")
@click.pass_context
@load_config
@validate_xsoar_connectivity
def getusergroups(ctx: click.Context, environment: str | None) -> None:
    """Dump all user groups in your environment. XSOAR 8+ only."""
    config = get_xsoar_config(ctx)
    xsoar_client: Client = config.get_client(environment)
    if xsoar_client.server_version < 8:
        click.echo("Error: Command not supported for XSOAR server versions less than 8")
        ctx.exit(1)
    user_groups = xsoar_client.rbac.get_user_groups()
    click.echo(json.dumps(user_groups, sort_keys=True, indent=4))


rbac.add_command(getroles)
rbac.add_command(getusers)
rbac.add_command(getusergroups)
