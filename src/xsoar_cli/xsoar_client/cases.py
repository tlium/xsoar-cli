from __future__ import annotations

from typing import TYPE_CHECKING

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
        endpoint = self.client.resolve_endpoint(v6="/incident", v8="/xsoar/public/v1/incident")
        response = self.client.make_request(endpoint=endpoint, json=data, method="POST")
        response.raise_for_status()
        return response.json()
