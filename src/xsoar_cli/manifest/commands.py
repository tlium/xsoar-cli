import json
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import click
from demisto_client.demisto_api.rest import ApiException
from packaging.version import Version

from xsoar_cli.utilities import (
    find_installed_packs_not_in_manifest,
    find_packs_in_manifest_not_installed,
    find_version_mismatch,
    get_xsoar_config,
    load_config,
    validate_artifacts_provider,
    validate_xsoar_connectivity,
)

if TYPE_CHECKING:
    from xsoar_client.xsoar_client import Client

logger = logging.getLogger(__name__)


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
@validate_xsoar_connectivity()
def generate(ctx: click.Context, environment: str | None, manifest_path: str) -> None:
    """Generate a new xsoar_config.json manifest from installed content packs.

    This command assumes that you do not have any custom content packs uploaded to XSOAR.
    All packs will be added as "marketplace_packs" in the manifest.
    """
    config = get_xsoar_config(ctx)
    xsoar_client: Client = config.get_client(environment)
    logger.info("Generating manifest from installed packs (environment: '%s')", environment or config.default_environment)
    installed_packs = xsoar_client.get_installed_packs()
    logger.debug("Fetched %d installed pack(s) from server", len(installed_packs))
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
    logger.info("Generated manifest with %d pack(s) at '%s'", len(manifest_data["marketplace_packs"]), manifest_path)


@click.option("--environment", default=None, help="Default environment set in config file.")
@click.argument("manifest", type=str)
@click.command()
@click.pass_context
@load_config
@validate_artifacts_provider
@validate_xsoar_connectivity()
def update(ctx: click.Context, environment: str | None, manifest: str) -> None:
    """Update manifest on disk with latest available content pack versions."""
    config = get_xsoar_config(ctx)
    xsoar_client: Client = config.get_client(environment)
    logger.info("Updating manifest '%s' (environment: '%s')", manifest, environment or config.default_environment)
    manifest_data = load_manifest(manifest)
    click.echo("Fetching outdated packs from XSOAR server. This may take a minute...")
    outdated_installed_packs = xsoar_client.get_outdated_packs()
    logger.debug("Found %d outdated pack(s) on server", len(outdated_installed_packs))

    changes_made = False
    for key in ["custom_packs", "marketplace_packs"]:
        custom = key == "custom_packs"
        pack_type = "Custom" if custom else "Marketplace"
        for index, manifest_pack in enumerate(manifest_data[key]):
            if custom:
                latest = xsoar_client.artifact_provider.get_latest_version(manifest_pack["id"])  # ty: ignore[unresolved-attribute]
            else:
                pack = next((item for item in outdated_installed_packs if item["id"] == manifest_pack["id"]), None)
                if not pack:
                    # We have a content pack defined in the manifest which isn't installed on the XSOAR server. Ignore
                    # this pack and continue evaluation
                    logger.debug("%s pack '%s' not found in outdated list, skipping", pack_type, manifest_pack["id"])
                    continue
                latest = pack["latest"]
            if Version(latest) == Version(manifest_pack["version"]):
                # No updates for pack if latest matches manifest definition
                logger.debug("%s pack '%s' already at latest version %s", pack_type, manifest_pack["id"], latest)
                continue

            # Check if there is a _comment key for the pack and print comment
            # as warning
            comment = manifest_data[key][index].get("_comment", None)
            if comment is not None:
                print(f"WARNING: comment found in manifest for {manifest_pack['id']}: {comment}")

            # Prompt user if pack should be upgraded
            logger.debug("%s pack '%s': update available from %s to %s", pack_type, manifest_pack["id"], manifest_pack["version"], latest)
            msg = f"Upgrade {manifest_pack['id']} from {manifest_pack['version']} to {latest}?"
            should_upgrade = click.confirm(msg, default=True)
            if should_upgrade:
                logger.debug(
                    "User accepted upgrade of %s pack '%s' from %s to %s",
                    pack_type.lower(),
                    manifest_pack["id"],
                    manifest_pack["version"],
                    latest,
                )
                manifest_data[key][index]["version"] = latest
                changes_made = True
            else:
                logger.debug(
                    "User declined upgrade of %s pack '%s' (staying at %s)",
                    pack_type.lower(),
                    manifest_pack["id"],
                    manifest_pack["version"],
                )

    if not changes_made:
        logger.info("No manifest changes made during update")
        click.echo("No changes made to manifest or no content packs applicable for update.")
    else:
        write_manifest(manifest, manifest_data)
        logger.info("Manifest '%s' updated with new pack versions", manifest)


