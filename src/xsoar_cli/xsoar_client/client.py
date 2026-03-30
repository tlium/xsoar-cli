from __future__ import annotations

from typing import TYPE_CHECKING, TypeAlias

import demisto_client
import demisto_client.demisto_api
import requests

from .artifact_providers.base import BaseArtifactProvider
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
