"""Unit tests for the Client core (``xsoar_cli.xsoar_client.client``).

Tests mock ``demisto_client.configure`` (called during ``__init__``) and
``requests.request`` (called by ``make_request``) to verify header building,
endpoint resolution, and connectivity checking.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from requests.exceptions import ConnectionError as RequestsConnectionError

from xsoar_cli.xsoar_client.constants import XSOAR_OLD_VERSION

# ---------------------------------------------------------------------------
# Helper to build a Client with demisto_client.configure mocked out
# ---------------------------------------------------------------------------


def _make_client(**overrides):  # noqa: ANN003, ANN201
    from xsoar_cli.xsoar_client.client import Client

    defaults = {
        "server_url": "https://xsoar.example.com",
        "api_token": "test-api-token",
        "server_version": 6,
    }
    defaults.update(overrides)
    with patch("xsoar_cli.xsoar_client.client.demisto_client.configure"):
        return Client(**defaults)


# ===========================================================================
# Client.resolve_endpoint
# ===========================================================================


class TestResolveEndpoint:
    def test_returns_v6_for_version_6(self) -> None:
        client = _make_client(server_version=6)
        result = client.resolve_endpoint(v6="/users", v8="/rbac/get_users")
        assert result == "/users"

    def test_returns_v6_for_version_below_threshold(self) -> None:
        client = _make_client(server_version=5)
        result = client.resolve_endpoint(v6="/users", v8="/rbac/get_users")
        assert result == "/users"

    def test_returns_v8_for_version_above_threshold(self) -> None:
        client = _make_client(server_version=8)
        result = client.resolve_endpoint(v6="/users", v8="/rbac/get_users")
        assert result == "/rbac/get_users"

    def test_returns_v8_for_version_7(self) -> None:
        client = _make_client(server_version=XSOAR_OLD_VERSION + 1)
        result = client.resolve_endpoint(v6="/incident", v8="/xsoar/public/v1/incident")
        assert result == "/xsoar/public/v1/incident"


# ===========================================================================
# Client.make_request
# ===========================================================================


class TestMakeRequest:
    def test_builds_correct_url(self) -> None:
        client = _make_client(server_url="https://xsoar.example.com")
        with patch("xsoar_cli.xsoar_client.client.requests.request") as mock_req:
            mock_req.return_value = MagicMock(status_code=200)
            client.make_request(endpoint="/test/endpoint", method="GET")

        call_kwargs = mock_req.call_args[1]
        assert call_kwargs["url"] == "https://xsoar.example.com/test/endpoint"

    def test_sets_authorization_header(self) -> None:
        client = _make_client(api_token="my-secret-token")
        with patch("xsoar_cli.xsoar_client.client.requests.request") as mock_req:
            mock_req.return_value = MagicMock(status_code=200)
            client.make_request(endpoint="/test", method="GET")

        headers = mock_req.call_args[1]["headers"]
        assert headers["Authorization"] == "my-secret-token"

    def test_sets_accept_and_content_type_headers(self) -> None:
        client = _make_client()
        with patch("xsoar_cli.xsoar_client.client.requests.request") as mock_req:
            mock_req.return_value = MagicMock(status_code=200)
            client.make_request(endpoint="/test", method="GET")

        headers = mock_req.call_args[1]["headers"]
        assert headers["Accept"] == "application/json"
        assert headers["Content-Type"] == "application/json"

    def test_includes_xdr_auth_id_header_when_set(self) -> None:
        client = _make_client(server_version=8, xsiam_auth_id="42")
        with patch("xsoar_cli.xsoar_client.client.requests.request") as mock_req:
            mock_req.return_value = MagicMock(status_code=200)
            client.make_request(endpoint="/test", method="GET")

        headers = mock_req.call_args[1]["headers"]
        assert headers["x-xdr-auth-id"] == "42"

    def test_omits_xdr_auth_id_header_when_empty(self) -> None:
        client = _make_client(server_version=6, xsiam_auth_id="")
        with patch("xsoar_cli.xsoar_client.client.requests.request") as mock_req:
            mock_req.return_value = MagicMock(status_code=200)
            client.make_request(endpoint="/test", method="GET")

        headers = mock_req.call_args[1]["headers"]
        assert "x-xdr-auth-id" not in headers

    def test_passes_json_body(self) -> None:
        client = _make_client()
        payload = {"query": "test"}
        with patch("xsoar_cli.xsoar_client.client.requests.request") as mock_req:
            mock_req.return_value = MagicMock(status_code=200)
            client.make_request(endpoint="/search", method="POST", json=payload)

        call_kwargs = mock_req.call_args[1]
        assert call_kwargs["json"] == {"query": "test"}
        assert call_kwargs["method"] == "POST"

    def test_passes_verify_ssl(self) -> None:
        client = _make_client(verify_ssl=True)
        with patch("xsoar_cli.xsoar_client.client.requests.request") as mock_req:
            mock_req.return_value = MagicMock(status_code=200)
            client.make_request(endpoint="/test", method="GET")

        call_kwargs = mock_req.call_args[1]
        assert call_kwargs["verify"] is True

    def test_passes_timeout(self) -> None:
        client = _make_client()
        with patch("xsoar_cli.xsoar_client.client.requests.request") as mock_req:
            mock_req.return_value = MagicMock(status_code=200)
            client.make_request(endpoint="/test", method="GET")

        call_kwargs = mock_req.call_args[1]
        assert call_kwargs["timeout"] == client.http_timeout

    def test_returns_response(self) -> None:
        client = _make_client()
        expected_response = MagicMock(status_code=200)
        with patch("xsoar_cli.xsoar_client.client.requests.request", return_value=expected_response):
            result = client.make_request(endpoint="/test", method="GET")

        assert result is expected_response


# ===========================================================================
# Client.test_connectivity
# ===========================================================================


class TestTestConnectivity:
    def test_success(self) -> None:
        client = _make_client(server_version=6)
        response = MagicMock(status_code=200)
        response.raise_for_status.return_value = None
        with patch("xsoar_cli.xsoar_client.client.requests.request", return_value=response):
            result = client.test_connectivity()

        assert result is True

    def test_uses_v6_endpoint(self) -> None:
        client = _make_client(server_version=6)
        response = MagicMock(status_code=200)
        response.raise_for_status.return_value = None
        with patch("xsoar_cli.xsoar_client.client.requests.request", return_value=response) as mock_req:
            client.test_connectivity()

        call_kwargs = mock_req.call_args[1]
        assert "/workers/status" in call_kwargs["url"]

    def test_uses_v8_endpoint(self) -> None:
        client = _make_client(server_version=8)
        response = MagicMock(status_code=200)
        response.raise_for_status.return_value = None
        with patch("xsoar_cli.xsoar_client.client.requests.request", return_value=response) as mock_req:
            client.test_connectivity()

        call_kwargs = mock_req.call_args[1]
        assert "/xsoar/workers/status" in call_kwargs["url"]

    def test_failure_raises_connection_error(self) -> None:
        client = _make_client(server_version=6)
        with patch(
            "xsoar_cli.xsoar_client.client.requests.request",
            side_effect=RequestsConnectionError("Connection refused"),
        ):
            with pytest.raises(ConnectionError, match="Failed to connect"):
                client.test_connectivity()

    def test_http_error_raises_connection_error(self) -> None:
        client = _make_client(server_version=6)
        response = MagicMock(status_code=401)
        response.raise_for_status.side_effect = Exception("401 Unauthorized")
        with patch("xsoar_cli.xsoar_client.client.requests.request", return_value=response):
            with pytest.raises(ConnectionError, match="Failed to connect"):
                client.test_connectivity()


# ===========================================================================
# Client.__init__ domain class wiring
# ===========================================================================


class TestClientInit:
    def test_domain_classes_initialized(self) -> None:
        client = _make_client()
        assert client.packs is not None
        assert client.cases is not None
        assert client.content is not None
        assert client.integrations is not None
        assert client.rbac is not None

    def test_artifact_provider_stored(self) -> None:
        provider = MagicMock()
        client = _make_client(artifact_provider=provider)
        assert client.artifact_provider is provider

    def test_artifact_provider_defaults_to_none(self) -> None:
        client = _make_client()
        assert client.artifact_provider is None

    def test_custom_pack_authors_passed_to_packs(self) -> None:
        client = _make_client(custom_pack_authors=["MyOrg", "OtherOrg"])
        assert client.packs.custom_pack_authors == ["MyOrg", "OtherOrg"]

    def test_custom_pack_authors_defaults_to_empty(self) -> None:
        client = _make_client()
        assert client.packs.custom_pack_authors == []
