"""Unit tests for the base artifact provider (``xsoar_cli.xsoar_client.artifact_providers.base``)."""

from __future__ import annotations

from xsoar_cli.xsoar_client.artifact_providers.base import BaseArtifactProvider


class _ConcreteProvider(BaseArtifactProvider):
    """Minimal concrete subclass for testing the non-abstract methods."""

    def test_connection(self) -> bool:
        return True

    def is_available(self, *, pack_id: str, pack_version: str) -> bool:
        return True

    def download(self, *, pack_id: str, pack_version: str) -> bytes:
        return b""

    def get_latest_version(self, pack_id: str) -> str:
        return "1.0.0"


class TestGetPackPath:
    def test_standard_path(self) -> None:
        provider = _ConcreteProvider()
        result = provider.get_pack_path("MyPack", "1.2.3")
        assert result == "content/packs/MyPack/1.2.3/MyPack.zip"

    def test_pack_id_with_underscores(self) -> None:
        provider = _ConcreteProvider()
        result = provider.get_pack_path("MyOrg_EDR", "2.0.0")
        assert result == "content/packs/MyOrg_EDR/2.0.0/MyOrg_EDR.zip"

    def test_prerelease_version(self) -> None:
        provider = _ConcreteProvider()
        result = provider.get_pack_path("Pack", "1.0.0rc1")
        assert result == "content/packs/Pack/1.0.0rc1/Pack.zip"
