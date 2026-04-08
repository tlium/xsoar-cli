"""Unit tests for the Packs domain class (``xsoar_cli.xsoar_client.packs``).

Tests mock ``client.make_request``, ``client.resolve_endpoint``,
``client.artifact_provider``, ``client.demisto_py_instance``, and external
HTTP calls to verify that each Packs method behaves correctly.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from demisto_client.demisto_api.rest import ApiException
from requests.exceptions import HTTPError

from xsoar_cli.xsoar_client.packs import OutdatedResult, Packs

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_INSTALLED = [
    {"id": "CommonScripts", "currentVersion": "1.14.20", "name": "Common Scripts", "author": "Cortex XSOAR"},
    {"id": "Phishing", "currentVersion": "3.6.1", "name": "Phishing", "author": "Cortex XSOAR"},
    {"id": "MyOrg_EDR", "currentVersion": "2.0.0", "name": "MyOrg EDR Pack", "author": "MyOrg"},
    {"id": "EWS", "currentVersion": "2.4.8", "name": "EWS", "author": "Cortex XSOAR"},
]

_INSTALLED_EXPIRED = [
    {
        "id": "MyOrg_EDR",
        "currentVersion": "2.0.0",
        "name": "MyOrg EDR Pack",
        "author": "MyOrg",
        "updateAvailable": False,
        "changelog": {},
    },
    {
        "id": "Phishing",
        "currentVersion": "3.6.1",
        "name": "Phishing",
        "author": "Cortex XSOAR",
        "updateAvailable": True,
        "changelog": {
            "3.6.1": {"releaseNotes": "Bug fixes.", "released": "2024-03-01T00:00:00Z"},
            "3.7.0": {"releaseNotes": "New detection rules.", "released": "2024-06-01T00:00:00Z"},
            "3.7.1": {"releaseNotes": "Hotfix.", "released": "2024-06-15T00:00:00Z"},
        },
    },
    {
        "id": "EWS",
        "currentVersion": "2.4.8",
        "name": "EWS",
        "author": "Cortex XSOAR",
        "updateAvailable": False,
        "changelog": {
            "2.4.8": {"releaseNotes": "Maintenance release.", "released": "2024-02-01T00:00:00Z"},
        },
    },
]


def _mock_response(json_data: list | dict, *, status_code: int = 200) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data
    response.raise_for_status.return_value = None
    return response


# ===========================================================================
# Packs.get_installed
# ===========================================================================


class TestGetInstalled:
    def test_happy_path(self, mock_client: MagicMock) -> None:
        mock_client.resolve_endpoint.return_value = "/contentpacks/metadata/installed"
        mock_client.make_request.return_value = _mock_response(_INSTALLED)

        packs = Packs(mock_client)
        result = packs.get_installed()

        assert result == _INSTALLED
        mock_client.resolve_endpoint.assert_called_once_with(
            v6="/contentpacks/metadata/installed",
            v8="/xsoar/public/v1/contentpacks/metadata/installed",
        )
        mock_client.make_request.assert_called_once()

    def test_caching(self, mock_client: MagicMock) -> None:
        """Second call should return cached data without making a new request."""
        mock_client.resolve_endpoint.return_value = "/contentpacks/metadata/installed"
        mock_client.make_request.return_value = _mock_response(_INSTALLED)

        packs = Packs(mock_client)
        first = packs.get_installed()
        second = packs.get_installed()

        assert first is second
        mock_client.make_request.assert_called_once()

    def test_http_error_propagates(self, mock_client: MagicMock) -> None:
        mock_client.resolve_endpoint.return_value = "/contentpacks/metadata/installed"
        response = MagicMock()
        response.raise_for_status.side_effect = HTTPError("500 Server Error")
        mock_client.make_request.return_value = response

        packs = Packs(mock_client)
        with pytest.raises(HTTPError, match="500 Server Error"):
            packs.get_installed()


# ===========================================================================
# Packs.get_installed_expired
# ===========================================================================


class TestGetInstalledExpired:
    def test_happy_path(self, mock_client: MagicMock) -> None:
        mock_client.resolve_endpoint.return_value = "/contentpacks/installed-expired"
        mock_client.make_request.return_value = _mock_response(_INSTALLED_EXPIRED)

        packs = Packs(mock_client)
        result = packs.get_installed_expired()

        assert result == _INSTALLED_EXPIRED
        mock_client.resolve_endpoint.assert_called_once_with(
            v6="/contentpacks/installed-expired",
            v8="/xsoar/contentpacks/installed-expired",
        )

    def test_caching(self, mock_client: MagicMock) -> None:
        mock_client.resolve_endpoint.return_value = "/contentpacks/installed-expired"
        mock_client.make_request.return_value = _mock_response(_INSTALLED_EXPIRED)

        packs = Packs(mock_client)
        first = packs.get_installed_expired()
        second = packs.get_installed_expired()

        assert first is second
        mock_client.make_request.assert_called_once()

    def test_http_error_propagates(self, mock_client: MagicMock) -> None:
        mock_client.resolve_endpoint.return_value = "/contentpacks/installed-expired"
        response = MagicMock()
        response.raise_for_status.side_effect = HTTPError("500 Server Error")
        mock_client.make_request.return_value = response

        packs = Packs(mock_client)
        with pytest.raises(HTTPError, match="500 Server Error"):
            packs.get_installed_expired()


# ===========================================================================
# Packs.is_installed
# ===========================================================================


class TestIsInstalled:
    def _make_packs(self, mock_client: MagicMock) -> Packs:
        mock_client.resolve_endpoint.return_value = "/contentpacks/metadata/installed"
        mock_client.make_request.return_value = _mock_response(_INSTALLED)
        return Packs(mock_client)

    def test_existing_pack(self, mock_client: MagicMock) -> None:
        packs = self._make_packs(mock_client)
        assert packs.is_installed(pack_id="CommonScripts") is True

    def test_nonexistent_pack(self, mock_client: MagicMock) -> None:
        packs = self._make_packs(mock_client)
        assert packs.is_installed(pack_id="NonExistent") is False

    def test_matching_version(self, mock_client: MagicMock) -> None:
        packs = self._make_packs(mock_client)
        assert packs.is_installed(pack_id="CommonScripts", pack_version="1.14.20") is True

    def test_nonmatching_version(self, mock_client: MagicMock) -> None:
        packs = self._make_packs(mock_client)
        assert packs.is_installed(pack_id="CommonScripts", pack_version="99.0.0") is False

    def test_nonexistent_pack_with_version(self, mock_client: MagicMock) -> None:
        packs = self._make_packs(mock_client)
        assert packs.is_installed(pack_id="NonExistent", pack_version="1.0.0") is False


# ===========================================================================
# Packs.is_available
# ===========================================================================


class TestIsAvailable:
    def test_marketplace_pack_available(self, mock_client: MagicMock) -> None:
        mock_head = MagicMock()
        mock_head.status_code = 200
        with patch("xsoar_cli.xsoar_client.packs.requests.head", return_value=mock_head) as patched:
            packs = Packs(mock_client)
            result = packs.is_available(pack_id="CommonScripts", version="1.14.20", custom=False)

        assert result is True
        patched.assert_called_once()
        call_url = patched.call_args[0][0]
        assert "CommonScripts/1.14.20/CommonScripts.zip" in call_url

    def test_marketplace_pack_not_available(self, mock_client: MagicMock) -> None:
        mock_head = MagicMock()
        mock_head.status_code = 404
        with patch("xsoar_cli.xsoar_client.packs.requests.head", return_value=mock_head):
            packs = Packs(mock_client)
            result = packs.is_available(pack_id="CommonScripts", version="99.0.0", custom=False)

        assert result is False

    def test_custom_pack_available(self, mock_client: MagicMock) -> None:
        provider = MagicMock()
        provider.is_available.return_value = True
        mock_client.artifact_provider = provider

        packs = Packs(mock_client)
        result = packs.is_available(pack_id="MyOrg_EDR", version="2.0.0", custom=True)

        assert result is True
        provider.is_available.assert_called_once_with(pack_id="MyOrg_EDR", pack_version="2.0.0")

    def test_custom_pack_not_available(self, mock_client: MagicMock) -> None:
        provider = MagicMock()
        provider.is_available.return_value = False
        mock_client.artifact_provider = provider

        packs = Packs(mock_client)
        result = packs.is_available(pack_id="MyOrg_EDR", version="99.0.0", custom=True)

        assert result is False

    def test_custom_pack_no_provider_raises(self, mock_client: MagicMock) -> None:
        mock_client.artifact_provider = None

        packs = Packs(mock_client)
        with pytest.raises(RuntimeError, match="No artifact provider configured"):
            packs.is_available(pack_id="MyOrg_EDR", version="2.0.0", custom=True)


# ===========================================================================
# Packs.download
# ===========================================================================


class TestDownload:
    def test_marketplace_pack(self, mock_client: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.content = b"zip-data"
        mock_response.raise_for_status.return_value = None
        with patch("xsoar_cli.xsoar_client.packs.requests.get", return_value=mock_response) as patched:
            packs = Packs(mock_client)
            result = packs.download("CommonScripts", "1.14.20", custom=False)

        assert result == b"zip-data"
        call_url = patched.call_args[0][0]
        assert "CommonScripts/1.14.20/CommonScripts.zip" in call_url

    def test_custom_pack(self, mock_client: MagicMock) -> None:
        provider = MagicMock()
        provider.download.return_value = b"custom-zip-data"
        mock_client.artifact_provider = provider

        packs = Packs(mock_client)
        result = packs.download("MyOrg_EDR", "2.0.0", custom=True)

        assert result == b"custom-zip-data"
        provider.download.assert_called_once_with(pack_id="MyOrg_EDR", pack_version="2.0.0")

    def test_custom_pack_no_provider_raises(self, mock_client: MagicMock) -> None:
        mock_client.artifact_provider = None

        packs = Packs(mock_client)
        with pytest.raises(RuntimeError, match="No artifact provider configured"):
            packs.download("MyOrg_EDR", "2.0.0", custom=True)

    def test_marketplace_http_error_propagates(self, mock_client: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = HTTPError("404 Not Found")
        with patch("xsoar_cli.xsoar_client.packs.requests.get", return_value=mock_response):
            packs = Packs(mock_client)
            with pytest.raises(HTTPError, match="404 Not Found"):
                packs.download("NonExistent", "1.0.0", custom=False)


# ===========================================================================
# Packs.deploy_zip
# ===========================================================================


class TestDeployZip:
    def test_happy_path(self, mock_client: MagicMock) -> None:
        packs = Packs(mock_client)
        result = packs.deploy_zip(filepath="/tmp/pack.zip")

        assert result is True
        mock_client.demisto_py_instance.upload_content_packs.assert_called_once_with(
            "/tmp/pack.zip",
            skip_validation="false",
            skip_verify="false",
        )

    def test_skip_validation(self, mock_client: MagicMock) -> None:
        packs = Packs(mock_client)
        packs.deploy_zip(filepath="/tmp/pack.zip", skip_validation=True)

        mock_client.demisto_py_instance.upload_content_packs.assert_called_once_with(
            "/tmp/pack.zip",
            skip_validation="true",
            skip_verify="false",
        )

    def test_skip_verify(self, mock_client: MagicMock) -> None:
        packs = Packs(mock_client)
        packs.deploy_zip(filepath="/tmp/pack.zip", skip_verify=True)

        mock_client.demisto_py_instance.upload_content_packs.assert_called_once_with(
            "/tmp/pack.zip",
            skip_validation="false",
            skip_verify="true",
        )


# ===========================================================================
# Packs.deploy
# ===========================================================================


class TestDeploy:
    def test_marketplace_pack(self, mock_client: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.content = b"zip-data"
        mock_response.raise_for_status.return_value = None
        with patch("xsoar_cli.xsoar_client.packs.requests.get", return_value=mock_response):
            packs = Packs(mock_client)
            result = packs.deploy(pack_id="CommonScripts", pack_version="1.14.20", custom=False)

        assert result is True
        mock_client.demisto_py_instance.upload_content_packs.assert_called_once()
        call_kwargs = mock_client.demisto_py_instance.upload_content_packs.call_args
        assert call_kwargs[1]["skip_verify"] == "false"

    def test_custom_pack_skips_verify(self, mock_client: MagicMock) -> None:
        provider = MagicMock()
        provider.download.return_value = b"custom-zip-data"
        mock_client.artifact_provider = provider

        packs = Packs(mock_client)
        result = packs.deploy(pack_id="MyOrg_EDR", pack_version="2.0.0", custom=True)

        assert result is True
        call_kwargs = mock_client.demisto_py_instance.upload_content_packs.call_args
        assert call_kwargs[1]["skip_verify"] == "true"

    def test_upload_failure_raises_runtime_error(self, mock_client: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.content = b"zip-data"
        mock_response.raise_for_status.return_value = None
        mock_client.demisto_py_instance.upload_content_packs.side_effect = ApiException(status=500, reason="Server Error")

        with patch("xsoar_cli.xsoar_client.packs.requests.get", return_value=mock_response):
            packs = Packs(mock_client)
            with pytest.raises(RuntimeError, match="upload_content_packs"):
                packs.deploy(pack_id="CommonScripts", pack_version="1.14.20", custom=False)

    def test_temp_file_cleaned_up_on_success(self, mock_client: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.content = b"zip-data"
        mock_response.raise_for_status.return_value = None

        with patch("xsoar_cli.xsoar_client.packs.requests.get", return_value=mock_response):
            packs = Packs(mock_client)
            packs.deploy(pack_id="CommonScripts", pack_version="1.14.20", custom=False)

        # The upload call should have received a path ending in .zip
        filepath = mock_client.demisto_py_instance.upload_content_packs.call_args[0][0]
        assert filepath.endswith(".zip")

    def test_temp_file_cleaned_up_on_failure(self, mock_client: MagicMock) -> None:
        """Temp file is removed even when upload raises."""
        mock_response = MagicMock()
        mock_response.content = b"zip-data"
        mock_response.raise_for_status.return_value = None
        mock_client.demisto_py_instance.upload_content_packs.side_effect = ApiException(status=500, reason="Fail")

        with (
            patch("xsoar_cli.xsoar_client.packs.requests.get", return_value=mock_response),
            patch("xsoar_cli.xsoar_client.packs.Path.unlink") as mock_unlink,
        ):
            packs = Packs(mock_client)
            with pytest.raises(RuntimeError):
                packs.deploy(pack_id="CommonScripts", pack_version="1.14.20", custom=False)

        mock_unlink.assert_called_once_with(missing_ok=True)


# ===========================================================================
# Packs.get_outdated
# ===========================================================================


class TestGetOutdated:
    def test_marketplace_pack_with_update(self, mock_client: MagicMock) -> None:
        mock_client.resolve_endpoint.return_value = "/contentpacks/installed-expired"
        mock_client.make_request.return_value = _mock_response(_INSTALLED_EXPIRED)

        packs = Packs(mock_client, custom_pack_authors=["MyOrg"])
        mock_client.artifact_provider = MagicMock()
        mock_client.artifact_provider.get_latest_version.return_value = "2.1.0"

        result = packs.get_outdated()

        assert isinstance(result, OutdatedResult)
        marketplace = [p for p in result.outdated if p["author"] == "Upstream"]
        assert len(marketplace) == 1
        assert marketplace[0]["id"] == "Phishing"
        assert marketplace[0]["latest"] == "3.7.1"

    def test_custom_pack_with_update(self, mock_client: MagicMock) -> None:
        mock_client.resolve_endpoint.return_value = "/contentpacks/installed-expired"
        mock_client.make_request.return_value = _mock_response(_INSTALLED_EXPIRED)

        provider = MagicMock()
        provider.get_latest_version.return_value = "2.1.0"
        mock_client.artifact_provider = provider

        packs = Packs(mock_client, custom_pack_authors=["MyOrg"])
        result = packs.get_outdated()

        custom = [p for p in result.outdated if p["author"] == "MyOrg"]
        assert len(custom) == 1
        assert custom[0]["id"] == "MyOrg_EDR"
        assert custom[0]["latest"] == "2.1.0"
        assert custom[0]["currentVersion"] == "2.0.0"

    def test_custom_pack_same_version_not_outdated(self, mock_client: MagicMock) -> None:
        mock_client.resolve_endpoint.return_value = "/contentpacks/installed-expired"
        mock_client.make_request.return_value = _mock_response(_INSTALLED_EXPIRED)

        provider = MagicMock()
        provider.get_latest_version.return_value = "2.0.0"
        mock_client.artifact_provider = provider

        packs = Packs(mock_client, custom_pack_authors=["MyOrg"])
        result = packs.get_outdated()

        custom = [p for p in result.outdated if p["author"] == "MyOrg"]
        assert len(custom) == 0

    def test_custom_pack_not_found_in_artifact_repo(self, mock_client: MagicMock) -> None:
        mock_client.resolve_endpoint.return_value = "/contentpacks/installed-expired"
        mock_client.make_request.return_value = _mock_response(_INSTALLED_EXPIRED)

        provider = MagicMock()
        provider.get_latest_version.side_effect = ValueError("Pack not found")
        mock_client.artifact_provider = provider

        packs = Packs(mock_client, custom_pack_authors=["MyOrg"])
        result = packs.get_outdated()

        assert "MyOrg_EDR" in result.skipped
        custom = [p for p in result.outdated if p.get("id") == "MyOrg_EDR"]
        assert len(custom) == 0

    def test_no_artifact_provider_for_custom_packs_raises(self, mock_client: MagicMock) -> None:
        mock_client.resolve_endpoint.return_value = "/contentpacks/installed-expired"
        mock_client.make_request.return_value = _mock_response(_INSTALLED_EXPIRED)
        mock_client.artifact_provider = None

        packs = Packs(mock_client, custom_pack_authors=["MyOrg"])
        with pytest.raises(RuntimeError, match="No artifact provider configured"):
            packs.get_outdated()

    def test_marketplace_pack_update_not_available_skipped(self, mock_client: MagicMock) -> None:
        """EWS has updateAvailable=False, so it should not appear in outdated."""
        mock_client.resolve_endpoint.return_value = "/contentpacks/installed-expired"
        mock_client.make_request.return_value = _mock_response(_INSTALLED_EXPIRED)

        provider = MagicMock()
        provider.get_latest_version.return_value = "2.1.0"
        mock_client.artifact_provider = provider

        packs = Packs(mock_client, custom_pack_authors=["MyOrg"])
        result = packs.get_outdated()

        ews = [p for p in result.outdated if p["id"] == "EWS"]
        assert len(ews) == 0

    def test_no_custom_pack_authors_treats_all_as_marketplace(self, mock_client: MagicMock) -> None:
        mock_client.resolve_endpoint.return_value = "/contentpacks/installed-expired"
        mock_client.make_request.return_value = _mock_response(_INSTALLED_EXPIRED)

        packs = Packs(mock_client)
        result = packs.get_outdated()

        # MyOrg_EDR has updateAvailable=False, so it is skipped as marketplace
        ids = [p["id"] for p in result.outdated]
        assert "MyOrg_EDR" not in ids
        # Phishing has updateAvailable=True, so it should be present
        assert "Phishing" in ids


# ===========================================================================
# Packs.get_latest_custom_version
# ===========================================================================


class TestGetLatestCustomVersion:
    def test_happy_path(self, mock_client: MagicMock) -> None:
        provider = MagicMock()
        provider.get_latest_version.return_value = "2.1.0"
        mock_client.artifact_provider = provider

        packs = Packs(mock_client)
        result = packs.get_latest_custom_version("MyOrg_EDR")

        assert result == "2.1.0"
        provider.get_latest_version.assert_called_once_with("MyOrg_EDR")

    def test_no_provider_raises(self, mock_client: MagicMock) -> None:
        mock_client.artifact_provider = None

        packs = Packs(mock_client)
        with pytest.raises(RuntimeError, match="No artifact provider configured"):
            packs.get_latest_custom_version("MyOrg_EDR")


# ===========================================================================
# Packs.delete
# ===========================================================================


class TestDelete:
    def test_raises_not_implemented(self, mock_client: MagicMock) -> None:
        packs = Packs(mock_client)
        with pytest.raises(NotImplementedError):
            packs.delete(pack_id="CommonScripts")