@click.option("--environment", default=None, help="Default environment set in config file.")
@click.option(
    "--mode",
    type=click.Choice(["full", "diff"]),
    default="diff",
    help="Validate the full manifest, or only the definitions that diff with installed versions",
)
@click.argument("manifest", type=str)
@click.command()
@click.pass_context
@load_config
@validate_artifacts_provider
@validate_xsoar_connectivity()
def validate(ctx: click.Context, environment: str | None, mode: str, manifest: str) -> None:
    """Validate manifest JSON and content pack availability by doing HTTP CONNECT to the appropriate artifacts repository.
    Custom pack availability is implementation dependant."""
    config = get_xsoar_config(ctx)
    xsoar_client: Client = config.get_client(environment)
    logger.info("Validating manifest '%s' in '%s' mode (environment: '%s')", manifest, mode, environment or config.default_environment)

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
        if not pack_metadata_path.is_file():
            return False
        with Path.open(pack_metadata_path, encoding="utf-8") as f:
            pack_metadata = json.load(f)
        if pack_metadata["currentVersion"] == pack["version"]:
            return True
        # The relevant Pack locally does not have the requested version.
        return False

    # Validate json keys. The manifest entries should only contain "id", "version" or "_comment"
    found_invalid_entry = False
    for key in keys:
        for index, pack in enumerate(manifest_data[key]):
            for k, v in pack.items():
                if k not in ["id", "version", "_comment"]:
                    logger.error("Manifest data contains invalid key. %s should only contain keys %s", pack, ["id", "version", "_comment"])
                    errmsg = f"The following manifest entry contains an invalid key:\n{json.dumps(pack, indent=4)}\n"
                    click.echo(f"ERROR: {errmsg}")
                    found_invalid_entry = True

    if found_invalid_entry:
        click.echo('Valid keys are "id", "version", "_comment"')
        ctx.exit(1)
    sys.exit(0)
    if mode == "full":
        for key in keys:
            custom = key == "custom_packs"
            pack_type = "Custom" if custom else "Marketplace"
            click.echo(f"Checking {key} availability ", nl=False)
            for pack in manifest_data[key]:
                available = xsoar_client.is_pack_available(pack_id=pack["id"], version=pack["version"], custom=custom)
                # We check if a pack is found in local filesystem regardless of whether it's an upstream pack or not.
                # This should cause any significantly negative performance penalties.
                if not available:
                    if custom and found_in_local_filesystem():
                        logger.debug("%s pack '%s' %s not in artifacts but found locally, skipping", pack_type, pack["id"], pack["version"])
                        continue
                    logger.info("Validation failed: %s pack '%s' version %s not reachable", pack_type.lower(), pack["id"], pack["version"])
                    click.echo(f"\nFailed to reach find {pack['id']} version {pack['version']}")
                    sys.exit(1)
                click.echo(".", nl=False)
            print()
        logger.info("Full validation passed for manifest '%s'", manifest)
        click.echo("Manifest is valid JSON and all packs are reachable")
        return
    elif mode == "diff":
        installed_packs = xsoar_client.get_installed_packs()
        for key in keys:
            found_diff = False
            custom = key == "custom_packs"
            pack_type = "Custom" if custom else "Marketplace"
            click.echo(f"Checking {key} availability ", nl=False)
            for pack in manifest_data[key]:
                installed = next((item for item in installed_packs if item["id"] == pack["id"]), {})
                if not installed or installed["currentVersion"] != pack["version"]:
                    available = xsoar_client.is_pack_available(pack_id=pack["id"], version=pack["version"], custom=custom)
                    # We check if a pack is found in local filesystem regardless of whether it's an upstream pack or not.
                    # This should cause any significantly negative performance penalties.
                    if not available:
                        if custom and found_in_local_filesystem():
                            logger.debug(
                                "%s pack '%s' %s not in artifacts but found locally, skipping", pack_type, pack["id"], pack["version"]
                            )
                            continue
                        logger.info(
                            "Validation failed: %s pack '%s' version %s not reachable", pack_type.lower(), pack["id"], pack["version"]
                        )
                        click.echo(f"\nFailed to find pack {pack['id']} version {pack['version']}")
                        sys.exit(1)
                    click.echo(".", nl=False)
                    found_diff = True
            if not found_diff:
                click.echo("- no diff from installed versions found in manifest.")
            else:
                print()

        logger.info("Diff validation passed for manifest '%s'", manifest)
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
@validate_xsoar_connectivity()
def diff(ctx: click.Context, manifest: str, environment: str | None) -> None:
    """Prints out the differences (if any) between what is defined in the xsoar_config.json manifest and what is actually
    installed on the XSOAR server."""
    config = get_xsoar_config(ctx)
    xsoar_client: Client = config.get_client(environment)
    logger.info("Computing manifest diff for '%s' (environment: '%s')", manifest, environment or config.default_environment)
    manifest_data = load_manifest(manifest)
    installed_packs = xsoar_client.get_installed_packs()
    logger.debug("Fetched %d installed pack(s) from server", len(installed_packs))
    # Detect install content packs not defined in manifest
    # Find content packs defined in manifest but that are not defined
    # Find installed content packs that are outdated
    results = {}
    results["undefined_in_manifest"] = find_installed_packs_not_in_manifest(installed_packs, manifest_data)
    # print(f'{results["undefined_in_manifest"]=}')
    results["not_installed"] = find_packs_in_manifest_not_installed(installed_packs, manifest_data)
    # print(f'{results["not_installed"]=}')
    results["mismatch"] = find_version_mismatch(installed_packs, manifest_data)
    # print(f'{results["mismatch"]=}')
    logger.debug(
        "Diff results: %d undefined in manifest, %d not installed, %d version mismatch",
        len(results["undefined_in_manifest"]),
        len(results["not_installed"]),
        len(results["mismatch"]),
    )
    found_diff = False
    for key in results:
        if results[key]:
            found_diff = True

    if not found_diff:
        logger.info("No differences found between manifest and server")
        click.echo("All packs up to date.")
        ctx.exit(0)

    # Example output string:
    #
    # Installed packs missing manifest definition:
    #  - AnsibleTower version 1.1.6
    #  - CDC_Databricks version 2.0.0
    #  - CDC_Testing version 1.0.15
    #
    #  Packs where install version does not match manifest definition:
    #    - Base version 1.41.60 installed when version 1.41.58 defined in manifest

    msg = ""
    if results["undefined_in_manifest"]:
        msg += "Installed packs missing manifest definition:\n"
        for item in results["undefined_in_manifest"]:
            msg += f"  - {item['id']} version {item['currentVersion']}\n"
        msg += "\n"

    if results["not_installed"]:
        msg += "Packs not installed but defined in manifest:\n"
        for item in results["not_installed"]:
            msg += f"  - {item['id']} version {item['version']}\n"
        msg += "\n\n"

    if results["mismatch"]:
        msg += "Packs where install version does not match manifest definition:\n"
        for item in results["mismatch"]:
            # mpobj = {pack["id"]: {"manifest version": pack["version"], "installed version": installed["currentVersion"]}}
            msg += f"  - {item['id']} version {item['installed_version']} installed when version {item['manifest_version']} defined in manifest\n"

    click.echo(msg)


