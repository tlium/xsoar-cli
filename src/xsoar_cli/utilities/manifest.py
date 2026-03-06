def find_installed_packs_not_in_manifest(installed_packs, manifest_data) -> list[dict[str, str]]:
    """Find packs that are installed on the XSOAR server but missing manifest definitions."""
    undefined_packs = []
    for pack in installed_packs:
        for key in manifest_data:
            installed = next((item for item in manifest_data[key] if item["id"] == pack["id"]), {})
            if installed:
                break
        if not installed:
            undefined_packs.append(pack)
    return undefined_packs


def find_packs_in_manifest_not_installed(installed_packs, manifest_data):
    """Find packs defined in the manifest that are not installed on the XSOAR server."""
    not_installed = []
    for key in manifest_data:
        for pack in manifest_data[key]:
            installed = next((item for item in installed_packs if item["id"] == pack["id"]), {})
            if not installed:
                not_installed.append(pack)
    return not_installed


def find_version_mismatch(installed_packs, manifest_data):
    """Find packs where the version installed in XSOAR differs from the version defined in the manifest."""
    outdated = []
    for key in manifest_data:
        for pack in manifest_data[key]:
            installed = next((item for item in installed_packs if item["id"] == pack["id"]), {})
            if not installed:
                # We don't care about packs that are not installed here. That use case is handled
                # in a separate function
                continue
            if installed["currentVersion"] != pack["version"]:
                tmpobj = {"id": pack["id"], "manifest_version": pack["version"], "installed_version": installed["currentVersion"]}
                outdated.append(tmpobj)
    return outdated
