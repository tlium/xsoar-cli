"""Manifest comparison helpers.

Functions for comparing installed XSOAR packs against a manifest definition,
used by the manifest CLI commands.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

MANIFEST_KEYS = ["custom_packs", "marketplace_packs"]


def _all_manifest_packs(manifest_data: dict) -> list[dict[str, str]]:
    """Return a flat list of all pack entries across manifest sections."""
    return [pack for key in MANIFEST_KEYS for pack in manifest_data.get(key, [])]


def find_installed_packs_not_in_manifest(
    installed_packs: list[dict[str, str]],
    manifest_data: dict,
) -> list[dict[str, str]]:
    """Find packs that are installed on the XSOAR server but missing manifest definitions."""
    manifest_ids = {pack["id"] for pack in _all_manifest_packs(manifest_data)}
    undefined = []
    for pack in installed_packs:
        if pack["id"] not in manifest_ids:
            undefined.append(pack)
    return undefined


def find_packs_in_manifest_not_installed(
    installed_packs: list[dict[str, str]],
    manifest_data: dict,
) -> list[dict[str, str]]:
    """Find packs defined in the manifest that are not installed on the XSOAR server."""
    installed_ids = {pack["id"] for pack in installed_packs}
    not_installed = []
    for pack in _all_manifest_packs(manifest_data):
        if pack["id"] not in installed_ids:
            not_installed.append(pack)
    return not_installed


def find_version_mismatch(
    installed_packs: list[dict[str, str]],
    manifest_data: dict,
) -> list[dict[str, str]]:
    """Find packs where the installed version differs from the manifest version."""
    installed_by_id = {pack["id"]: pack for pack in installed_packs}
    mismatched = []
    for manifest_pack in _all_manifest_packs(manifest_data):
        installed = installed_by_id.get(manifest_pack["id"])
        if not installed:
            # Packs not installed are handled by find_packs_in_manifest_not_installed
            continue
        if installed["currentVersion"] != manifest_pack["version"]:
            mismatched.append(
                {
                    "id": manifest_pack["id"],
                    "manifest_version": manifest_pack["version"],
                    "installed_version": installed["currentVersion"],
                }
            )
    return mismatched
