"""Unit tests for the Azure artifact provider (``xsoar_cli.xsoar_client.artifact_providers.azure``).

All methods interact with ``azure.storage.blob``. Tests mock ``BlobServiceClient``
and container/blob clients to verify behavior without real Azure connectivity.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from azure.core.exceptions import ResourceNotFoundError

from xsoar_cli.xsoar_client.artifact_providers.azure import AzureArtifactProvider

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_provider(**overrides) -> AzureArtifactProvider:  # noqa: ANN003
    defaults = {
        "storage_account_url": "https://myaccount.blob.core.windows.net",
        "container_name": "artifacts",
        "access_token": "test-sas-token",
    }
    defaults.update(overrides)
    return AzureArtifactProvider(**defaults)


# ===========================================================================
# service property
# ===========================================================================


class TestServiceProperty:
    def test_uses_explicit_access_token(self) -> None:
        provider = _make_provider(access_token="explicit-token")
        with patch("xsoar_cli.xsoar_client.artifact_providers.azure.BlobServiceClient") as mock_cls:
            _ = provider.service
        mock_cls.assert_called_once_with(
            account_url="https://myaccount.blob.core.windows.net",
            credential="explicit-token",
        )

    def test_falls_back_to_env_var(self) -> None:
        provider = _make_provider(access_token="")
        with (
            patch.dict("os.environ", {"AZURE_STORAGE_SAS_TOKEN": "env-token"}),
            patch("xsoar_cli.xsoar_client.artifact_providers.azure.BlobServiceClient") as mock_cls,
        ):
            _ = provider.service
        mock_cls.assert_called_once_with(
            account_url="https://myaccount.blob.core.windows.net",
            credential="env-token",
        )
        assert provider.access_token == "env-token"

    def test_no_token_raises(self) -> None:
        provider = _make_provider(access_token="")
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(RuntimeError, match="Cannot find access token"):
                _ = provider.service

    def test_caches_service_instance(self) -> None:
        provider = _make_provider()
        with patch("xsoar_cli.xsoar_client.artifact_providers.azure.BlobServiceClient") as mock_cls:
            first = provider.service
            second = provider.service
        assert first is second
        mock_cls.assert_called_once()


# ===========================================================================
# container_client property
# ===========================================================================


class TestContainerClientProperty:
    def test_uses_configured_container_name(self) -> None:
        provider = _make_provider(container_name="my-container")
        mock_service = MagicMock()
        provider._service = mock_service

        _ = provider.container_client

        mock_service.get_container_client.assert_called_once_with("my-container")

    def test_caches_container_client(self) -> None:
        provider = _make_provider()
        mock_service = MagicMock()
        provider._service = mock_service

        first = provider.container_client
        second = provider.container_client

        assert first is second
        mock_service.get_container_client.assert_called_once()


# ===========================================================================
# test_connection
# ===========================================================================


class TestTestConnection:
    def test_happy_path(self) -> None:
        provider = _make_provider()
        mock_container = MagicMock()
        provider._container_client = mock_container

        result = provider.test_connection()

        assert result is True
        mock_container.get_container_properties.assert_called_once()

    def test_failure_propagates(self) -> None:
        provider = _make_provider()
        mock_container = MagicMock()
        mock_container.get_container_properties.side_effect = Exception("Connection failed")
        provider._container_client = mock_container

        with pytest.raises(Exception, match="Connection failed"):
            provider.test_connection()


# ===========================================================================
# is_available
# ===========================================================================


class TestIsAvailable:
    def test_blob_exists(self) -> None:
        provider = _make_provider()
        mock_container = MagicMock()
        provider._container_client = mock_container

        result = provider.is_available(pack_id="MyPack", pack_version="1.0.0")

        assert result is True
        expected_path = "content/packs/MyPack/1.0.0/MyPack.zip"
        mock_container.get_blob_client.assert_called_once_with(blob=expected_path)
        mock_container.get_blob_client.return_value.get_blob_properties.assert_called_once()

    def test_blob_not_found(self) -> None:
        provider = _make_provider()
        mock_container = MagicMock()
        mock_blob = MagicMock()
        mock_blob.get_blob_properties.side_effect = ResourceNotFoundError("Not found")
        mock_container.get_blob_client.return_value = mock_blob
        provider._container_client = mock_container

        result = provider.is_available(pack_id="MyPack", pack_version="99.0.0")

        assert result is False


# ===========================================================================
# download
# ===========================================================================


class TestDownload:
    def test_returns_blob_content(self) -> None:
        provider = _make_provider()
        mock_container = MagicMock()
        mock_stream = MagicMock()
        mock_stream.readall.return_value = b"zip-file-data"
        mock_container.download_blob.return_value = mock_stream
        provider._container_client = mock_container

        result = provider.download(pack_id="MyPack", pack_version="1.0.0")

        assert result == b"zip-file-data"
        expected_path = "content/packs/MyPack/1.0.0/MyPack.zip"
        mock_container.download_blob.assert_called_once_with(blob=expected_path)

    def test_uses_get_pack_path(self) -> None:
        provider = _make_provider()
        mock_container = MagicMock()
        mock_stream = MagicMock()
        mock_stream.readall.return_value = b"data"
        mock_container.download_blob.return_value = mock_stream
        provider._container_client = mock_container

        provider.download(pack_id="SomePack", pack_version="2.3.4")

        expected_path = "content/packs/SomePack/2.3.4/SomePack.zip"
        mock_container.download_blob.assert_called_once_with(blob=expected_path)


# ===========================================================================
# get_latest_version
# ===========================================================================


class TestGetLatestVersion:
    def test_parses_versions_from_blob_names(self) -> None:
        provider = _make_provider()
        mock_container = MagicMock()
        mock_container.list_blob_names.return_value = [
            "content/packs/MyPack/1.0.0/MyPack.zip",
            "content/packs/MyPack/1.1.0/MyPack.zip",
            "content/packs/MyPack/2.0.0/MyPack.zip",
            "content/packs/MyPack/1.9.0/MyPack.zip",
        ]
        provider._container_client = mock_container

        result = provider.get_latest_version("MyPack")

        assert result == "2.0.0"
        mock_container.list_blob_names.assert_called_once_with(
            name_starts_with="content/packs/MyPack/",
        )

    def test_handles_single_version(self) -> None:
        provider = _make_provider()
        mock_container = MagicMock()
        mock_container.list_blob_names.return_value = [
            "content/packs/MyPack/1.0.0/MyPack.zip",
        ]
        provider._container_client = mock_container

        result = provider.get_latest_version("MyPack")

        assert result == "1.0.0"

    def test_raises_on_empty_listing(self) -> None:
        provider = _make_provider()
        mock_container = MagicMock()
        mock_container.list_blob_names.return_value = []
        provider._container_client = mock_container

        with pytest.raises(ValueError):
            provider.get_latest_version("NonExistent")
