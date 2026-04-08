"""Unit tests for the RBAC domain class (``xsoar_cli.xsoar_client.rbac``).

Tests mock ``client.make_request`` and ``client.resolve_endpoint`` to verify
that each RBAC method builds the correct request and propagates
responses/errors as expected.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from requests.exceptions import HTTPError

from xsoar_cli.xsoar_client.rbac import Rbac

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_USERS = [
    {
        "id": "admin",
        "username": "admin",
        "name": "Admin User",
        "email": "admin@example.com",
        "roles": {"demisto": ["Administrator"]},
        "phone": "",
        "accUser": False,
    },
    {
        "id": "analyst1",
        "username": "analyst1",
        "name": "Jane Doe",
        "email": "jane.doe@example.com",
        "roles": {"demisto": ["Analyst"]},
        "phone": "+1234567890",
        "accUser": False,
    },
]

_ROLES = [
    {
        "id": "Administrator",
        "name": "Administrator",
        "permissions": {"demisto": ["adminPage", "scripts", "playbooks"]},
    },
    {
        "id": "Analyst",
        "name": "Analyst",
        "permissions": {"demisto": ["scripts", "playbooks"]},
    },
]

_USER_GROUPS = [
    {
        "id": "group-uuid-001",
        "name": "SOC Team",
        "data": ["analyst1", "analyst2"],
    },
    {
        "id": "group-uuid-002",
        "name": "Admins",
        "data": ["admin"],
    },
]


def _mock_response(json_data: list | dict, *, status_code: int = 200) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data
    response.raise_for_status.return_value = None
    return response


# ===========================================================================
# Rbac.get_users
# ===========================================================================


class TestGetUsers:
    def test_happy_path_v6(self, mock_client: MagicMock) -> None:
        mock_client.resolve_endpoint.return_value = "/users"
        mock_client.make_request.return_value = _mock_response(_USERS)

        rbac = Rbac(mock_client)
        result = rbac.get_users()

        assert result == _USERS
        mock_client.resolve_endpoint.assert_called_once_with(v6="/users", v8="/rbac/get_users")
        mock_client.make_request.assert_called_once_with(endpoint="/users", method="GET")

    def test_happy_path_v8(self, mock_client: MagicMock) -> None:
        mock_client.resolve_endpoint.return_value = "/rbac/get_users"
        mock_client.make_request.return_value = _mock_response(_USERS)

        rbac = Rbac(mock_client)
        rbac.get_users()

        mock_client.make_request.assert_called_once_with(endpoint="/rbac/get_users", method="GET")

    def test_calls_raise_for_status(self, mock_client: MagicMock) -> None:
        mock_client.resolve_endpoint.return_value = "/users"
        mock_client.make_request.return_value = _mock_response(_USERS)

        rbac = Rbac(mock_client)
        rbac.get_users()

        mock_client.make_request.return_value.raise_for_status.assert_called_once()

    def test_http_error_propagates(self, mock_client: MagicMock) -> None:
        mock_client.resolve_endpoint.return_value = "/users"
        response = MagicMock()
        response.raise_for_status.side_effect = HTTPError("403 Forbidden")
        mock_client.make_request.return_value = response

        rbac = Rbac(mock_client)
        with pytest.raises(HTTPError, match="403 Forbidden"):
            rbac.get_users()


# ===========================================================================
# Rbac.get_roles
# ===========================================================================


class TestGetRoles:
    def test_happy_path_v6(self, mock_client: MagicMock) -> None:
        mock_client.resolve_endpoint.return_value = "/roles"
        mock_client.make_request.return_value = _mock_response(_ROLES)

        rbac = Rbac(mock_client)
        result = rbac.get_roles()

        assert result == _ROLES
        mock_client.resolve_endpoint.assert_called_once_with(v6="/roles", v8="/rbac/get_roles")
        mock_client.make_request.assert_called_once_with(endpoint="/roles", method="GET")

    def test_happy_path_v8(self, mock_client: MagicMock) -> None:
        mock_client.resolve_endpoint.return_value = "/rbac/get_roles"
        mock_client.make_request.return_value = _mock_response(_ROLES)

        rbac = Rbac(mock_client)
        rbac.get_roles()

        mock_client.make_request.assert_called_once_with(endpoint="/rbac/get_roles", method="GET")

    def test_calls_raise_for_status(self, mock_client: MagicMock) -> None:
        mock_client.resolve_endpoint.return_value = "/roles"
        mock_client.make_request.return_value = _mock_response(_ROLES)

        rbac = Rbac(mock_client)
        rbac.get_roles()

        mock_client.make_request.return_value.raise_for_status.assert_called_once()

    def test_http_error_propagates(self, mock_client: MagicMock) -> None:
        mock_client.resolve_endpoint.return_value = "/roles"
        response = MagicMock()
        response.raise_for_status.side_effect = HTTPError("403 Forbidden")
        mock_client.make_request.return_value = response

        rbac = Rbac(mock_client)
        with pytest.raises(HTTPError, match="403 Forbidden"):
            rbac.get_roles()


# ===========================================================================
# Rbac.get_user_groups
# ===========================================================================


class TestGetUserGroups:
    def test_happy_path_v6(self, mock_client: MagicMock) -> None:
        mock_client.resolve_endpoint.return_value = "/user_groups"
        mock_client.make_request.return_value = _mock_response(_USER_GROUPS)

        rbac = Rbac(mock_client)
        result = rbac.get_user_groups()

        assert result == _USER_GROUPS
        mock_client.resolve_endpoint.assert_called_once_with(v6="/user_groups", v8="/rbac/get_user_groups")
        mock_client.make_request.assert_called_once_with(endpoint="/user_groups", method="GET")

    def test_happy_path_v8(self, mock_client: MagicMock) -> None:
        mock_client.resolve_endpoint.return_value = "/rbac/get_user_groups"
        mock_client.make_request.return_value = _mock_response(_USER_GROUPS)

        rbac = Rbac(mock_client)
        rbac.get_user_groups()

        mock_client.make_request.assert_called_once_with(endpoint="/rbac/get_user_groups", method="GET")

    def test_calls_raise_for_status(self, mock_client: MagicMock) -> None:
        mock_client.resolve_endpoint.return_value = "/user_groups"
        mock_client.make_request.return_value = _mock_response(_USER_GROUPS)

        rbac = Rbac(mock_client)
        rbac.get_user_groups()

        mock_client.make_request.return_value.raise_for_status.assert_called_once()

    def test_http_error_propagates(self, mock_client: MagicMock) -> None:
        mock_client.resolve_endpoint.return_value = "/user_groups"
        response = MagicMock()
        response.raise_for_status.side_effect = HTTPError("403 Forbidden")
        mock_client.make_request.return_value = response

        rbac = Rbac(mock_client)
        with pytest.raises(HTTPError, match="403 Forbidden"):
            rbac.get_user_groups()
