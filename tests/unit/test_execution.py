"""Unit tests for the Execution domain class (``xsoar_cli.xsoar_client.execution``).

``resolve_playground_id`` and ``execute_command`` are implemented and tested
against mocked demisto-py responses. ``execute_playbook`` is still a placeholder
that raises ``NotImplementedError``; that test pins the contract.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from xsoar_cli.xsoar_client.execution import Execution, build_command_string


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


class TestBuildCommandString:
    def test_no_args(self) -> None:
        assert build_command_string("MyScript", {}) == "!MyScript"

    def test_leading_bang_preserved(self) -> None:
        assert build_command_string("!whois", {}) == "!whois"

    def test_simple_args(self) -> None:
        assert build_command_string("MyScript", {"a": "1", "b": "2"}) == "!MyScript a=1 b=2"

    def test_whitespace_value_quoted(self) -> None:
        assert build_command_string("MyScript", {"q": "hello world"}) == '!MyScript q="hello world"'

    def test_embedded_quote_escaped(self) -> None:
        assert build_command_string("MyScript", {"q": 'a "b" c'}) == '!MyScript q="a \\"b\\" c"'

    def test_value_without_whitespace_not_quoted(self) -> None:
        assert build_command_string("MyScript", {"url": "https://example.com"}) == "!MyScript url=https://example.com"


class TestExecuteCommand:
    def test_sync_returns_wrapped_entries(self, mock_client: MagicMock) -> None:
        entry_a = SimpleNamespace(to_dict=lambda: {"id": "1@x", "contents": "a"})
        entry_b = SimpleNamespace(to_dict=lambda: {"id": "2@x", "contents": "b"})
        mock_client.demisto_py_instance.investigation_add_entries_sync.return_value = [entry_a, entry_b]

        execution = Execution(mock_client)
        result = execution.execute_command("MyScript", {"a": "1"}, "playground-id", mode="sync")

        assert result == {"entries": [{"id": "1@x", "contents": "a"}, {"id": "2@x", "contents": "b"}]}
        update_entry = mock_client.demisto_py_instance.investigation_add_entries_sync.call_args.kwargs["update_entry"]
        assert update_entry.investigation_id == "playground-id"
        assert update_entry.data == "!MyScript a=1"

    def test_sync_is_default_mode(self, mock_client: MagicMock) -> None:
        mock_client.demisto_py_instance.investigation_add_entries_sync.return_value = []

        execution = Execution(mock_client)
        execution.execute_command("MyScript", {}, "playground-id")

        mock_client.demisto_py_instance.investigation_add_entries_sync.assert_called_once()
        mock_client.demisto_py_instance.investigation_add_entry_handler.assert_not_called()

    def test_sync_handles_none_result(self, mock_client: MagicMock) -> None:
        mock_client.demisto_py_instance.investigation_add_entries_sync.return_value = None

        execution = Execution(mock_client)
        result = execution.execute_command("MyScript", {}, "playground-id", mode="sync")

        assert result == {"entries": []}

    def test_async_returns_wrapped_entry(self, mock_client: MagicMock) -> None:
        entry = SimpleNamespace(id="1@x", to_dict=lambda: {"id": "1@x"})
        mock_client.demisto_py_instance.investigation_add_entry_handler.return_value = entry

        execution = Execution(mock_client)
        result = execution.execute_command("MyScript", {}, "playground-id", mode="async")

        assert result == {"entry": {"id": "1@x"}}
        mock_client.demisto_py_instance.investigation_add_entries_sync.assert_not_called()

    def test_invalid_mode_raises_value_error(self, mock_client: MagicMock) -> None:
        execution = Execution(mock_client)
        with pytest.raises(ValueError, match="Invalid execution mode"):
            execution.execute_command("MyScript", {}, "playground-id", mode="bogus")


class TestExecutePlaybook:
    def test_raises_not_implemented(self, mock_client: MagicMock) -> None:
        execution = Execution(mock_client)
        with pytest.raises(NotImplementedError):
            execution.execute_playbook("My Playbook", "playground-id")
