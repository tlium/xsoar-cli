"""Unit tests for the Cases domain class (``xsoar_cli.xsoar_client.cases``).

Tests mock ``client.make_request`` and ``client.resolve_endpoint`` to verify
that ``Cases.get()`` and ``Cases.create()`` build the correct requests and
propagate responses/errors as expected.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from requests.exceptions import HTTPError

from xsoar_cli.xsoar_client.cases import Cases

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_GET_RESPONSE = {
    "id": "12345",
    "version": 3,
    "name": "Phishing Investigation",
    "type": "Phishing",
    "status": 1,
    "severity": 2,
    "owner": "admin",
    "created": "2024-06-15T08:30:00Z",
    "modified": "2024-06-15T09:45:00Z",
    "details": "Suspicious email reported by user",
    "labels": [
        {"type": "Email", "value": "phish@example.com"},
        {"type": "Reporter", "value": "jdoe"},
    ],
    "attachment": None,
    "cacheVersn": 2,
    "sizeInBytes": 4096,
    "dbotMirrorId": "",
    "dbotMirrorInstance": "",
    "dbotMirrorDirection": "",
    "dbotDirtyFields": [],
    "dbotCurrentDirtyFields": [],
    "dbotMirrorTags": [],
    "dbotMirrorLastSync": "",
}

_CREATE_RESPONSE = {
    "id": "12346",
    "name": "Phishing Investigation",
    "created": "2024-06-15T10:00:00Z",
    "modified": "2024-06-15T10:00:00Z",
    "details": "Suspicious email reported by user",
    "status": 1,
    "severity": 2,
    "owner": "admin",
    "version": 1,
}


def _mock_response(json_data: dict, *, status_code: int = 200) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data
    response.raise_for_status.return_value = None
    return response


# ===========================================================================
# Cases.get
# ===========================================================================


class TestCasesGet:
    def test_happy_path(self, mock_client: MagicMock) -> None:
        mock_client.make_request.return_value = _mock_response(_GET_RESPONSE)

        cases = Cases(mock_client)
        result = cases.get(12345)

        assert result == _GET_RESPONSE
        mock_client.make_request.assert_called_once_with(endpoint="/incident/load/12345", method="GET")

    def test_calls_raise_for_status(self, mock_client: MagicMock) -> None:
        mock_client.make_request.return_value = _mock_response(_GET_RESPONSE)

        cases = Cases(mock_client)
        cases.get(12345)

        mock_client.make_request.return_value.raise_for_status.assert_called_once()

    def test_http_error_propagates(self, mock_client: MagicMock) -> None:
        response = MagicMock()
        response.raise_for_status.side_effect = HTTPError("404 Not Found")
        mock_client.make_request.return_value = response

        cases = Cases(mock_client)
        with pytest.raises(HTTPError, match="404 Not Found"):
            cases.get(99999)

    def test_returns_full_response_fields(self, mock_client: MagicMock) -> None:
        """Verify all fields needed by the clone command are present."""
        mock_client.make_request.return_value = _mock_response(_GET_RESPONSE)

        cases = Cases(mock_client)
        result = cases.get(12345)

        clone_fields = [
            "id",
            "version",
            "created",
            "modified",
            "cacheVersn",
            "sizeInBytes",
            "attachment",
            "labels",
            "owner",
            "dbotMirrorId",
            "dbotMirrorInstance",
            "dbotMirrorDirection",
            "dbotDirtyFields",
            "dbotCurrentDirtyFields",
            "dbotMirrorTags",
            "dbotMirrorLastSync",
        ]
        for field in clone_fields:
            assert field in result, f"Missing field required by clone: {field}"


# ===========================================================================
# Cases.create
# ===========================================================================


class TestCasesCreate:
    def test_happy_path_v6(self, mock_client: MagicMock) -> None:
        mock_client.resolve_endpoint.return_value = "/incident"
        mock_client.make_request.return_value = _mock_response(_CREATE_RESPONSE)

        cases = Cases(mock_client)
        data = {"name": "New Case", "severity": 1}
        result = cases.create(data)

        assert result["id"] == "12346"
        mock_client.resolve_endpoint.assert_called_once_with(v6="/incident", v8="/xsoar/public/v1/incident")
        mock_client.make_request.assert_called_once_with(endpoint="/incident", json=data, method="POST")

    def test_happy_path_v8(self, mock_client: MagicMock) -> None:
        mock_client.resolve_endpoint.return_value = "/xsoar/public/v1/incident"
        mock_client.make_request.return_value = _mock_response(_CREATE_RESPONSE)

        cases = Cases(mock_client)
        data = {"name": "New Case", "severity": 1}
        cases.create(data)

        mock_client.make_request.assert_called_once_with(endpoint="/xsoar/public/v1/incident", json=data, method="POST")

    def test_calls_raise_for_status(self, mock_client: MagicMock) -> None:
        mock_client.resolve_endpoint.return_value = "/incident"
        mock_client.make_request.return_value = _mock_response(_CREATE_RESPONSE)

        cases = Cases(mock_client)
        cases.create({"name": "Test"})

        mock_client.make_request.return_value.raise_for_status.assert_called_once()

    def test_http_error_propagates(self, mock_client: MagicMock) -> None:
        mock_client.resolve_endpoint.return_value = "/incident"
        response = MagicMock()
        response.raise_for_status.side_effect = HTTPError("400 Bad Request")
        mock_client.make_request.return_value = response

        cases = Cases(mock_client)
        with pytest.raises(HTTPError, match="400 Bad Request"):
            cases.create({"name": "Bad"})
