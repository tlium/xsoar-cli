"""CLI integration tests for the ``playbook`` command group."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tests.cli.conftest import InvokeHelper


class TestPlaybookGroup:
    def test_shows_help(self, invoke: InvokeHelper) -> None:
        result = invoke(["playbook"])
        assert result.exit_code == 0

    def test_help_flag(self, invoke: InvokeHelper) -> None:
        result = invoke(["playbook", "--help"])
        assert result.exit_code == 0
