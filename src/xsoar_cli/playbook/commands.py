import pathlib
import subprocess
import sys
from io import StringIO
from typing import TYPE_CHECKING

import click
import yaml

from xsoar_cli.utilities import load_config

if TYPE_CHECKING:
    from xsoar_client.xsoar_client import Client


@click.group()
@click.pass_context
def playbook(ctx: click.Context) -> None:
    """Download/attach/detach playbooks"""


@click.option(
    "--environment", default=None, help="Default environment set in config file."
)
@click.command()
@click.argument("name", type=str)
@click.pass_context
@load_config
def download(ctx: click.Context, environment: str | None, name: str) -> None:
    """Download and reattach playbook.

    We try to detect output path to $(cwd)/Packs/<Pack ID>/Playbooks/<name>.yml
    Whitespace in Pack ID and playbook filename will be replaced with underscores. After the playbook is downloaded,
    then demisto-sdk format --assume-yes --no-validate --no-graph is done on the downloaded playbook before the item
    is re-attached in XSOAR.
    """
    if not environment:
        environment = ctx.obj["default_environment"]
    xsoar_client: Client = ctx.obj["server_envs"][environment]["xsoar_client"]
    # Maybe we should search for the playbook before attempting download in
    # case user specifies a cutsom playbook and not a system playbook
    try:
        click.echo("Downloading playbook...", nl=False)
        playbook = xsoar_client.download_item(item_type="playbook", item_id=name)
        click.echo("ok.")
    except Exception as ex:  # noqa: BLE001
        click.echo(f"FAILED: {ex!s}")
        sys.exit(1)
    playbook_bytes_data = StringIO(playbook.decode("utf-8"))
    playbook_data = yaml.safe_load(playbook_bytes_data)
    pack_id = playbook_data["contentitemexportablefields"]["contentitemfields"][
        "packID"
    ]
    cwd = pathlib.Path().cwd()
    target_dir = pathlib.Path(cwd / "Packs" / pack_id / "Playbooks")
    if not target_dir.is_dir():
        msg = f"Cannot find target directory: {target_dir}\nMaybe you're not running xsoar-cli from the root of a content repository?"
        click.echo(msg)
        sys.exit(1)
    filepath = pathlib.Path(
        cwd / "Packs" / pack_id / "Playbooks" / f"{playbook_data['id']}.yml"
    )
    filepath = pathlib.Path(str(filepath).replace(" ", "_"))
    with filepath.open("w") as f:
        yaml.dump(playbook_data, f, default_flow_style=False)
    click.echo(f"Written playbook to: {filepath}")
    click.echo("Running demisto-sdk format on newly downloaded playbook")
    subprocess.run(
        [
            "demisto-sdk",
            "format",
            "--assume-yes",
            "--no-validate",
            "--no-graph",
            str(filepath),
        ],
        check=False,
    )  # noqa: S603, S607
    click.echo("Re-attaching playbook in XSOAR...", nl=False)
    xsoar_client.attach_item(item_type="playbook", item_id=name)
    click.echo("done.")


playbook.add_command(download)
