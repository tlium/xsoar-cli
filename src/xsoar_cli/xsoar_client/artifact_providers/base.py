from __future__ import annotations

from abc import ABC, abstractmethod


class BaseArtifactProvider(ABC):
    """Abstract base class for artifact storage providers."""

    @abstractmethod
    def test_connection(self) -> bool:
        """Test connection to the artifact storage."""
        ...

    @abstractmethod
    def is_available(self, *, pack_id: str, pack_version: str) -> bool:
        """Check if a specific pack version is available."""
        ...

    @abstractmethod
    def download(self, *, pack_id: str, pack_version: str) -> bytes:
        """Download a pack from the artifact storage."""
        ...

    @abstractmethod
    def get_latest_version(self, pack_id: str) -> str:
        """Get the latest version of a pack."""
        ...

    def get_pack_path(self, pack_id: str, pack_version: str) -> str:
        """Generate the standard path for a pack artifact."""
        return f"content/packs/{pack_id}/{pack_version}/{pack_id}.zip"
