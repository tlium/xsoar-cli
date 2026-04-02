from __future__ import annotations

import tarfile
from io import BytesIO, StringIO
from typing import TYPE_CHECKING

from requests.models import Response

if TYPE_CHECKING:
    from .client import Client


class Content:
    def __init__(self, client: Client) -> None:
        self.client = client

    def get_bundle(self) -> dict[str, StringIO]:
        """Downloads and extracts the custom content bundle."""
        endpoint = "/content/bundle"
        response = self.client.make_request(endpoint=endpoint, method="GET")
        loaded_files: dict[str, StringIO] = {}

        with tarfile.open(fileobj=BytesIO(response.content), mode="r") as tar:
            tar_members = tar.getmembers()

            for file in tar_members:
                file_name = file.name.lstrip("/")

                if extracted_file := tar.extractfile(file):
                    file_data = StringIO(extracted_file.read().decode("utf-8"))
                    loaded_files[file_name] = file_data
        return loaded_files

    def get_detached(self, content_type: str | None) -> Response:
        """Returns detached content. Currently supports script, playbooks, layouts.
        Where content_type must be either "playbooks" or "scripts".
        """
        payload = {"query": "system:T"}
        if content_type == "scripts":
            endpoint = "/automation/search"
        elif content_type == "playbooks":
            endpoint = "/playbook/search"
        else:
            raise ValueError(f"Invalid value {content_type=}")
        response = self.client.make_request(endpoint=endpoint, method="POST", json=payload)
        response.raise_for_status()
        return response

    def download_item(self, item_type: str, item_id: str) -> bytes:
        """Downloads a content item by type and ID."""
        if item_type == "playbook":
            endpoint = f"/{item_type}/{item_id}/yaml"
            response = self.client.make_request(endpoint=endpoint, method="GET")
        else:
            msg = 'Unknown item_type selected for download. Must be one of ["playbook"]'
            raise ValueError(msg)
        response.raise_for_status()
        return response.content

    def attach_item(self, item_type: str, item_id: str) -> None:
        """Attaches a content item to the server-managed version."""
        if item_type == "playbook":
            endpoint = f"/{item_type}/attach/{item_id}"
            response = self.client.make_request(endpoint=endpoint, method="POST")
        else:
            msg = 'Unknown item_type selected. Must be one of ["playbook"]'
            raise ValueError(msg)
        response.raise_for_status()

    def detach_item(self, item_type: str, item_id: str) -> None:
        """Detaches a content item from the server-managed version."""
        if item_type == "playbook":
            endpoint = f"/{item_type}/detach/{item_id}"
            response = self.client.make_request(endpoint=endpoint, method="POST")
        else:
            msg = 'Unknown item_type selected. Must be one of ["playbook"]'
            raise ValueError(msg)
        response.raise_for_status()

    def _list_playbooks(self) -> list[dict]:
        endpoint = "/playbook/search"
        payload = {"query": "hidden:F AND deprecated:F"}
        response = self.client.make_request(endpoint=endpoint, json=payload, method="POST")
        response.raise_for_status()
        return response.json()["playbooks"]

    def _list_scripts(self) -> list[dict]:
        endpoint = "/automation/search"
        payload = {"query": "", "stripContext": False}
        response = self.client.make_request(endpoint=endpoint, json=payload, method="POST")
        response.raise_for_status()
        return response.json()["scripts"]

    def _list_commands(self) -> list[dict]:
        endpoint = "/user/commands"
        response = self.client.make_request(endpoint=endpoint, method="GET")
        response.raise_for_status()
        return response.json()

    def list(self, item_type: str) -> list[dict] | dict[str, list[dict]]:
        if item_type == "playbooks":
            return self._list_playbooks()
        if item_type == "scripts":
            return self._list_scripts()
        if item_type == "commands":
            return self._list_commands()
        if item_type == "all":
            return {"playbooks": self._list_playbooks(), "scripts": self._list_scripts(), "commands": self._list_commands()}
        raise ValueError(f"ERROR: list command received invalid argument {item_type=}")
