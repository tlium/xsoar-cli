"""CLI integration tests for the ``manifest`` command group."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from tests.cli.conftest import InvokeHelper


class TestManifestGroup:
    def test_shows_help(self, invoke: InvokeHelper) -> None:
        result = invoke(["manifest"])
        assert result.exit_code == 0

    def test_help_flag(self, invoke: InvokeHelper) -> None:
        result = invoke(["manifest", "--help"])
        assert result.exit_code == 0


class TestManifestValidate:
    """Tests for ``manifest validate`` (full validation, default behavior)."""

    def test_valid_manifest_all_packs_reachable(self, invoke: InvokeHelper, mock_xsoar_env, tmp_path: Path) -> None:
        manifest = tmp_path / "xsoar_config.json"
        manifest.write_text(
            json.dumps(
                {
                    "custom_packs": [{"id": "MyOrg_EDR", "version": "2.0.0"}],
                    "marketplace_packs": [{"id": "CommonScripts", "version": "1.14.20"}],
                }
            )
        )
        mock_xsoar_env.client.packs.is_available.return_value = True
        result = invoke(["manifest", "validate", str(manifest)])
        assert result.exit_code == 0
        assert "Manifest is valid JSON" in result.output
        assert "all packs are reachable" in result.output

    def test_invalid_json(self, invoke: InvokeHelper, mock_xsoar_env, tmp_path: Path) -> None:
        manifest = tmp_path / "xsoar_config.json"
        manifest.write_text("{ invalid json }")
        result = invoke(["manifest", "validate", str(manifest)])
        assert result.exit_code != 0
        assert "Failed to decode JSON" in result.output

    def test_invalid_manifest_keys(self, invoke: InvokeHelper, mock_xsoar_env, tmp_path: Path) -> None:
        manifest = tmp_path / "xsoar_config.json"
        manifest.write_text(
            json.dumps(
                {
                    "custom_packs": [{"id": "MyOrg_EDR", "version": "2.0.0", "bogus_key": "value"}],
                    "marketplace_packs": [],
                }
            )
        )
        result = invoke(["manifest", "validate", str(manifest)])
        assert result.exit_code != 0
        assert "invalid key" in result.output

    def test_marketplace_pack_not_reachable(self, invoke: InvokeHelper, mock_xsoar_env, tmp_path: Path) -> None:
        manifest = tmp_path / "xsoar_config.json"
        manifest.write_text(
            json.dumps(
                {
                    "custom_packs": [],
                    "marketplace_packs": [{"id": "CommonScripts", "version": "1.14.20"}],
                }
            )
        )
        mock_xsoar_env.client.packs.is_available.return_value = False
        result = invoke(["manifest", "validate", str(manifest)])
        assert result.exit_code != 0
        assert "Failed to find CommonScripts" in result.output

    def test_checks_both_custom_and_marketplace(self, invoke: InvokeHelper, mock_xsoar_env, tmp_path: Path) -> None:
        manifest = tmp_path / "xsoar_config.json"
        manifest.write_text(
            json.dumps(
                {
                    "custom_packs": [{"id": "MyOrg_EDR", "version": "2.0.0"}],
                    "marketplace_packs": [{"id": "CommonScripts", "version": "1.14.20"}],
                }
            )
        )
        mock_xsoar_env.client.packs.is_available.return_value = True
        result = invoke(["manifest", "validate", str(manifest)])
        assert result.exit_code == 0
        assert "Checking custom_packs availability" in result.output
        assert "Checking marketplace_packs availability" in result.output

    def test_validates_all_packs_by_default(self, invoke: InvokeHelper, mock_xsoar_env, tmp_path: Path) -> None:
        """Default behavior validates every pack, not just changed ones."""
        manifest = tmp_path / "xsoar_config.json"
        manifest.write_text(
            json.dumps(
                {
                    "custom_packs": [],
                    "marketplace_packs": [
                        {"id": "CommonScripts", "version": "1.14.20"},
                        {"id": "Phishing", "version": "3.6.1"},
                    ],
                }
            )
        )
        mock_xsoar_env.client.packs.is_available.return_value = True
        result = invoke(["manifest", "validate", str(manifest)])
        assert result.exit_code == 0
        # get_installed should not be called in full validation mode
        mock_xsoar_env.client.packs.get_installed.assert_not_called()
        # Both packs should be checked
        assert mock_xsoar_env.client.packs.is_available.call_count == 2


class TestManifestValidateOnlyChanged:
    """Tests for ``manifest validate --only-changed``."""

    def test_no_changes_skips_availability_check(self, invoke: InvokeHelper, mock_xsoar_env, tmp_path: Path) -> None:
        manifest = tmp_path / "xsoar_config.json"
        manifest.write_text(
            json.dumps(
                {
                    "custom_packs": [{"id": "MyOrg_EDR", "version": "2.0.0"}],
                    "marketplace_packs": [{"id": "CommonScripts", "version": "1.14.20"}],
                }
            )
        )
        mock_xsoar_env.client.packs.get_installed.return_value = [
            {"id": "MyOrg_EDR", "currentVersion": "2.0.0"},
            {"id": "CommonScripts", "currentVersion": "1.14.20"},
        ]
        result = invoke(["manifest", "validate", "--only-changed", str(manifest)])
        assert result.exit_code == 0
        assert "no changes found" in result.output
        mock_xsoar_env.client.packs.is_available.assert_not_called()

    def test_version_change_triggers_availability_check(self, invoke: InvokeHelper, mock_xsoar_env, tmp_path: Path) -> None:
        manifest = tmp_path / "xsoar_config.json"
        manifest.write_text(
            json.dumps(
                {
                    "custom_packs": [],
                    "marketplace_packs": [
                        {"id": "CommonScripts", "version": "2.0.0"},
                        {"id": "Phishing", "version": "3.6.1"},
                    ],
                }
            )
        )
        mock_xsoar_env.client.packs.get_installed.return_value = [
            {"id": "CommonScripts", "currentVersion": "1.14.20"},
            {"id": "Phishing", "currentVersion": "3.6.1"},
        ]
        mock_xsoar_env.client.packs.is_available.return_value = True
        result = invoke(["manifest", "validate", "--only-changed", str(manifest)])
        assert result.exit_code == 0
        # Only CommonScripts should be checked (version changed), not Phishing
        mock_xsoar_env.client.packs.is_available.assert_called_once_with(
            pack_id="CommonScripts",
            version="2.0.0",
            custom=False,
        )

    def test_new_pack_triggers_availability_check(self, invoke: InvokeHelper, mock_xsoar_env, tmp_path: Path) -> None:
        manifest = tmp_path / "xsoar_config.json"
        manifest.write_text(
            json.dumps(
                {
                    "custom_packs": [],
                    "marketplace_packs": [{"id": "NewPack", "version": "1.0.0"}],
                }
            )
        )
        mock_xsoar_env.client.packs.get_installed.return_value = []
        mock_xsoar_env.client.packs.is_available.return_value = True
        result = invoke(["manifest", "validate", "--only-changed", str(manifest)])
        assert result.exit_code == 0
        mock_xsoar_env.client.packs.is_available.assert_called_once_with(
            pack_id="NewPack",
            version="1.0.0",
            custom=False,
        )

    def test_changed_pack_not_reachable(self, invoke: InvokeHelper, mock_xsoar_env, tmp_path: Path) -> None:
        manifest = tmp_path / "xsoar_config.json"
        manifest.write_text(
            json.dumps(
                {
                    "custom_packs": [],
                    "marketplace_packs": [{"id": "CommonScripts", "version": "2.0.0"}],
                }
            )
        )
        mock_xsoar_env.client.packs.get_installed.return_value = [
            {"id": "CommonScripts", "currentVersion": "1.14.20"},
        ]
        mock_xsoar_env.client.packs.is_available.return_value = False
        result = invoke(["manifest", "validate", "--only-changed", str(manifest)])
        assert result.exit_code != 0
        assert "Failed to find CommonScripts" in result.output

    def test_downgrade_triggers_availability_check(self, invoke: InvokeHelper, mock_xsoar_env, tmp_path: Path) -> None:
        manifest = tmp_path / "xsoar_config.json"
        manifest.write_text(
            json.dumps(
                {
                    "custom_packs": [],
                    "marketplace_packs": [{"id": "CommonScripts", "version": "1.0.0"}],
                }
            )
        )
        mock_xsoar_env.client.packs.get_installed.return_value = [
            {"id": "CommonScripts", "currentVersion": "2.0.0"},
        ]
        mock_xsoar_env.client.packs.is_available.return_value = True
        result = invoke(["manifest", "validate", "--only-changed", str(manifest)])
        assert result.exit_code == 0
        mock_xsoar_env.client.packs.is_available.assert_called_once_with(
            pack_id="CommonScripts",
            version="1.0.0",
            custom=False,
        )
