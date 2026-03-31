from __future__ import annotations

from typing import TYPE_CHECKING, TypeAlias

import demisto_client
import demisto_client.demisto_api
import requests

from .artifact_providers.base import BaseArtifactProvider
from .cases import Cases
from .constants import HTTP_CALL_TIMEOUT, XSOAR_OLD_VERSION
from .content import Content
from .integrations import Integrations
from .packs import Packs
from .rbac import Rbac

if TYPE_CHECKING:
    from requests.models import Response

JSONType: TypeAlias = dict | list | None


requests.packages.urllib3.disable_warnings()  # ty: ignore[unresolved-attribute]


class Client:
    def __init__(
        self,
        *,
        server_url: str,
        api_token: str,
        server_version: int,
        xsiam_auth_id: str = "",
        verify_ssl: bool | str = False,
        custom_pack_authors: list[str] | None = None,
        artifact_provider: BaseArtifactProvider | None = None,
    ) -> None:
        self.server_url = server_url
        self.api_token = api_token
        self.server_version = server_version
        self.xsiam_auth_id = xsiam_auth_id
        self.verify_ssl = verify_ssl
        self.artifact_provider = artifact_provider
        self.http_timeout = HTTP_CALL_TIMEOUT
        self.demisto_py_instance = demisto_client.configure(
            base_url=self.server_url,
            api_key=self.api_token,
            auth_id=self.xsiam_auth_id,
            verify_ssl=self.verify_ssl,
        )

        self.packs = Packs(self, custom_pack_authors=custom_pack_authors)
        self.cases = Cases(self)
        self.content = Content(self)
        self.integrations = Integrations(self)
        self.rbac = Rbac(self)

    def make_request(
        self,
        *,
        endpoint: str,
        method: str,
        json: JSONType = None,
    ) -> Response:
        """Wrapper for Requests. Sets the appropriate headers and authentication token."""
        url = f"{self.server_url}{endpoint}"
        headers = {
            "Accept": "application/json",
            "Authorization": self.api_token,
            "Content-Type": "application/json",
        }
        if self.xsiam_auth_id:
            headers["x-xdr-auth-id"] = self.xsiam_auth_id
        return requests.request(
            method=method,
            url=url,
            headers=headers,
            json=json,
            verify=self.verify_ssl,
            timeout=self.http_timeout,
        )

    def test_connectivity(self) -> bool:
        """Tests connectivity to the XSOAR server."""
        endpoint = self.resolve_endpoint(v6="/workers/status", v8="/xsoar/workers/status")
        try:
            response = self.make_request(endpoint=endpoint, method="GET")
            response.raise_for_status()
        except Exception as ex:
            msg = "Failed to connect to XSOAR server"
            raise ConnectionError(msg) from ex
        return True

    def resolve_endpoint(self, *, v6: str, v8: str) -> str:
        """Return the appropriate endpoint for the server version. Avoid using if/else statements throughout xsoar-client subclasses."""
        if self.server_version > XSOAR_OLD_VERSION:
            return v8
        return v6
