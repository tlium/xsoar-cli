"""CLI integration tests for the ``case`` command group."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tests.cli.conftest import InvokeHelper


class TestCaseGroup:
    """The bare ``case`` command and its help output."""

    def test_shows_help(self, invoke: InvokeHelper) -> None:
        result = invoke(["case"])
        assert result.exit_code == 0

    def test_help_flag(self, invoke: InvokeHelper) -> None:
        result = invoke(["case", "--help"])
        assert result.exit_code == 0


class TestCaseGet:
    """Tests for ``case get``."""

    def test_get_case_success(self, invoke: InvokeHelper, mock_case_env) -> None:
        result = invoke(["case", "get", "152230"])
        assert result.exit_code == 0

    def test_get_case_http_error(self, invoke: InvokeHelper, mock_case_env, make_http_error) -> None:
        mock_case_env.get.side_effect = make_http_error(400, text="Bad Request")
        result = invoke(["case", "get", "152230"])
        assert result.exit_code == 1


class TestCaseCreate:
    """Tests for ``case create``."""

    def test_create_case_success(self, invoke: InvokeHelper, mock_case_env) -> None:
        result = invoke(["case", "create"])
        assert result.exit_code == 0


class TestCaseClone:
    """Tests for ``case clone``."""

    def test_clone_missing_options(self, invoke: InvokeHelper, mock_case_env) -> None:
        result = invoke(["case", "clone", "152230"])
        assert result.exit_code == 2

    def test_clone_with_bogus_environments(self, invoke: InvokeHelper, mock_case_env) -> None:
        result = invoke(["case", "clone", "--dest", "bogus", "--source", "bogus", "152230"])
        assert result.exit_code == 1


class TestCaseGetContext:
    """Tests for ``case get-context``."""

    def test_get_context_success(self, invoke: InvokeHelper, mock_case_env) -> None:
        result = invoke(["case", "get-context", "153483"])
        assert result.exit_code == 0
        mock_case_env.get_context.assert_called_once_with(153483)

    def test_get_context_http_error(self, invoke: InvokeHelper, mock_case_env, make_http_error) -> None:
        mock_case_env.get_context.side_effect = make_http_error(404, text="Not Found")
        result = invoke(["case", "get-context", "153483"])
        assert result.exit_code == 1


class TestCaseGetEntry:
    """Tests for ``case get-entry``."""

    def test_get_entry_success(self, invoke: InvokeHelper, mock_case_env) -> None:
        result = invoke(["case", "get-entry", "153483", "112@153483"])
        assert result.exit_code == 0
        mock_case_env.get_entry.assert_called_once_with(153483, "112@153483")

    def test_get_entry_not_found(self, invoke: InvokeHelper, mock_case_env) -> None:
        mock_case_env.get_entry.side_effect = ValueError("Entry '999@153483' not found in case 153483")
        result = invoke(["case", "get-entry", "153483", "999@153483"])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_get_entry_http_error(self, invoke: InvokeHelper, mock_case_env, make_http_error) -> None:
        mock_case_env.get_entry.side_effect = make_http_error(400, text="Bad Request")
        result = invoke(["case", "get-entry", "153483", "112@153483"])
        assert result.exit_code == 1

    def test_get_entry_missing_entry_id_argument(self, invoke: InvokeHelper, mock_case_env) -> None:
        result = invoke(["case", "get-entry", "153483"])
        assert result.exit_code == 2
