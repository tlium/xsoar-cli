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
@click.pass_context
def rbac(ctx: click.Context) -> None:
    """Dump roles, users and user groups"""


@click.command()
@click.option("--environment", default=None, help="Default environment set in config file.")
@click.pass_context
@load_config
@validate_xsoar_connectivity()
def getroles(ctx: click.Context, environment: str | None) -> None:
    """Dump all roles in your environment."""
    config = get_xsoar_config(ctx)
    xsoar_client: Client = config.get_client(environment)
    results = xsoar_client.rbac.get_roles()
    roles = json.loads(results)
    click.echo(json.dumps(roles, sort_keys=True, indent=4) + "\n")


@click.command()
@click.option("--environment", default=None, help="Default environment set in config file.")
@click.pass_context
@load_config
@validate_xsoar_connectivity()
def getusers(ctx: click.Context, environment: str | None) -> None:
    """Dump all users in your environment."""
    config = get_xsoar_config(ctx)
    xsoar_client: Client = config.get_client(environment)
    results = xsoar_client.rbac.get_users()
    users = json.loads(results)
    click.echo(json.dumps(users, sort_keys=True, indent=4) + "\n")


@click.command()
@click.option("--environment", default=None, help="Default environment set in config file.")
@click.pass_context
@load_config
@validate_xsoar_connectivity()
def getusergroups(ctx: click.Context, environment: str | None) -> None:
    """Dump all user groups in your environment. XSOAR 8+ only."""
    config = get_xsoar_config(ctx)
    xsoar_client: Client = config.get_client(environment)
    if xsoar_client.server_version < 8:
        click.echo("Error: Command not supported for XSOAR server versions less than 8")
        ctx.exit(1)
    results = xsoar_client.rbac.get_user_groups()
    user_groups = json.loads(results)
    click.echo(json.dumps(user_groups, sort_keys=True, indent=4) + "\n")


rbac.add_command(getroles)
rbac.add_command(getusers)
rbac.add_command(getusergroups)
