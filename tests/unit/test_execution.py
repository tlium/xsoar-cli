"""Unit tests for the Execution domain class (``xsoar_cli.xsoar_client.execution``).

All methods are currently placeholders that raise ``NotImplementedError``.
These tests pin that contract so the placeholders are not accidentally left
half-implemented or silently changed.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from xsoar_cli.xsoar_client.execution import Execution


class TestResolvePlaygroundId:
    def test_raises_not_implemented(self, mock_client: MagicMock) -> None:
        execution = Execution(mock_client)
        with pytest.raises(NotImplementedError):
            execution.resolve_playground_id()


class TestExecuteCommand:
    def test_raises_not_implemented(self, mock_client: MagicMock) -> None:
        execution = Execution(mock_client)
        with pytest.raises(NotImplementedError):
            execution.execute_command("MyScript", {"arg1": "val1"}, "playground-id")


class TestExecutePlaybook:
    def test_raises_not_implemented(self, mock_client: MagicMock) -> None:
        execution = Execution(mock_client)
        with pytest.raises(NotImplementedError):
            execution.execute_playbook("My Playbook", "playground-id")
