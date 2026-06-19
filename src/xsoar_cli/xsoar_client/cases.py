from __future__ import annotations

from typing import TYPE_CHECKING

from .constants import INVESTIGATION_PAGE_SIZE

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

    def get_context(self, case_id: int) -> dict:
        """Fetches the investigation context tree for a case, verbatim.

        Returns the raw GET /investigation/<id>/context response, which matches
        demisto.context() at runtime. The incident record is not merged in.
        """
        endpoint = f"/investigation/{case_id}/context"
        response = self.client.make_request(endpoint=endpoint, method="GET")
        response.raise_for_status()
        return response.json()

    def get_entry(self, case_id: int, entry_id: str) -> dict:
        """Fetches a single War Room entry by its full ID (e.g. '112@153483').

        XSOAR has no per-entry endpoint, so the full War Room history is fetched
        via POST /investigation/<id> and the entry with the matching id is
        returned verbatim. Raises ValueError if no entry with that id exists.
        """
        data, _, _ = self.client.demisto_py_instance.generic_request(
            path=f"/investigation/{case_id}",
            method="POST",
            body={"pageSize": INVESTIGATION_PAGE_SIZE},
            content_type="application/json",
            response_type=object,
        )
        entries = data.get("entries") or []
        for entry in entries:
            if entry.get("id") == entry_id:
                return entry
        msg = f"Entry '{entry_id}' not found in case {case_id}"
        raise ValueError(msg)
