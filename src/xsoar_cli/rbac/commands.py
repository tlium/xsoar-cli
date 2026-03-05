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
def rbac(ctx: click.Context) -> None:
    """Dump roles, users and user groups"""


@click.option("--environment", default=None, help="Default environment set in config file.")
@click.command()
@click.pass_context
@load_config
@validate_xsoar_connectivity()
def getroles(ctx: click.Context, environment: str | None) -> None:
    """Dump all roles in your environment."""
    config = get_xsoar_config(ctx)
    xsoar_client: Client = config.get_client(environment)
    results = xsoar_client.get_roles()
    roles = json.loads(results)
    click.echo(json.dumps(roles, sort_keys=True, indent=4) + "\n")


@click.option("--environment", default=None, help="Default environment set in config file.")
@click.command()
@click.pass_context
@load_config
@validate_xsoar_connectivity()
def getusers(ctx: click.Context, environment: str | None) -> None:
    """Dump all users in your environment."""
    config = get_xsoar_config(ctx)
    xsoar_client: Client = config.get_client(environment)
    results = xsoar_client.get_users()
    users = json.loads(results)
    click.echo(json.dumps(users, sort_keys=True, indent=4) + "\n")

    config = get_xsoar_config(ctx)
    xsoar_client: Client = config.get_client(environment)


@click.option("--environment", default=None, help="Default environment set in config file.")
@click.command()
@click.pass_context
@load_config
@validate_xsoar_connectivity()
def getusergroups(ctx: click.Context, environment: str | None) -> None:
    """Dump all roles in your environment."""
    config = get_xsoar_config(ctx)
    xsoar_client: Client = config.get_client(environment)
    results = xsoar_client.get_user_groups()
    user_groups = json.loads(results)
    click.echo(json.dumps(user_groups, sort_keys=True, indent=4) + "\n")


rbac.add_command(getroles)
rbac.add_command(getusers)
rbac.add_command(getusergroups)
