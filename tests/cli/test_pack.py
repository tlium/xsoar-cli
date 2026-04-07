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