@click.option("--environment", default=None, help="Default environment set in config file.")
@click.option("--verbose", is_flag=True, default=False)
@click.option("--yes", is_flag=True, default=False)
@click.command()
@click.argument("manifest", type=str)
@click.pass_context
@load_config
@validate_artifacts_provider
@validate_xsoar_connectivity()
def deploy(ctx: click.Context, environment: str | None, manifest: str, verbose: bool, yes: bool) -> None:  # noqa: FBT001
    """
    Deploys content packs to the XSOAR server as defined in the xsoar_config.json manifest.
    The PATH argument expects the full or relative path to xsoar_config.json

    \b
    Prompts for confirmation prior to pack installation.
    """
    # Initialize client and determine target environment
    config = get_xsoar_config(ctx)
    xsoar_client: Client = config.get_client(environment)
    active_env = environment or config.default_environment
    logger.info("Deploying manifest '%s' to environment '%s'", manifest, active_env)

    # Prompt for confirmation unless --yes flag is provided
    should_continue = True
    if not yes:
        should_continue = click.confirm(
            f"WARNING: this operation will attempt to deploy all packs defined in the manifest to XSOAR {active_env} environment. Continue?",
        )
    if not should_continue:
        ctx.exit()

    # Load manifest and fetch currently installed packs from server
    manifest_data = load_manifest(manifest)
    click.echo("Fetching installed packs...", err=True)
    installed_packs = xsoar_client.get_installed_packs()
    click.echo("done.")

    # Process both custom and marketplace packs
    installed_any = False
    for key in ["custom_packs", "marketplace_packs"]:
        custom = key == "custom_packs"
        pack_type = "Custom" if custom else "Marketplace"
        logger.debug("Processing %s packs from manifest", pack_type.lower())
        for pack in manifest_data[key]:
            # Check if pack needs installation (missing or version mismatch)
            installed = next((item for item in installed_packs if item["id"] == pack["id"]), {})
            if not installed or installed["currentVersion"] != pack["version"]:
                logger.debug("Deploying %s pack '%s' version %s", pack_type.lower(), pack["id"], pack["version"])
                click.echo(f"Installing {pack['id']} version {pack['version']}...", nl=False)
                try:
                    xsoar_client.deploy_pack(pack_id=pack["id"], pack_version=pack["version"], custom=custom)
                except RuntimeError as ex:
                    logger.info("Failed to deploy %s pack '%s' version %s: %s", pack_type.lower(), pack["id"], pack["version"], ex)
                    click.echo("FAILED")
                    # Extract and format the original API exception
                    original_exception = ex.__cause__

                    if isinstance(original_exception, ApiException) and original_exception.body:
                        try:
                            error_body = json.loads(original_exception.body)
                            error_message = error_body.get("error", "Unknown error")
                            click.echo(f"ERROR: {error_message}")
                        except json.JSONDecodeError:
                            # Body exists but isn't valid JSON
                            click.echo(str(original_exception))
                    else:
                        # Not an ApiException or no body available
                        click.echo(str(original_exception))
                    ctx.exit(1)
                else:
                    logger.debug("Successfully deployed %s pack '%s' version %s", pack_type.lower(), pack["id"], pack["version"])
                    click.echo("OK.")
                    installed_any = True
            elif verbose:
                logger.debug("%s pack '%s' version %s already installed, skipping", pack_type, pack["id"], pack["version"])
                click.echo(f"Not installing {pack['id']} version {pack['version']}. Already installed.")

    if not installed_any:
        logger.info("Deploy complete: no packs required installation")
        click.echo("No packs to install. All packs and versions in manifest is already installed on XSOAR server.")
    else:
        logger.info("Deploy complete for manifest '%s' to environment '%s'", manifest, active_env)


manifest.add_command(deploy)
manifest.add_command(diff)
manifest.add_command(update)
manifest.add_command(validate)
manifest.add_command(generate)
