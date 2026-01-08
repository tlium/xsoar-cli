import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import click

from xsoar_cli.utilities import load_config

if TYPE_CHECKING:
    from xsoar_client.xsoar_client import Client


def load_manifest(manifest: str):  # noqa: ANN201
    """Calls json.load() on the manifest and returns a dict."""
    filepath = Path(manifest)
    try:
        return json.load(filepath.open("r"))
    except json.JSONDecodeError:
        msg = f"Failed to decode JSON in {filepath}"
        click.echo(msg)
        sys.exit(1)
    except FileNotFoundError:
        print(f"File not found: {filepath}")
        sys.exit(1)


def write_manifest(manifest: str, data: Any) -> None:  # noqa: ANN401
    """Writes the xsoar_conf.json manifest using json.dumps()"""
    manifest_path = Path(manifest)
    with manifest_path.open("w") as f:
        f.write(json.dumps(data, indent=4))
        f.write("\n")
    click.echo(f"Written updated manifest to '{manifest_path}'")


@click.group()
def manifest() -> None:
    """Various commands to interact/update/deploy content packs defined in the xsoar_config.json manifest."""


@click.option("--environment", default=None, help="Default environment set in config file.")
@click.argument("manifest_path", type=str)
@click.command()
@click.pass_context
@load_config
def generate(ctx: click.Context, environment: str | None, manifest_path: str) -> None:
    """Generate a new xsoar_config.json manifest from installed content packs.

    This command assumes that you do not have any custom content packs uploaded to XSOAR.
    All packs will be added as "marketplace_packs" in the manifest.
    """
    if not environment:
        environment = ctx.obj["default_environment"]
    xsoar_client: Client = ctx.obj["server_envs"][environment]["xsoar_client"]
    installed_packs = xsoar_client.get_installed_packs()
    manifest_data = {
        "marketplace_packs": [],
    }
    for item in installed_packs:
        tmpobj = {
            "id": item["id"],
            "version": item["currentVersion"],
        }
        manifest_data["marketplace_packs"].append(tmpobj)
    write_manifest(manifest_path, manifest_data)


@click.option("--environment", default=None, help="Default environment set in config file.")
@click.argument("manifest", type=str)
@click.command()
@click.pass_context
@load_config
def update(ctx: click.Context, environment: str | None, manifest: str) -> None:
    """Update manifest on disk with latest available content pack versions."""
    if not environment:
        environment = ctx.obj["default_environment"]
    xsoar_client: Client = ctx.obj["server_envs"][environment]["xsoar_client"]
    manifest_data = load_manifest(manifest)
    click.echo("Fetching outdated packs from XSOAR server. This may take a minute...", nl=False)
    results = xsoar_client.get_outdated_packs()
    click.echo("done.")
    if not results:
        click.echo("No packs eligible for upgrade.")
        sys.exit(0)

    item1 = "Pack ID"
    item2 = "Installed version"
    item3 = "Latest available version"
    header = f"{item1:50}{item2:20}{item3:20}"
    click.echo(header)
    for pack in results:
        click.echo(f"{pack['id']:50}{pack['currentVersion']:20}{pack['latest']:20}")
    click.echo(f"Total number of outdated content packs: {len(results)}")

    for pack in results:
        key = "custom_packs" if pack["author"] in ctx.obj["custom_pack_authors"] else "marketplace_packs"
        index = next((i for i, item in enumerate(manifest_data[key]) if item["id"] == pack["id"]), None)
        if index is None:
            msg = f"Pack {pack['id']} not found in manifest."
            click.echo(msg)
            sys.exit(1)
        comment = manifest_data[key][index].get("_comment", None)
        if comment is not None:
            print(f"WARNING: comment found in manifest for {pack['id']}: {comment}")
        msg = f"Upgrade {pack['id']} from {pack['currentVersion']} to {pack['latest']}?"
        should_upgrade = click.confirm(msg, default=True)
        if should_upgrade:
            manifest_data[key][index]["version"] = pack["latest"]
    write_manifest(manifest, manifest_data)


