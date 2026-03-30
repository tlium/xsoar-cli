from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .xsoar_client import Client


class Integrations:
    def __init__(self, client: Client) -> None:
        self.client = client

    def get_instances(self) -> str:
        """Returns information on all installed integrations and their configured instances."""
        endpoint = "/integration/instances"
        response = self.client._make_request(endpoint=endpoint, method="GET")
        response.raise_for_status()
        return response.content

    def load_config(self, name: str, instance_name: str) -> None:
        """Load integration instance configuration into XSOAR from a JSON file."""
        raise NotImplementedError
