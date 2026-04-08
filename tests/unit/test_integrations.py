"""Unit tests for the Integrations domain class (``xsoar_cli.xsoar_client.integrations``).

Tests mock ``client.make_request`` to verify that each method builds the
correct request and propagates responses/errors as expected.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from requests.exceptions import HTTPError

from xsoar_cli.xsoar_client.integrations import Integrations

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_INSTANCES = [
    {
        "id": "instance-uuid-001",
        "name": "EWS_Main",
        "brand": "EWS v2",
        "enabled": "true",
        "defaultIgnored": "false",
        "configvalues": {},
    },
    {
        "id": "instance-uuid-002",
        "name": "EWS_Secondary",
        "brand": "EWS v2",
        "enabled": "false",
        "defaultIgnored": "false",
        "configvalues": {},
    },
    {
        "id": "instance-uuid-003",
        "name": "VirusTotal_Prod",
        "brand": "VirusTotal",
        "enabled": "true",
        "defaultIgnored": "false",
        "configvalues": {},
    },
]


def _mock_response(json_data: list | dict, *, status_code: int = 200) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data
    response.raise_for_status.return_value = None
    return response


# ===========================================================================
# Integrations.get_instances
# ===========================================================================


class TestGetInstances:
    def test_happy_path(self, mock_client: MagicMock) -> None:
        mock_client.make_request.return_value = _mock_response(_INSTANCES)

        integrations = Integrations(mock_client)
        result = integrations.get_instances()

        assert result == _INSTANCES
        mock_client.make_request.assert_called_once_with(endpoint="/integration/instances", method="GET")

    def test_calls_raise_for_status(self, mock_client: MagicMock) -> None:
        mock_client.make_request.return_value = _mock_response(_INSTANCES)

        integrations = Integrations(mock_client)
        integrations.get_instances()

        mock_client.make_request.return_value.raise_for_status.assert_called_once()

    def test_http_error_propagates(self, mock_client: MagicMock) -> None:
        response = MagicMock()
        response.raise_for_status.side_effect = HTTPError("403 Forbidden")
        mock_client.make_request.return_value = response

        integrations = Integrations(mock_client)
        with pytest.raises(HTTPError, match="403 Forbidden"):
            integrations.get_instances()

    def test_returns_empty_list(self, mock_client: MagicMock) -> None:
        mock_client.make_request.return_value = _mock_response([])

        integrations = Integrations(mock_client)
        result = integrations.get_instances()

        assert result == []

    def test_name_field_accessible(self, mock_client: MagicMock) -> None:
        """The ``name`` field is accessed via bare dict lookup in the dump command."""
        mock_client.make_request.return_value = _mock_response(_INSTANCES)

        integrations = Integrations(mock_client)
        result = integrations.get_instances()

        names = [inst["name"] for inst in result]
        assert names == ["EWS_Main", "EWS_Secondary", "VirusTotal_Prod"]


# ===========================================================================
# Integrations.load_config
# ===========================================================================


class TestLoadConfig:
    def test_raises_not_implemented(self, mock_client: MagicMock) -> None:
        integrations = Integrations(mock_client)
        with pytest.raises(NotImplementedError):
            integrations.load_config("config.json", "EWS_Main")
