from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .client import Client


class Rbac:
    def __init__(self, client: Client) -> None:
        self.client = client

    def get_users(self) -> str:
        """Returns information on all XSOAR users."""
        if self.client.server_version < 8:
            endpoint = "/users"
        else:
            endpoint = "/rbac/get_users"
        response = self.client._make_request(endpoint=endpoint, method="GET")
        response.raise_for_status()
        return response.content

    def get_roles(self) -> str:
        """Returns information on all XSOAR roles."""
        if self.client.server_version < 8:
            endpoint = "/roles"
        else:
            endpoint = "/rbac/get_roles"
        response = self.client._make_request(endpoint=endpoint, method="GET")
        response.raise_for_status()
        return response.content

    def get_user_groups(self) -> str:
        """Returns information on all XSOAR user groups."""
        if self.client.server_version < 8:
            endpoint = "/user_groups"
        else:
            endpoint = "/rbac/get_user_groups"
        response = self.client._make_request(endpoint=endpoint, method="GET")
        response.raise_for_status()
        return response.content
