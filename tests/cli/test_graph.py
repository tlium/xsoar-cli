"""CLI integration tests for the ``graph`` command group."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tests.cli.conftest import InvokeHelper


class TestGraphGroup:
    def test_shows_help(self, invoke: InvokeHelper) -> None:
        result = invoke(["graph"])
        assert result.exit_code == 0

    def test_help_flag(self, invoke: InvokeHelper) -> None:
        result = invoke(["graph", "--help"])
        assert result.exit_code == 0
