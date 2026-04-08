"""Unit tests for the S3 artifact provider (``xsoar_cli.xsoar_client.artifact_providers.s3``).

All methods interact with boto3. Tests mock ``boto3.session.Session`` and the
S3 resource/client objects to verify correct behavior without AWS credentials.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from xsoar_cli.xsoar_client.artifact_providers.s3 import S3ArtifactProvider

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_provider(**overrides) -> S3ArtifactProvider:  # noqa: ANN003
    defaults = {"bucket_name": "my-artifacts-bucket"}
    defaults.update(overrides)
    return S3ArtifactProvider(**defaults)


# ===========================================================================
# Lazy initialization (session / s3 properties)
# ===========================================================================


class TestLazyInit:
    def test_session_created_on_first_access(self) -> None:
        provider = _make_provider()
        assert provider._session is None
        with patch("xsoar_cli.xsoar_client.artifact_providers.s3.boto3.session.Session") as mock_session_cls:
            mock_session_cls.return_value = MagicMock()
            session = provider.session
            assert session is mock_session_cls.return_value
            assert provider._session is session

    def test_session_cached(self) -> None:
        provider = _make_provider()
        with patch("xsoar_cli.xsoar_client.artifact_providers.s3.boto3.session.Session") as mock_session_cls:
            mock_session_cls.return_value = MagicMock()
            first = provider.session
            second = provider.session
            assert first is second
            mock_session_cls.assert_called_once()

    def test_s3_resource_created_from_session(self) -> None:
        provider = _make_provider()
        mock_session = MagicMock()
        mock_resource = MagicMock()
        mock_session.resource.return_value = mock_resource
        provider._session = mock_session

        s3 = provider.s3

        assert s3 is mock_resource
        mock_session.resource.assert_called_once_with("s3")

    def test_s3_resource_cached(self) -> None:
        provider = _make_provider()
        mock_session = MagicMock()
        provider._session = mock_session

        first = provider.s3
        second = provider.s3

        assert first is second
        mock_session.resource.assert_called_once()


# ===========================================================================
# test_connection
# ===========================================================================


class TestTestConnection:
    def test_happy_path(self) -> None:
        provider = _make_provider()
        mock_s3 = MagicMock()
        mock_bucket = MagicMock()
        mock_s3.Bucket.return_value = mock_bucket
        provider._s3 = mock_s3
        provider._session = MagicMock()

        result = provider.test_connection()

        assert result is True
        mock_s3.Bucket.assert_called_once_with("my-artifacts-bucket")
        mock_bucket.load.assert_called_once()

    def test_failure_propagates(self) -> None:
        provider = _make_provider()
        mock_s3 = MagicMock()
        mock_bucket = MagicMock()
        mock_bucket.load.side_effect = Exception("Access Denied")
        mock_s3.Bucket.return_value = mock_bucket
        provider._s3 = mock_s3
        provider._session = MagicMock()

        with pytest.raises(Exception, match="Access Denied"):
            provider.test_connection()


# ===========================================================================
# is_available
# ===========================================================================


class TestIsAvailable:
    def test_object_exists(self) -> None:
        provider = _make_provider()
        mock_s3 = MagicMock()
        mock_obj = MagicMock()
        mock_obj.load.return_value = None
        mock_s3.Object.return_value = mock_obj
        provider._s3 = mock_s3
        provider._session = MagicMock()

        result = provider.is_available(pack_id="MyPack", pack_version="1.0.0")

        assert result is True
        mock_s3.Object.assert_called_once_with(
            "my-artifacts-bucket",
            "content/packs/MyPack/1.0.0/MyPack.zip",
        )

    def test_object_does_not_exist(self) -> None:
        provider = _make_provider()
        mock_s3 = MagicMock()
        mock_obj = MagicMock()
        mock_obj.load.side_effect = Exception("Not Found")
        mock_s3.Object.return_value = mock_obj
        provider._s3 = mock_s3
        provider._session = MagicMock()

        result = provider.is_available(pack_id="MyPack", pack_version="99.0.0")

        assert result is False


# ===========================================================================
# download
# ===========================================================================


class TestDownload:
    def test_returns_bytes(self) -> None:
        provider = _make_provider()
        mock_s3 = MagicMock()
        mock_obj = MagicMock()
        mock_body = MagicMock()
        mock_body.read.return_value = b"zip-content"
        mock_obj.get.return_value = {"Body": mock_body}
        mock_s3.Object.return_value = mock_obj
        provider._s3 = mock_s3
        provider._session = MagicMock()

        result = provider.download(pack_id="MyPack", pack_version="1.0.0")

        assert result == b"zip-content"
        mock_s3.Object.assert_called_once_with(
            bucket_name="my-artifacts-bucket",
            key="content/packs/MyPack/1.0.0/MyPack.zip",
        )


# ===========================================================================
# get_latest_version
# ===========================================================================


class TestGetLatestVersion:
    def test_parses_version_prefixes(self) -> None:
        provider = _make_provider()
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_client.list_objects_v2.return_value = {
            "CommonPrefixes": [
                {"Prefix": "content/packs/MyPack/1.0.0/"},
                {"Prefix": "content/packs/MyPack/1.1.0/"},
                {"Prefix": "content/packs/MyPack/2.0.0/"},
                {"Prefix": "content/packs/MyPack/1.2.0/"},
            ],
        }
        mock_session.client.return_value = mock_client
        provider._session = mock_session

        result = provider.get_latest_version("MyPack")

        assert result == "2.0.0"
        mock_session.client.assert_called_once_with("s3", verify=True)
        mock_client.list_objects_v2.assert_called_once_with(
            Bucket="my-artifacts-bucket",
            Prefix="content/packs/MyPack/",
            Delimiter="/",
        )

    def test_single_version(self) -> None:
        provider = _make_provider()
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_client.list_objects_v2.return_value = {
            "CommonPrefixes": [
                {"Prefix": "content/packs/MyPack/1.0.0/"},
            ],
        }
        mock_session.client.return_value = mock_client
        provider._session = mock_session

        result = provider.get_latest_version("MyPack")

        assert result == "1.0.0"

    def test_no_versions_raises(self) -> None:
        provider = _make_provider()
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_client.list_objects_v2.return_value = {}
        mock_session.client.return_value = mock_client
        provider._session = mock_session

        with pytest.raises(ValueError):
            provider.get_latest_version("MyPack")

    def test_respects_verify_ssl(self) -> None:
        provider = _make_provider(verify_ssl=False)
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_client.list_objects_v2.return_value = {
            "CommonPrefixes": [{"Prefix": "content/packs/MyPack/1.0.0/"}],
        }
        mock_session.client.return_value = mock_client
        provider._session = mock_session

        provider.get_latest_version("MyPack")

        mock_session.client.assert_called_once_with("s3", verify=False)
