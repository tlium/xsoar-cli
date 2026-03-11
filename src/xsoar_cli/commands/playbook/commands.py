import logging
import pathlib
import subprocess
from io import StringIO
from typing import TYPE_CHECKING

import click
import yaml

from xsoar_cli.utilities.config_file import get_xsoar_config, load_config
from xsoar_cli.utilities.validators import validate_xsoar_connectivity

if TYPE_CHECKING:
    from xsoar_client.xsoar_client import Client

logger = logging.getLogger(__name__)


@click.group()
@click.pass_context
def playbook(ctx: click.Context) -> None:
    """Download and manage playbooks"""


@click.command()
@click.option("--environment", default=None, help="Default environment set in config file.")
@click.argument("name", type=str)
@click.pass_context
@load_config
@validate_xsoar_connectivity()
def download(ctx: click.Context, environment: str | None, name: str) -> None:
    """Download and reattach playbook.

    We try to detect output path to $(cwd)/Packs/<Pack ID>/Playbooks/<name>.yml
    Whitespace in Pack ID and playbook filename will be replaced with underscores. After the playbook is downloaded,
    then demisto-sdk format --assume-no --no-validate --no-graph is done on the downloaded playbook before the item
    is re-attached.
    """
    config = get_xsoar_config(ctx)
    xsoar_client: Client = config.get_client(environment)
    logger.info("Downloading playbook '%s' (environment: '%s')", name, environment or config.default_environment)
    # Maybe we should search for the playbook before attempting download in
    # case user specifies a cutsom playbook and not a system playbook
    try:
        click.echo("Downloading playbook...", nl=False)
        playbook = xsoar_client.download_item(item_type="playbook", item_id=name)
        click.echo("ok.")
    except Exception as ex:  # noqa: BLE001
        logger.info("Failed to download playbook '%s': %s", name, ex)
        click.echo(f"FAILED: {ex!s}")
        ctx.exit(1)
    playbook_bytes_data = StringIO(playbook.decode("utf-8"))
    playbook_data = yaml.safe_load(playbook_bytes_data)
    pack_id = playbook_data["contentitemexportablefields"]["contentitemfields"]["packID"]
    logger.debug("Detected pack ID '%s' for playbook '%s'", pack_id, name)
    cwd = pathlib.Path().cwd()
    target_dir = pathlib.Path(cwd / "Packs" / pack_id / "Playbooks")
    if not target_dir.is_dir():
        logger.info("Target directory not found: %s", target_dir)
        msg = f"Cannot find target directory: {target_dir}\nMaybe you're not running xsoar-cli from the root of a content repository?"
        click.echo(msg)
        ctx.exit(1)
    filepath = pathlib.Path(cwd / "Packs" / pack_id / "Playbooks" / f"{playbook_data['id']}.yml")
    filepath = pathlib.Path(str(filepath).replace(" ", "_"))
    with filepath.open("w") as f:
        yaml.dump(playbook_data, f, default_flow_style=False)
    logger.debug("Written playbook YAML to %s", filepath)
    click.echo(f"Written playbook to: {filepath}")
    click.echo("Running demisto-sdk format on newly downloaded playbook")
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
    click.echo("Re-attaching playbook in XSOAR...", nl=False)
    xsoar_client.attach_item(item_type="playbook", item_id=name)
    click.echo("done.")
    logger.info("Playbook '%s' downloaded and re-attached", name)


playbook.add_command(download)
