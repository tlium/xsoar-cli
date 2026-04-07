"""Handlers for downloading content items from XSOAR.

Each content type has a handler class that knows how to download, extract the
pack ID, build the output filename, and write the data to disk. The download
command dispatches to the appropriate handler based on the --type argument.
"""

from __future__ import annotations

import json
import logging
import pathlib
from abc import ABC, abstractmethod
from io import StringIO
from typing import TYPE_CHECKING, Any

import click
import yaml

if TYPE_CHECKING:
    from xsoar_cli.xsoar_client.client import Client

logger = logging.getLogger(__name__)


# -- Handler base class and implementations ----------------------------------


class ContentHandler(ABC):
    """Base class for content type download handlers."""

    subdir: str

    @abstractmethod
    def download(self, client: Client, name: str) -> Any:
        """Download the content item from XSOAR. Return type varies by handler."""

    @abstractmethod
    def extract_pack_id(self, data: Any) -> str | None:
        """Extract the pack ID from the downloaded data."""

    @abstractmethod
    def build_filename(self, name: str) -> str:
        """Build the output filename for the content item."""

    @abstractmethod
    def write(self, filepath: pathlib.Path, data: Any) -> None:
        """Write the downloaded data to disk."""


class PlaybookHandler(ContentHandler):
    subdir = "Playbooks"

    def download(self, client: Client, name: str) -> bytes:
        return client.content.download_playbook(name)

    def extract_pack_id(self, data: bytes) -> str | None:
        playbook_data = yaml.safe_load(StringIO(data.decode("utf-8")))
        return playbook_data.get("contentitemexportablefields", {}).get("contentitemfields", {}).get("packID")

    def build_filename(self, name: str) -> str:
        return f"{name.replace(' ', '_')}.yml"

    def write(self, filepath: pathlib.Path, data: bytes) -> None:
        filepath.write_bytes(data)


class LayoutHandler(ContentHandler):
    subdir = "Layouts"

    def download(self, client: Client, name: str) -> dict:
        return client.content.download_layout(name)

    def extract_pack_id(self, data: dict) -> str | None:
        return data.get("packID")

    def build_filename(self, name: str) -> str:
        return f"layoutscontainer-{name.replace(' ', '_')}.json"

    def write(self, filepath: pathlib.Path, data: dict) -> None:
        filepath.write_text(json.dumps(data, indent=4))


# -- Registry and helpers ----------------------------------------------------

HANDLERS: dict[str, ContentHandler] = {
    "playbook": PlaybookHandler(),
    "layout": LayoutHandler(),
}


def resolve_output_path(
    pack_id: str | None,
    subdir: str,
    filename: str,
    *,
    cwd: pathlib.Path | None = None,
) -> pathlib.Path | None:
    """Determine where to write a downloaded content item.

    Returns the resolved file path, or None if the user chose to discard.

    Rules:
    - If pack_id is known, target is Packs/<pack_id>/<subdir>/<filename>.
    - If the target directory does not exist, warn and offer cwd as fallback.
    - If the target file does not already exist, prompt for confirmation.
    - If the target file already exists, overwrite silently.
    """
    if cwd is None:
        cwd = pathlib.Path.cwd()

    if pack_id:
        target_dir = cwd / "Packs" / pack_id / subdir
    else:
        logger.warning("Could not determine pack ID, falling back to current directory")
        target_dir = cwd

    if not target_dir.is_dir():
        click.echo(f"Warning: target directory does not exist: {target_dir}")
        if not click.confirm("Save to current working directory instead?"):
            return None
        target_dir = cwd

    filepath = target_dir / filename

    if not filepath.exists():
        click.echo(f"File does not exist: {filepath}")
        if not click.confirm("Write to this path?"):
            return None

    return filepath
