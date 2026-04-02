from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import click

from xsoar_cli.utilities.config_file import get_xsoar_config, load_config
from xsoar_cli.utilities.manifest import (
    MANIFEST_KEYS,
    find_installed_packs_not_in_manifest,
    find_packs_in_manifest_not_installed,
    find_version_mismatch,
)
from xsoar_cli.utilities.validators import validate_artifacts_provider, validate_xsoar_connectivity

if TYPE_CHECKING:
    from xsoar_cli.xsoar_client.client import Client

logger = logging.getLogger(__name__)


def load_manifest(manifest: str) -> dict:
    """Load and parse a manifest JSON file. Raises click.ClickException on failure."""
    filepath = Path(manifest)
    try:
        with filepath.open() as f:
            return json.load(f)
    except json.JSONDecodeError:
        raise click.ClickException(f"Failed to decode JSON in {filepath}")
    except FileNotFoundError:
        raise click.ClickException(f"File not found: {filepath}")


def write_manifest(manifest: str, data: Any) -> None:  # noqa: ANN401
    """Writes the xsoar_conf.json manifest using json.dumps()"""
    manifest_path = Path(manifest)
    with manifest_path.open("w") as f:
        f.write(json.dumps(data, indent=4))
        f.write("\n")
    click.echo(f"Written updated manifest to '{manifest_path}'")


def _pack_found_locally(pack_id: str, pack_version: str, manifest_path: str) -> bool:
    """Check if a pack with the given version exists in the local filesystem.

    During a merge request the manifest may reference a new pack that is not yet
    available in the artifact repository. If the pack exists locally with the
    correct version, validation can safely skip the remote availability check.
    """
    repo_path = Path(manifest_path).resolve().parent
    metadata_path = repo_path / "Packs" / pack_id / "pack_metadata.json"
    if not metadata_path.is_file():
        return False
    with metadata_path.open(encoding="utf-8") as f:
        pack_metadata = json.load(f)
    return pack_metadata["currentVersion"] == pack_version


def _validate_manifest_keys(manifest_data: dict) -> list[dict]:
    """Return manifest entries that contain invalid keys.

    Valid keys are "id", "version", and "_comment".
    """
    valid_keys = {"id", "version", "_comment"}
    invalid_entries = []
    for key in MANIFEST_KEYS:
        for pack in manifest_data[key]:
            if not set(pack.keys()).issubset(valid_keys):
                invalid_entries.append(pack)
    return invalid_entries


def _check_pack_availability(
    xsoar_client: Client,
    packs: list[dict[str, str]],
    *,
    custom: bool,
    manifest_path: str,
) -> None:
    """Verify that each pack is reachable in the artifact repository.

    Falls back to a local filesystem check for custom packs. Raises
    click.ClickException if any pack is not available.
    """
    pack_type = "Custom" if custom else "Marketplace"
    for pack in packs:
        available = xsoar_client.packs.is_available(
            pack_id=pack["id"],
            version=pack["version"],
            custom=custom,
        )
        if available:
            click.echo(".", nl=False)
            continue
        if custom and _pack_found_locally(pack["id"], pack["version"], manifest_path):
            logger.debug(
                "%s pack '%s' %s not in artifacts but found locally, skipping",
                pack_type,
                pack["id"],
                pack["version"],
            )
            continue
        logger.info(
            "Validation failed: %s pack '%s' version %s not reachable",
            pack_type.lower(),
            pack["id"],
            pack["version"],
        )
        raise click.ClickException(f"Failed to find {pack['id']} version {pack['version']}")
    click.echo()


@click.group()
def manifest() -> None:
    """Various commands to interact/update/deploy content packs defined in the xsoar_config.json manifest."""


@click.command()
@click.option("--environment", default=None, help="Default environment set in config file.")
@click.argument("manifest_path", type=str)
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
    installed_packs = xsoar_client.packs.get_installed()
    logger.debug("Fetched %d installed pack(s) from server", len(installed_packs))
    manifest_data = {
        "marketplace_packs": [],
    }
    for item in installed_packs:
        manifest_data["marketplace_packs"].append(
            {
                "id": item["id"],
                "version": item["currentVersion"],
            }
        )
    write_manifest(manifest_path, manifest_data)
    logger.info("Generated manifest with %d pack(s) at '%s'", len(manifest_data["marketplace_packs"]), manifest_path)


@click.command()
@click.option("--environment", default=None, help="Default environment set in config file.")
@click.argument("manifest", type=str)
@click.pass_context
@load_config
@validate_artifacts_provider
@validate_xsoar_connectivity()
def update(ctx: click.Context, environment: str | None, manifest: str) -> None:
    """Update manifest on disk with latest available content pack versions."""
    # Lazy import for performance reasons
    from packaging.version import Version

    config = get_xsoar_config(ctx)
    xsoar_client: Client = config.get_client(environment)
    logger.info("Updating manifest '%s' (environment: '%s')", manifest, environment or config.default_environment)
    manifest_data = load_manifest(manifest)
    click.echo("Fetching outdated packs from XSOAR server. This may take a minute...")
    result = xsoar_client.packs.get_outdated()
    outdated_installed_packs = result.outdated
    logger.debug("Found %d outdated pack(s) on server", len(outdated_installed_packs))
    if result.skipped:
        logger.info("Skipped %d custom pack(s) not found in artifacts repo", len(result.skipped))
        click.echo(f"Warning: {len(result.skipped)} custom pack(s) installed but not found in artifacts repo:", err=True)
        for pack_id in result.skipped:
            click.echo(f"  - {pack_id}", err=True)

    changes_made = False
    for key in MANIFEST_KEYS:
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
                click.echo(f"WARNING: comment found in manifest for {manifest_pack['id']}: {comment}")

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


