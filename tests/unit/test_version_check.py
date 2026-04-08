"""Unit tests for version check utilities (``xsoar_cli.utilities.version_check``).

Functions under test interact with ``importlib.metadata``, ``requests``, and
``packaging.version``. All external calls are mocked.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from packaging.version import Version

from xsoar_cli.utilities.version_check import (
    check_for_update,
    get_installed_version,
    get_latest_version,
    is_pypi_install,
)

# ===========================================================================
# is_pypi_install
# ===========================================================================


class TestIsPypiInstall:
    def test_returns_true_when_no_direct_url(self) -> None:
        dist = MagicMock()
        dist.read_text.return_value = None
        with patch("xsoar_cli.utilities.version_check.importlib.metadata.distribution", return_value=dist):
            assert is_pypi_install("some-package") is True
        dist.read_text.assert_called_once_with("direct_url.json")

    def test_returns_false_when_direct_url_present(self) -> None:
        dist = MagicMock()
        dist.read_text.return_value = '{"url": "file:///local/path"}'
        with patch("xsoar_cli.utilities.version_check.importlib.metadata.distribution", return_value=dist):
            assert is_pypi_install("some-package") is False


# ===========================================================================
# get_installed_version
# ===========================================================================


class TestGetInstalledVersion:
    def test_returns_parsed_version(self) -> None:
        dist = MagicMock()
        dist.version = "1.2.3"
        with patch("xsoar_cli.utilities.version_check.importlib.metadata.distribution", return_value=dist):
            result = get_installed_version("some-package")
        assert result == Version("1.2.3")

    def test_handles_prerelease_version(self) -> None:
        dist = MagicMock()
        dist.version = "2.0.0a1"
        with patch("xsoar_cli.utilities.version_check.importlib.metadata.distribution", return_value=dist):
            result = get_installed_version("some-package")
        assert result == Version("2.0.0a1")
        assert result.is_prerelease


# ===========================================================================
# get_latest_version
# ===========================================================================


class TestGetLatestVersion:
    def test_returns_latest_stable(self) -> None:
        response = MagicMock()
        response.json.return_value = {
            "versions": ["0.9.0", "1.0.0", "1.1.0", "1.2.0a1"],
        }
        with patch("requests.get", return_value=response) as mock_get:
            result = get_latest_version("xsoar-cli")
        assert result == Version("1.1.0")
        mock_get.assert_called_once_with(
            "https://pypi.org/simple/xsoar-cli/",
            headers={"Accept": "application/vnd.pypi.simple.v1+json"},
            timeout=3,
        )

    def test_falls_back_to_prerelease_when_no_stable(self) -> None:
        response = MagicMock()
        response.json.return_value = {
            "versions": ["1.0.0a1", "1.0.0b2", "1.0.0rc1"],
        }
        with patch("requests.get", return_value=response):
            result = get_latest_version("xsoar-cli")
        assert result == Version("1.0.0rc1")

    def test_calls_raise_for_status(self) -> None:
        response = MagicMock()
        response.json.return_value = {"versions": ["1.0.0"]}
        with patch("requests.get", return_value=response):
            get_latest_version("xsoar-cli")
        response.raise_for_status.assert_called_once()


# ===========================================================================
# check_for_update
# ===========================================================================


class TestCheckForUpdate:
    def test_none_config_skips(self) -> None:
        assert check_for_update(None) is None

    def test_skip_version_check_true_skips(self) -> None:
        assert check_for_update({"skip_version_check": True}) is None

    def test_skip_version_check_absent_defaults_to_skip(self) -> None:
        assert check_for_update({}) is None

    def test_non_pypi_install_skips(self) -> None:
        config = {"skip_version_check": False}
        with (
            patch("xsoar_cli.utilities.version_check.is_pypi_install", return_value=False),
            patch("xsoar_cli.utilities.version_check.get_installed_version", return_value=Version("1.0.0")),
        ):
            assert check_for_update(config) is None

    def test_update_available(self) -> None:
        config = {"skip_version_check": False}
        with (
            patch("xsoar_cli.utilities.version_check.is_pypi_install", return_value=True),
            patch("xsoar_cli.utilities.version_check.get_installed_version", return_value=Version("1.0.0")),
            patch("xsoar_cli.utilities.version_check.get_latest_version", return_value=Version("1.2.0")),
        ):
            result = check_for_update(config)
        assert result is not None
        assert "1.0.0" in result
        assert "1.2.0" in result

    def test_no_update_available(self) -> None:
        config = {"skip_version_check": False}
        with (
            patch("xsoar_cli.utilities.version_check.is_pypi_install", return_value=True),
            patch("xsoar_cli.utilities.version_check.get_installed_version", return_value=Version("1.2.0")),
            patch("xsoar_cli.utilities.version_check.get_latest_version", return_value=Version("1.2.0")),
        ):
            assert check_for_update(config) is None

    def test_installed_newer_than_latest(self) -> None:
        config = {"skip_version_check": False}
        with (
            patch("xsoar_cli.utilities.version_check.is_pypi_install", return_value=True),
            patch("xsoar_cli.utilities.version_check.get_installed_version", return_value=Version("2.0.0")),
            patch("xsoar_cli.utilities.version_check.get_latest_version", return_value=Version("1.2.0")),
        ):
            assert check_for_update(config) is None
