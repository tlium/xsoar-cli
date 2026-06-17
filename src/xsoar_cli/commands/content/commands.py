import logging
import pathlib
import subprocess
from typing import TYPE_CHECKING

import click

from xsoar_cli.utilities.config_file import get_xsoar_config, load_config
from xsoar_cli.utilities.content import filter_content, format_detached_summary
from xsoar_cli.utilities.download_content_handlers import HANDLERS, resolve_output_path
from xsoar_cli.utilities.output import OUTPUT_FORMATS, format_content_output
from xsoar_cli.utilities.validators import validate_xsoar_connectivity

if TYPE_CHECKING:
    from xsoar_cli.xsoar_client.client import Client

logger = logging.getLogger(__name__)


@click.group()
def content() -> None:
    """Inspect and manage content items"""
    pass


@click.command()
@click.option("--environment", default=None, help="Default environment set in config file.")
@click.option(
    "--type",
    "content_type",
    type=click.Choice(["scripts", "playbooks", "all"], case_sensitive=False),
    required=True,
    help="Type of content items to retrieve.",
)
@click.pass_context
@load_config
@validate_xsoar_connectivity
def get_detached(ctx: click.Context, environment: str | None, content_type: str) -> None:
    """List detached content items."""
    config = get_xsoar_config(ctx)
    xsoar_client: Client = config.get_client(environment)

    types = ["scripts", "playbooks"] if content_type == "all" else [content_type]
    sections = []
    for t in types:
        items = xsoar_client.content.get_detached(t)
        sections.append(format_detached_summary(items, t))
    click.echo("\n\n".join(sections))


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
@click.option(
    "--output-format",
    type=click.Choice(OUTPUT_FORMATS, case_sensitive=False),
    default="table",
    show_default=True,
    help="Output format. Use 'json' for machine-readable output.",
)
@click.pass_context
@load_config
@validate_xsoar_connectivity
def list_content(ctx: click.Context, environment: str | None, content_type: str, output_format: str) -> None:
    """
    List available content items. Enumerates commands, playbooks and scripts
    available on the server, primarily to facilitate better AI generated
    playbooks."""
    config = get_xsoar_config(ctx)
    xsoar_client: Client = config.get_client(environment)
    json_blob = xsoar_client.content.list(content_type)

    # Individual type calls return a bare list, normalize to dict for filter_content.
    if isinstance(json_blob, list):
        json_blob = {content_type: json_blob}

    filtered = filter_content(json_blob)
    click.echo(format_content_output(filtered, output_format=output_format))


@click.command()
@click.option("--environment", default=None, help="Default environment set in config file.")
@click.option(
    "--type",
    "content_type",
    type=click.Choice(sorted(HANDLERS.keys()), case_sensitive=False),
    required=True,
    help="Type of content item to download.",
)
@click.option(
    "--output",
    "output_path",
    default=None,
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    help="Path to the content repository root. Defaults to current working directory.",
)
@click.argument("name", type=str)
@click.pass_context
@load_config
@validate_xsoar_connectivity
def download(ctx: click.Context, environment: str | None, content_type: str, output_path: str | None, name: str) -> None:
    """Download a content item by name.

    Attempts to write the downloaded item into the appropriate content pack
    directory under Packs/<pack_id>/. If the target directory does not exist,
    offers to save to the current working directory instead. If the target file
    does not already exist, prompts for confirmation before writing.

    Use --output to specify the content repository root when running outside of it.
    """
    config = get_xsoar_config(ctx)
    xsoar_client: Client = config.get_client(environment)
    handler = HANDLERS[content_type]

    logger.info("Downloading %s '%s' (environment: '%s')", content_type, name, environment or config.default_environment)
    try:
        click.echo(f"Downloading {content_type} '{name}'...", nl=False)
        data = handler.download(xsoar_client, name)
        click.echo("ok.")
    except Exception as ex:  # noqa: BLE001
        click.echo("FAILED.")
        logger.info("Failed to download %s '%s': %s", content_type, name, ex)
        click.echo(f"Error: {ex}")
        ctx.exit(1)
        return

    pack_id = handler.extract_pack_id(data)
    filename = handler.build_filename(name)
    base_path = pathlib.Path(output_path) if output_path else None

    filepath = resolve_output_path(pack_id, handler.subdir, filename, cwd=base_path)
    if filepath is None:
        click.echo("Download discarded.")
        return

    handler.write(filepath, data)
    logger.debug("Written %s to %s", content_type, filepath)
    click.echo(f"Written to: {filepath}")

    if handler.reattach_after_download:
        click.echo(f"Re-attaching {content_type} '{name}'...", nl=False)
        logger.debug("Re-attaching %s '%s'", content_type, name)
        try:
            xsoar_client.content.attach_item(handler.item_type, name)
            click.echo("ok.")
        except Exception as ex:  # noqa: BLE001
            click.echo("FAILED.")
            logger.warning("Failed to re-attach %s '%s': %s", content_type, name, ex)
            click.echo(f"Warning: re-attach failed: {ex}")

    if handler.format_after_download:
        click.echo("Running demisto-sdk format...")
        logger.debug("Running demisto-sdk format on %s", filepath)
        subprocess.run(
            [
                "demisto-sdk",
                "format",
                "--assume-no",
                "--no-validate",
                "--no-graph",
                "--from-version",
                "6.10.0",
                str(filepath),
            ],
            check=False,
        )  # noqa: S603, S607


content.add_command(get_detached)
content.add_command(list_content)
content.add_command(download)
