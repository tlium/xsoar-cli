import json
import logging
import pathlib
from typing import TYPE_CHECKING

import click

from xsoar_cli.utilities.config_file import get_xsoar_config, load_config
from xsoar_cli.utilities.content import filter_content
from xsoar_cli.utilities.validators import validate_xsoar_connectivity

if TYPE_CHECKING:
    from xsoar_cli.xsoar_client.client import Client

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


# We name the command in the decorator here to avoid shadowing the builtin list.
@click.command("list")
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
def list_content(ctx: click.Context, environment: str | None, content_type: str, detail: bool, verbose: bool) -> None:
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
    if isinstance(json_blob, list):
        json_blob = {content_type: json_blob}

    filtered = filter_content(json_blob, detail=detail)
    click.echo(json.dumps(filtered, indent=4))


@click.command()
@click.option("--environment", default=None, help="Default environment set in config file.")
@click.option(
    "--type",
    "content_type",
    type=click.Choice(["playbook", "layout"], case_sensitive=False),
    required=True,
    help="Type of content item to download.",
)
@click.argument("name", type=str)
@click.pass_context
@load_config
@validate_xsoar_connectivity()
def download(ctx: click.Context, environment: str | None, content_type: str, name: str) -> None:
    """Download a content item by name."""
    config = get_xsoar_config(ctx)
    xsoar_client: Client = config.get_client(environment)

    if content_type == "playbook":
        logger.info("Downloading playbook '%s' (environment: '%s')", name, environment or config.default_environment)
        try:
            click.echo(f"Downloading playbook '{name}'...", nl=False)
            data = xsoar_client.content.download_playbook(name)
            click.echo("ok.")
        except Exception as ex:  # noqa: BLE001
            click.echo("FAILED.")
            logger.info("Failed to download playbook '%s': %s", name, ex)
            click.echo(f"Error: {ex}")
            ctx.exit(1)
            return

        filename = f"{name.replace(' ', '_')}.yml"
        filepath = pathlib.Path.cwd() / filename
        filepath.write_bytes(data)
        logger.debug("Written playbook YAML to %s", filepath)
        click.echo(f"Written to: {filepath}")

    elif content_type == "layout":
        logger.info("Downloading layout '%s' (environment: '%s')", name, environment or config.default_environment)
        try:
            click.echo(f"Downloading layout '{name}'...", nl=False)
            data = xsoar_client.content.download_layout(name)
            click.echo("ok.")
        except Exception as ex:  # noqa: BLE001
            click.echo("FAILED.")
            logger.info("Failed to download layout '%s': %s", name, ex)
            click.echo(f"Error: {ex}")
            ctx.exit(1)
            return

        filename = f"{name.replace(' ', '_')}.json"
        filepath = pathlib.Path.cwd() / filename
        filepath.write_text(json.dumps(data, indent=4))
        logger.debug("Written layout JSON to %s", filepath)
        click.echo(f"Written to: {filepath}")


content.add_command(get_detached)
content.add_command(list_content)
content.add_command(download)
