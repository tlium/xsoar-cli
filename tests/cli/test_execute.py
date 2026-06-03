"""CLI integration tests for the ``execute`` command group."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from xsoar_cli.commands.execute.commands import parse_arg_tokens

if TYPE_CHECKING:
    from tests.cli.conftest import InvokeHelper


class TestExecuteGroup:
    """The bare ``execute`` command and its help output."""

    def test_shows_help(self, invoke: InvokeHelper) -> None:
        result = invoke(["execute"])
        assert result.exit_code == 0

    def test_help_flag(self, invoke: InvokeHelper) -> None:
        result = invoke(["execute", "--help"])
        assert result.exit_code == 0


class TestParseArgTokens:
    """Direct tests for the ``key=value`` token parser used by ``execute command``."""

    def test_empty(self) -> None:
        assert parse_arg_tokens(()) == {}

    def test_single_pair(self) -> None:
        assert parse_arg_tokens(("arg1=val1",)) == {"arg1": "val1"}

    def test_multiple_pairs(self) -> None:
        assert parse_arg_tokens(("a=1", "b=2")) == {"a": "1", "b": "2"}

    def test_value_with_equals(self) -> None:
        assert parse_arg_tokens(("query=a=b",)) == {"query": "a=b"}

    def test_strips_whitespace(self) -> None:
        assert parse_arg_tokens((" a = 1 ",)) == {"a": "1"}

    def test_malformed_token_raises(self) -> None:
        with pytest.raises(ValueError, match="Malformed argument"):
            parse_arg_tokens(("notapair",))


class TestExecuteCommand:
    """Tests for ``execute command``."""

    def test_success_playground(self, invoke: InvokeHelper, mock_execute_env) -> None:
        result = invoke(["execute", "command", "MyScript", "arg1=val1"])
        assert result.exit_code == 0
        mock_execute_env.resolve_playground_id.assert_called_once()
        mock_execute_env.execute_command.assert_called_once_with("MyScript", {"arg1": "val1"}, "playground-id")

    def test_success_with_case_id(self, invoke: InvokeHelper, mock_execute_env) -> None:
        result = invoke(["execute", "command", "MyScript", "--case-id", "12345"])
        assert result.exit_code == 0
        mock_execute_env.resolve_playground_id.assert_not_called()
        mock_execute_env.execute_command.assert_called_once_with("MyScript", {}, "12345")

    def test_multiple_args(self, invoke: InvokeHelper, mock_execute_env) -> None:
        result = invoke(["execute", "command", "MyScript", "a=1", "b=2"])
        assert result.exit_code == 0
        mock_execute_env.execute_command.assert_called_once_with("MyScript", {"a": "1", "b": "2"}, "playground-id")

    def test_malformed_arg_exits_nonzero(self, invoke: InvokeHelper, mock_execute_env) -> None:
        result = invoke(["execute", "command", "MyScript", "notapair"])
        assert result.exit_code == 1
        assert "Malformed argument" in result.output
        mock_execute_env.execute_command.assert_not_called()

    def test_missing_name_exits_usage_error(self, invoke: InvokeHelper, mock_execute_env) -> None:
        result = invoke(["execute", "command"])
        assert result.exit_code == 2

    def test_output_level_raw(self, invoke: InvokeHelper, mock_execute_env) -> None:
        result = invoke(["execute", "command", "MyScript", "--output-level", "raw"])
        assert result.exit_code == 0
        assert "result" in result.output

    def test_invalid_output_level_exits_usage_error(self, invoke: InvokeHelper, mock_execute_env) -> None:
        result = invoke(["execute", "command", "MyScript", "--output-level", "bogus"])
        assert result.exit_code == 2


class TestPlaygroundResolutionErrors:
    """Error handling when resolving the playground investigation ID.

    Covers the two distinct failure modes surfaced by ``resolve_investigation_id``:
    an API-level failure (ApiException) versus a logical failure where the calls
    succeed but no single playground is found (RuntimeError). Each must exit
    non-zero with its own message. Exercised via ``execute command``; the same
    handling is shared by ``execute playbook``.
    """

    def test_api_exception_exits_with_api_message(self, invoke: InvokeHelper, mock_execute_env) -> None:
        from demisto_client.demisto_api.rest import ApiException

        mock_execute_env.resolve_playground_id.side_effect = ApiException(status=500, reason="boom")
        result = invoke(["execute", "command", "MyScript"])
        assert result.exit_code == 1
        assert "failed to query XSOAR for the playground investigation" in result.output
        mock_execute_env.execute_command.assert_not_called()

    def test_runtime_error_exits_with_specific_message(self, invoke: InvokeHelper, mock_execute_env) -> None:
        mock_execute_env.resolve_playground_id.side_effect = RuntimeError("No playground investigation found in the environment")
        result = invoke(["execute", "command", "MyScript"])
        assert result.exit_code == 1
        assert "No playground investigation found" in result.output
        mock_execute_env.execute_command.assert_not_called()

    def test_api_exception_does_not_apply_when_case_id_given(self, invoke: InvokeHelper, mock_execute_env) -> None:
        from demisto_client.demisto_api.rest import ApiException

        # With an explicit case ID the playground is never resolved, so a
        # configured side effect must not be triggered.
        mock_execute_env.resolve_playground_id.side_effect = ApiException(status=500, reason="boom")
        result = invoke(["execute", "command", "MyScript", "--case-id", "12345"])
        assert result.exit_code == 0
        mock_execute_env.resolve_playground_id.assert_not_called()
        mock_execute_env.execute_command.assert_called_once_with("MyScript", {}, "12345")


class TestExecutePlaybook:
    """Tests for ``execute playbook``."""

    def test_success_playground(self, invoke: InvokeHelper, mock_execute_env) -> None:
        result = invoke(["execute", "playbook", "My Playbook"])
        assert result.exit_code == 0
        mock_execute_env.resolve_playground_id.assert_called_once()
        mock_execute_env.execute_playbook.assert_called_once_with("My Playbook", "playground-id")

    def test_success_with_case_id(self, invoke: InvokeHelper, mock_execute_env) -> None:
        result = invoke(["execute", "playbook", "My Playbook", "--case-id", "12345"])
        assert result.exit_code == 0
        mock_execute_env.resolve_playground_id.assert_not_called()
        mock_execute_env.execute_playbook.assert_called_once_with("My Playbook", "12345")

    def test_missing_name_exits_usage_error(self, invoke: InvokeHelper, mock_execute_env) -> None:
        result = invoke(["execute", "playbook"])
        assert result.exit_code == 2
