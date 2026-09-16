"""CLI integration tests for the ``pack`` command group."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tests.cli.conftest import InvokeHelper


class TestPackGroup:
    def test_shows_help(self, invoke: InvokeHelper) -> None:
        result = invoke(["pack"])
        assert result.exit_code == 0

    def test_help_flag(self, invoke: InvokeHelper) -> None:
        result = invoke(["pack", "--help"])
        assert result.exit_code == 0


class TestPackGetOutdated:
    """Tests for ``pack get-outdated``."""

    def test_reports_orphan_custom_pack_and_lists_outdated(self, invoke: InvokeHelper, mock_xsoar_env) -> None:
        """Regression test: an orphan custom pack (installed on the server but
        missing from the artifacts repo) is surfaced in the warning list and
        does not cause a formatting crash on ``pack['latest']``."""
        from xsoar_cli.xsoar_client.packs import OutdatedResult

        mock_xsoar_env.client.packs.get_outdated.return_value = OutdatedResult(
            outdated=[
                {
                    "id": "CommonScripts",
                    "currentVersion": "1.14.20",
                    "latest": "1.15.0",
                    "author": "Upstream",
                },
            ],
            skipped=["OrphanPack"],
        )

        result = invoke(["pack", "get-outdated"])

        assert result.exit_code == 0, result.output
        assert "OrphanPack" in result.output
        assert "installed but not found in artifacts repo" in result.output
        assert "CommonScripts" in result.output
        assert "1.15.0" in result.output
