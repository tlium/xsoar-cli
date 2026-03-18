import json
import logging
from typing import TYPE_CHECKING

import click

from xsoar_cli.utilities.config_file import get_xsoar_config, load_config
from xsoar_cli.utilities.content import filter_content
from xsoar_cli.utilities.validators import validate_xsoar_connectivity

if TYPE_CHECKING:
    from xsoar_client.xsoar_client import Client

logger = logging.getLogger(__name__)


@click.group()
def content() -> None:
    """Inspect and manage content items."""


@click.command()
@click.option("--environment", default=None, help="Default environment set in config file.")
@click.option(
    "--type",
    "content_type",
    type=click.Choice(["scripts", "playbooks", "all"], case_sensitive=False),
    default="all",
    show_default=True,
    help="Type of content items to retrieve.",
)
@click.pass_context
@load_config
@validate_xsoar_connectivity()
def get_detached(ctx: click.Context, environment: str | None, content_type: str) -> None:
    """List detached content items."""
    config = get_xsoar_config(ctx)
    xsoar_client: Client = config.get_client(environment)
    response = xsoar_client.content.get_detached(content_type)
    click.echo(json.dumps(response.json(), indent=4))
    click.echo(f"Getting detached content items ({content_type=})")


@click.command()
@click.option("--environment", default=None, help="Default environment set in config file.")
@click.option(
    "--type",
    "content_type",
    type=click.Choice(["scripts", "playbooks", "commands", "all"], case_sensitive=False),
    default="all",
    show_default=True,
    help="Type of content items to list.",
)
@click.option("--detail", is_flag=True, default=False, help="Include argument-level detail in filtered output.")
@click.option("--verbose", is_flag=True, default=False, help="Output the full unfiltered response.")
@click.pass_context
@load_config
@validate_xsoar_connectivity()
def list(ctx: click.Context, environment: str | None, content_type: str, detail: bool, verbose: bool) -> None:
    """
    List detached content items. The purpose of this function is to list out available commands,
    playbooks and scripts, primarily to facilitate better AI generated playbooks"""
    config = get_xsoar_config(ctx)
    xsoar_client: Client = config.get_client(environment)
    json_blob = xsoar_client.content.list(content_type)
    if verbose:
        click.echo(json.dumps(json_blob, indent=4))
        ctx.exit(0)

    # Individual type calls return a bare list, normalize to dict for filter_content.
    # Note: isinstance(json_blob, list) cannot be used here because the function
    # name "list" shadows the builtin.
    if not isinstance(json_blob, dict):
        json_blob = {content_type: json_blob}

    filtered = filter_content(json_blob, detail=detail)
    click.echo(json.dumps(filtered, indent=4))


content.add_command(get_detached)
content.add_command(list)
