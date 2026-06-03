"""Unit tests for the Execution domain class (``xsoar_cli.xsoar_client.execution``).

``resolve_playground_id`` is implemented and tested against mocked demisto-py
responses. ``execute_command`` and ``execute_playbook`` are still placeholders
that raise ``NotImplementedError``; those tests pin that contract.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from xsoar_cli.xsoar_client.execution import Execution


def _search_result(*, total: int, ids: list[str], creating_user_ids: list[str] | None = None) -> SimpleNamespace:
    """Build a stand-in for a demisto-py search_investigations response.

    ``data`` holds objects exposing ``id`` and ``creating_user_id`` attributes,
    matching the SDK investigation model fields used by ``resolve_playground_id``.
    """
    creating = creating_user_ids if creating_user_ids is not None else [None] * len(ids)
    data = [SimpleNamespace(id=item_id, creating_user_id=user) for item_id, user in zip(ids, creating)]
    return SimpleNamespace(total=total, data=data)


class TestResolvePlaygroundId:
    def test_single_playground(self, mock_client: MagicMock) -> None:
        mock_client.demisto_py_instance.search_investigations.return_value = _search_result(total=1, ids=["pg-1"])

        execution = Execution(mock_client)
        assert execution.resolve_playground_id() == "pg-1"

    def test_no_playground_raises_runtime_error(self, mock_client: MagicMock) -> None:
        mock_client.demisto_py_instance.search_investigations.return_value = _search_result(total=0, ids=[])

        execution = Execution(mock_client)
        with pytest.raises(RuntimeError, match="No playground investigation found"):
            execution.resolve_playground_id()

    def test_multiple_playgrounds_filtered_by_user(self, mock_client: MagicMock) -> None:
        # Two playgrounds visible to the token on a single page; only one belongs
        # to the current user ("alice").
        mock_client.demisto_py_instance.search_investigations.return_value = _search_result(
            total=2,
            ids=["pg-alice", "pg-bob"],
            creating_user_ids=["alice", "bob"],
        )
        mock_client.demisto_py_instance.generic_request.return_value = ({"username": "alice"}, 200, None)

        execution = Execution(mock_client)
        assert execution.resolve_playground_id() == "pg-alice"

    def test_multiple_playgrounds_username_lookup_fails(self, mock_client: MagicMock) -> None:
        mock_client.demisto_py_instance.search_investigations.return_value = _search_result(
            total=2,
            ids=["pg-alice", "pg-bob"],
            creating_user_ids=["alice", "bob"],
        )
        mock_client.demisto_py_instance.generic_request.return_value = ({}, 403, None)

        execution = Execution(mock_client)
        with pytest.raises(RuntimeError, match="Could not determine the current user"):
            execution.resolve_playground_id()

    def test_multiple_playgrounds_ambiguous_raises(self, mock_client: MagicMock) -> None:
        # Both playgrounds belong to the current user, leaving the result ambiguous.
        mock_client.demisto_py_instance.search_investigations.return_value = _search_result(
            total=2,
            ids=["pg-a", "pg-b"],
            creating_user_ids=["alice", "alice"],
        )
        mock_client.demisto_py_instance.generic_request.return_value = ({"username": "alice"}, 200, None)

        execution = Execution(mock_client)
        with pytest.raises(RuntimeError, match="Expected exactly one playground"):
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
