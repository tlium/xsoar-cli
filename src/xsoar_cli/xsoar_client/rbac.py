from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .client import Client


class Rbac:
    def __init__(self, client: Client) -> None:
        self.client = client

    def get_users(self) -> list:
        """Returns information on all XSOAR users."""
        endpoint = self.client.resolve_endpoint(v6="/users", v8="/rbac/get_users")
        response = self.client.make_request(endpoint=endpoint, method="GET")
        response.raise_for_status()
        return response.json()

    def get_roles(self) -> list:
        """Returns information on all XSOAR roles."""
        endpoint = self.client.resolve_endpoint(v6="/roles", v8="/rbac/get_roles")
        response = self.client.make_request(endpoint=endpoint, method="GET")
        response.raise_for_status()
        return response.json()

    def get_user_groups(self) -> list:
        """Returns information on all XSOAR user groups."""
        endpoint = self.client.resolve_endpoint(v6="/user_groups", v8="/rbac/get_user_groups")
        response = self.client.make_request(endpoint=endpoint, method="GET")
        response.raise_for_status()
        return response.json()