@click.command()
@click.option("--environment", default=None, help="Default environment set in config file.")
@click.option(
    "--mode",
    type=click.Choice(["full", "diff"]),
    default="diff",
    help="Validate the full manifest, or only the definitions that diff with installed versions",
)
@click.argument("manifest", type=str)
@click.pass_context
@load_config
@validate_artifacts_provider
@validate_xsoar_connectivity()
def validate(ctx: click.Context, environment: str | None, mode: str, manifest: str) -> None:
    """Validate manifest JSON and content pack availability.

    Custom pack availability is implementation dependent."""
    config = get_xsoar_config(ctx)
    xsoar_client: Client = config.get_client(environment)
    logger.info("Validating manifest '%s' in '%s' mode (environment: '%s')", manifest, mode, environment or config.default_environment)

    manifest_data = load_manifest(manifest)
    click.echo("Manifest is valid JSON")

    invalid_entries = _validate_manifest_keys(manifest_data)
    if invalid_entries:
        for entry in invalid_entries:
            logger.error("Manifest entry contains invalid key: %s", entry)
            click.echo(f"ERROR: The following manifest entry contains an invalid key:\n{json.dumps(entry, indent=4)}\n")
        click.echo('Valid keys are "id", "version", "_comment"')
        ctx.exit(1)

    if mode == "full":
        for key in MANIFEST_KEYS:
            custom = key == "custom_packs"
            click.echo(f"Checking {key} availability ", nl=False)
            _check_pack_availability(
                xsoar_client,
                manifest_data[key],
                custom=custom,
                manifest_path=manifest,
            )
        logger.info("Full validation passed for manifest '%s'", manifest)
        click.echo("Manifest is valid JSON and all packs are reachable")
    elif mode == "diff":
        installed_packs = xsoar_client.packs.get_installed()
        installed_by_id = {pack["id"]: pack for pack in installed_packs}
        for key in MANIFEST_KEYS:
            custom = key == "custom_packs"
            packs_to_check = []
            for pack in manifest_data[key]:
                installed = installed_by_id.get(pack["id"])
                if not installed or installed["currentVersion"] != pack["version"]:
                    packs_to_check.append(pack)
            click.echo(f"Checking {key} availability ", nl=False)
            if not packs_to_check:
                click.echo("- no diff from installed versions found in manifest.")
            else:
                _check_pack_availability(
                    xsoar_client,
                    packs_to_check,
                    custom=custom,
                    manifest_path=manifest,
                )
        logger.info("Diff validation passed for manifest '%s'", manifest)
        click.echo("Manifest is valid JSON and all packs are reachable.")
    else:
        msg = "Invalid value for --mode detected. This should never happen"
        raise RuntimeError(msg)


@click.command()
@click.option("--environment", default=None, help="Default environment set in config file.")
@click.argument("manifest", type=str)
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
    installed_packs = xsoar_client.packs.get_installed()
    logger.debug("Fetched %d installed pack(s) from server", len(installed_packs))
    results = {}
    results["undefined_in_manifest"] = find_installed_packs_not_in_manifest(installed_packs, manifest_data)
    results["not_installed"] = find_packs_in_manifest_not_installed(installed_packs, manifest_data)
    results["mismatch"] = find_version_mismatch(installed_packs, manifest_data)
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
            msg += f"  - {item['id']} version {item['installed_version']} installed when version {item['manifest_version']} defined in manifest\n"

    click.echo(msg)


@click.command()
@click.option("--environment", default=None, help="Default environment set in config file.")
@click.option("--verbose", is_flag=True, default=False)
@click.option("--yes", is_flag=True, default=False)
@click.argument("manifest", type=str)
@click.pass_context
@load_config
@validate_artifacts_provider
@validate_xsoar_connectivity()
def deploy(ctx: click.Context, environment: str | None, manifest: str, verbose: bool, yes: bool) -> None:  # noqa: FBT001
    """Deploy content packs to the server as defined in the xsoar_config.json manifest.

    The MANIFEST argument expects the full or relative path to xsoar_config.json.

    \b
    Prompts for confirmation prior to pack installation.
    """
    # Lazy import for performance reasons
    from demisto_client.demisto_api.rest import ApiException

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
    installed_packs = xsoar_client.packs.get_installed()
    click.echo("done.")

    # Process both custom and marketplace packs
    installed_any = False
    for key in MANIFEST_KEYS:
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
                    xsoar_client.packs.deploy(pack_id=pack["id"], pack_version=pack["version"], custom=custom)
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