@click.option("--environment", default=None, help="Default environment set in config file.")
@click.option("--mode", type=click.Choice(["full", "diff"]), default="diff", help="Validate the full manifest, or only the definitions that diff with installed versions")
@click.argument("manifest", type=str)
@click.command()
@click.pass_context
@load_config
def validate(ctx: click.Context, environment: str | None, mode: str, manifest: str) -> None:
    """Validate manifest JSON and content pack availability by doing HTTP CONNECT to the appropriate artifacts repository.
    Custom pack availability is implementation dependant."""
    if not environment:
        environment = ctx.obj["default_environment"]
    xsoar_client: Client = ctx.obj["server_envs"][environment]["xsoar_client"]

    manifest_data = load_manifest(manifest)
    click.echo("Manifest is valid JSON")
    keys = ["custom_packs", "marketplace_packs"]


    def found_in_local_filesystem() -> bool:
        # If we are in a merge request and the merge request contains a new pack as well
        # as a updated xsoar_config.json manifest, then the pack is not available in S3
        # before the MR is merged. Check if we can find the appropriate pack version locally
        # If so, we can ignore this error because the pack will become available after merge.
        manifest_arg = Path(manifest)
        manifest_path = manifest_arg.resolve()
        repo_path = manifest_path.parent
        pack_metadata_path = Path(f"{repo_path}/Packs/{pack['id']}/pack_metadata.json")
        with Path.open(pack_metadata_path, encoding="utf-8") as f:
            pack_metadata = json.load(f)
        if pack_metadata["currentVersion"] == pack["version"]:
            return True
        # The relevant Pack locally does not have the requested version.
        return False

    if mode == "full":
        for key in keys:
            custom = key == "custom_packs"
            click.echo(f"Checking {key} availability ", nl=False)
            for pack in manifest_data[key]:
                available = xsoar_client.is_pack_available(pack_id=pack["id"], version=pack["version"], custom=custom)
                # We check if a pack is found in local filesystem regardless of whether it's an upstream pack or not.
                # This should cause any significantly negative performance penalties.
                if not available and not found_in_local_filesystem():
                    click.echo(f"\nFailed to reach pack {pack['id']} version {pack['version']}")
                    sys.exit(1)
                click.echo(".", nl=False)
            print()
        click.echo("Manifest is valid JSON and all packs are reachable")
        return
    elif mode == "diff":
        installed_packs = xsoar_client.get_installed_packs()
        for key in keys:
            found_diff = False
            custom = key == "custom_packs"
            click.echo(f"Checking {key} availability ", nl=False)
            for pack in manifest_data[key]:
                installed = next((item for item in installed_packs if item["id"] == pack["id"]), {})
                if not installed or installed["currentVersion"] != pack["version"]:
                    available = xsoar_client.is_pack_available(pack_id=pack["id"], version=pack["version"], custom=custom)
                    # We check if a pack is found in local filesystem regardless of whether it's an upstream pack or not.
                    # This should cause any significantly negative performance penalties.
                    if not available and not found_in_local_filesystem():
                        click.echo(f"\nFailed to reach pack {pack['id']} version {pack['version']}")
                        sys.exit(1)
                    click.echo(".", nl=False)
                    found_diff = True
            if not found_diff:
                click.echo("- no diff from installed versions found in manifest.")
            else:
                print()

        click.echo("Manifest is valid JSON and all packs are reachable.")
        return
    else:
        msg = "Invalid value for --mode detected. This should never happen"
        raise RuntimeError(msg)


@click.option("--environment", default=None, help="Default environment set in config file.")
@click.argument("manifest", type=str)
@click.command()
@click.pass_context
@load_config
def diff(ctx: click.Context, manifest: str, environment: str | None) -> None:
    """Prints out the differences (if any) between what is defined in the xsoar_config.json manifest and what is actually
    installed on the XSOAR server."""
    if not environment:
        environment = ctx.obj["default_environment"]
    xsoar_client: Client = ctx.obj["server_envs"][environment]["xsoar_client"]
    manifest_data = load_manifest(manifest)
    installed_packs = xsoar_client.get_installed_packs()
    all_good = True
    for key in manifest_data:
        for pack in manifest_data[key]:
            installed = next((item for item in installed_packs if item["id"] == pack["id"]), {})
            if not installed:
                click.echo(f"Pack {pack['id']} is not installed")
                all_good = False
            elif installed["currentVersion"] != pack["version"]:
                msg = f"Manifest states {pack['id']} version {pack['version']} but version {installed['currentVersion']} is installed"
                click.echo(msg)
                all_good = False
    if all_good:
        click.echo("All packs up to date.")


@click.option("--environment", default=None, help="Default environment set in config file.")
@click.option("--verbose", is_flag=True, default=False)
@click.option("--yes", is_flag=True, default=False)
@click.command()
@click.argument("manifest", type=str)
@click.pass_context
@load_config
def deploy(ctx: click.Context, environment: str | None, manifest: str, verbose: bool, yes: bool) -> None:  # noqa: FBT001
    """
    Deploys content packs to the XSOAR server as defined in the xsoar_config.json manifest.
    The PATH argument expects the full or relative path to xsoar_config.json

    \b
    Prompts for confirmation prior to pack installation.
    """
    should_continue = True
    if not yes:
        should_continue = click.confirm(
            f"WARNING: this operation will attempt to deploy all packs defined in the manifest to XSOAR {environment} environment. Continue?",
        )
    if not should_continue:
        ctx.exit()
    if not environment:
        environment = ctx.obj["default_environment"]
    xsoar_client: Client = ctx.obj["server_envs"][environment]["xsoar_client"]
    manifest_data = load_manifest(manifest)
    click.echo("Fetching installed packs...", err=True)
    installed_packs = xsoar_client.get_installed_packs()
    click.echo("done.")
    none_installed = True
    for key in manifest_data:
        custom = key == "custom_packs"
        for pack in manifest_data[key]:
            installed = next((item for item in installed_packs if item["id"] == pack["id"]), {})
            if not installed or installed["currentVersion"] != pack["version"]:
                # Install pack
                click.echo(f"Installing {pack['id']} version {pack['version']}...", nl=False)
                xsoar_client.deploy_pack(pack_id=pack["id"], pack_version=pack["version"], custom=custom)
                click.echo("OK.")
                none_installed = False
            elif verbose:
                click.echo(f"Not installing {pack['id']} version {pack['version']}. Already installed.")
                # Print message that install is skipped

    if none_installed:
        click.echo("No packs to install. All packs and versions in manifest is already installed on XSOAR server.")


manifest.add_command(deploy)
manifest.add_command(diff)
manifest.add_command(update)
manifest.add_command(validate)
manifest.add_command(generate)
