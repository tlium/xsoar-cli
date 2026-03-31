from __future__ import annotations

from typing import TYPE_CHECKING

from .constants import XSOAR_OLD_VERSION

if TYPE_CHECKING:
    from .client import Client


class Cases:
    def __init__(self, client: Client) -> None:
        self.client = client

    def get(self, case_id: int) -> dict:
        """Fetches a case by ID."""
        endpoint = f"/incident/load/{case_id}"
        response = self.client.make_request(endpoint=endpoint, method="GET")
        response.raise_for_status()
        return response.json()

    def create(self, data: dict) -> dict:
        """Creates a new case."""
        if self.client.server_version > XSOAR_OLD_VERSION:
            endpoint = "/xsoar/public/v1/incident"
        else:
            endpoint = "/incident"
        response = self.client.make_request(endpoint=endpoint, json=data, method="POST")
        response.raise_for_status()
        return response.json()
