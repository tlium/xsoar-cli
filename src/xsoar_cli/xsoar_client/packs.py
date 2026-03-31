from __future__ import annotations

import sys
import tempfile
from typing import TYPE_CHECKING

import requests
from demisto_client.demisto_api.rest import ApiException
from packaging import version

from .constants import HTTP_CALL_TIMEOUT, XSOAR_OLD_VERSION

if TYPE_CHECKING:
    from .client import Client


class Packs:
    def __init__(self, client: Client, custom_pack_authors: list[str] | None = None) -> None:
        self.client = client
        self.custom_pack_authors = custom_pack_authors or []
        self.installed_packs: list[dict] | None = None
        self.installed_expired: list[dict] | None = None

    def get_installed(self) -> list[dict]:
        """Fetches a complete list of installed packs."""
        if self.client.server_version > XSOAR_OLD_VERSION:
            endpoint = "/xsoar/public/v1/contentpacks/metadata/installed"
        else:
            endpoint = "/contentpacks/metadata/installed"

        if self.installed_packs is None:
            response = self.client.make_request(endpoint=endpoint, method="GET")
            response.raise_for_status()
            self.installed_packs = response.json()
        return self.installed_packs

    def get_installed_expired(self) -> list[dict]:
        """Fetches a complete list of installed expired packs."""
        if self.client.server_version > XSOAR_OLD_VERSION:
            endpoint = "/xsoar/contentpacks/installed-expired"
        else:
            endpoint = "/contentpacks/installed-expired"

        if self.installed_expired is None:
            response = self.client.make_request(endpoint=endpoint, method="GET")
            response.raise_for_status()
            self.installed_expired = response.json()
        return self.installed_expired

    def is_installed(self, *, pack_id: str = "", pack_version: str = "") -> bool:
        """Checks if a pack (optionally at a specific version) is installed."""
        installed = self.get_installed()
        if not pack_version:
            return any(item for item in installed if item["id"] == pack_id)
        return any(item for item in installed if item["id"] == pack_id and item["currentVersion"] == pack_version)

    def is_available(self, *, pack_id: str, version: str, custom: bool) -> bool:
        """Checks if a pack version is available for download."""
        if custom:
            if not self.client.artifact_provider:
                raise RuntimeError("No artifact provider configured")
            return self.client.artifact_provider.is_available(pack_id=pack_id, pack_version=version)
        baseurl = "https://marketplace.xsoar.paloaltonetworks.com/content/packs"
        path = f"/{pack_id}/{version}/{pack_id}.zip"
        url = baseurl + path
        response = requests.head(url, timeout=self.client.http_timeout)
        if int(response.status_code) != 200:  # noqa: PLR2004, SIM103
            return False
        return True

    def download(self, pack_id: str, pack_version: str, custom: bool) -> bytes:  # noqa: FBT001
        """Downloads a content pack from upstream or the artifacts repository."""
        if custom:
            if not self.client.artifact_provider:
                raise RuntimeError("No artifact provider configured")
            return self.client.artifact_provider.download(pack_id=pack_id, pack_version=pack_version)
        baseurl = "https://marketplace.xsoar.paloaltonetworks.com/content/packs"
        path = f"/{pack_id}/{pack_version}/{pack_id}.zip"
        url = baseurl + path
        response = requests.get(url, timeout=HTTP_CALL_TIMEOUT)
        response.raise_for_status()
        return response.content

    def delete(self, *, pack_id: str = "") -> bool:
        raise NotImplementedError

    def deploy_zip(self, *, filepath: str = "", skip_validation: bool = False, skip_verify: bool = False) -> bool:
        """Uploads a content pack zip file to the server."""
        params = {
            "skip_validation": "true" if skip_validation else "false",
            "skip_verify": "true" if skip_verify else "false",
        }
        self.client.demisto_py_instance.upload_content_packs(filepath, **params)
        return True

    def deploy(self, *, pack_id: str, pack_version: str, custom: bool) -> bool:
        """Downloads and deploys a content pack. Raises RuntimeError on upload failure."""
        params = {}
        filedata = self.download(pack_id=pack_id, pack_version=pack_version, custom=custom)
        if custom:
            params["skip_validation"] = "false"
            params["skip_verify"] = "true"
        else:
            params["skip_validation"] = "false"
            params["skip_verify"] = "false"

        tmp = tempfile.NamedTemporaryFile()  # noqa: SIM115
        with open(tmp.name, "wb") as f:  # noqa: PTH123
            f.write(filedata)

        try:
            self.client.demisto_py_instance.upload_content_packs(tmp.name, **params)
        except ApiException as ex:
            msg = f"Exception when calling DefaulApi->upload_content_packs: {ex!s}\n"
            raise RuntimeError(msg) from ex
        return True

    def get_outdated(self) -> list[dict]:
        """Returns a list of packs that have updates available."""
        expired_packs = self.get_installed_expired()
        update_available = []
        for pack in expired_packs:
            if pack["author"] in self.custom_pack_authors:
                if not self.client.artifact_provider:
                    raise RuntimeError("No artifact provider configured")
                try:
                    latest_version = self.client.artifact_provider.get_latest_version(pack["id"])
                except ValueError:
                    msg = f"WARNING: custom pack {pack['id']} installed on XSOAR server, but cannot find pack in artifacts repo."
                    print(msg, file=sys.stderr)
                    continue
                if latest_version == pack["currentVersion"]:
                    continue
                tmpobj = {
                    "id": pack["id"],
                    "currentVersion": pack["currentVersion"],
                    "latest": latest_version,
                    "author": pack["author"],
                }
                update_available.append(tmpobj)
            elif not pack["updateAvailable"]:
                continue
            else:
                tmpobj = {
                    "id": pack["id"],
                    "currentVersion": pack["currentVersion"],
                    "latest": max(list(pack["changelog"]), key=version.parse),
                    "author": "Upstream",
                }
                update_available.append(tmpobj)

        return update_available

    def get_latest_custom_version(self, pack_id: str) -> str:
        """Gets the latest version of a custom pack from the artifacts repository."""
        if not self.client.artifact_provider:
            raise RuntimeError("No artifact provider configured")
        return self.client.artifact_provider.get_latest_version(pack_id)
