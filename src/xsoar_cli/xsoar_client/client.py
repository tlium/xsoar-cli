from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, TypeAlias

import demisto_client
import demisto_client.demisto_api
import requests

from .artifact_providers import BaseArtifactProvider
from .cases import Cases
from .config import ClientConfig
from .constants import HTTP_CALL_TIMEOUT, XSOAR_OLD_VERSION
from .content import Content
from .integrations import Integrations
from .packs import Packs
from .rbac import Rbac

if TYPE_CHECKING:
    from requests.models import Response

JSONType: TypeAlias = dict | list | None


requests.packages.urllib3.disable_warnings()  # ty: ignore[unresolved-attribute]


def _deprecated(new_path: str):
    warnings.warn(
        f"Direct method call is deprecated, use {new_path} instead",
        DeprecationWarning,
        stacklevel=3,
    )


class Client:
    def __init__(
        self,
        *,
        config: ClientConfig,
        artifact_provider: BaseArtifactProvider | None = None,
    ) -> None:
        self.config = config
        self.artifact_provider = artifact_provider
        self.http_timeout = HTTP_CALL_TIMEOUT
        self.demisto_py_instance = demisto_client.configure(
            base_url=self.config.server_url,
            api_key=self.config.api_token,
            auth_id=self.config.xsiam_auth_id,
            verify_ssl=self.config.verify_ssl,
        )

        self.packs = Packs(self)
        self.cases = Cases(self)
        self.content = Content(self)
        self.integrations = Integrations(self)
        self.rbac = Rbac(self)

    def _make_request(
        self,
        *,
        endpoint: str,
        method: str,
        json: JSONType = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
        data: dict | None = None,
    ) -> Response:
        """Wrapper for Requests. Sets the appropriate headers and authentication token."""
        url = f"{self.config.server_url}{endpoint}"
        headers = {
            "Accept": "application/json",
            "Authorization": self.config.api_token,
            "Content-Type": "application/json",
        }
        if self.config.xsiam_auth_id:
            headers["x-xdr-auth-id"] = self.config.xsiam_auth_id
        return requests.request(
            method=method,
            url=url,
            headers=headers,
            json=json,
            files=files,
            data=data,
            verify=self.config.verify_ssl,
            timeout=self.http_timeout,
        )

    def test_connectivity(self) -> bool:
        """Tests connectivity to the XSOAR server."""
        if self.config.server_version > XSOAR_OLD_VERSION:
            endpoint = "/xsoar/workers/status"
        else:
            endpoint = "/workers/status"
        try:
            response = self._make_request(endpoint=endpoint, method="GET")
            response.raise_for_status()
        except Exception as ex:
            msg = "Failed to connect to XSOAR server"
            raise ConnectionError(msg) from ex
        return True

    # -- Deprecated proxy methods for backwards compatibility --

    def get_roles(self) -> str:
        _deprecated("client.rbac.get_roles()")
        return self.rbac.get_roles()

    def get_users(self) -> str:
        _deprecated("client.rbac.get_users()")
        return self.rbac.get_users()

    def get_user_groups(self) -> str:
        _deprecated("client.rbac.get_user_groups()")
        return self.rbac.get_user_groups()

    def get_integrations(self) -> str:
        _deprecated("client.integrations.get_instances()")
        return self.integrations.get_instances()

    def get_case(self, case_id: int) -> dict:
        _deprecated("client.cases.get()")
        return self.cases.get(case_id)

    def create_case(self, data: dict) -> dict:
        _deprecated("client.cases.create()")
        return self.cases.create(data)

    def download_item(self, item_type: str, item_id: str) -> bytes:
        _deprecated("client.content.download_item()")
        return self.content.download_item(item_type, item_id)

    def attach_item(self, item_type: str, item_id: str) -> None:
        _deprecated("client.content.attach_item()")
        self.content.attach_item(item_type, item_id)

    def detach_item(self, item_type: str, item_id: str) -> None:
        _deprecated("client.content.detach_item()")
        self.content.detach_item(item_type, item_id)

    def get_installed_packs(self) -> list[dict]:
        _deprecated("client.packs.get_installed()")
        return self.packs.get_installed()

    def get_installed_expired_packs(self) -> list[dict]:
        _deprecated("client.packs.get_installed_expired()")
        return self.packs.get_installed_expired()

    def is_installed(self, *, pack_id: str = "", pack_version: str = "") -> bool:
        _deprecated("client.packs.is_installed()")
        return self.packs.is_installed(pack_id=pack_id, pack_version=pack_version)

    def is_pack_available(self, *, pack_id: str, version: str, custom: bool) -> bool:
        _deprecated("client.packs.is_available()")
        return self.packs.is_available(pack_id=pack_id, version=version, custom=custom)

    def download_pack(self, pack_id: str, pack_version: str, custom: bool) -> bytes:  # noqa: FBT001
        _deprecated("client.packs.download()")
        return self.packs.download(pack_id, pack_version, custom)

    def deploy_pack(self, *, pack_id: str, pack_version: str, custom: bool) -> bool:
        _deprecated("client.packs.deploy()")
        return self.packs.deploy(pack_id=pack_id, pack_version=pack_version, custom=custom)

    def deploy_zip(self, *, filepath: str = "", skip_validation: bool = False, skip_verify: bool = False) -> bool:
        _deprecated("client.packs.deploy_zip()")
        return self.packs.deploy_zip(filepath=filepath, skip_validation=skip_validation, skip_verify=skip_verify)

    def delete(self, *, pack_id: str = "") -> bool:
        _deprecated("client.packs.delete()")
        return self.packs.delete(pack_id=pack_id)

    def get_outdated_packs(self) -> list[dict]:
        _deprecated("client.packs.get_outdated()")
        return self.packs.get_outdated()

    def get_latest_custom_pack_version(self, pack_id: str) -> str:
        _deprecated("client.packs.get_latest_custom_version()")
        return self.packs.get_latest_custom_version(pack_id)
