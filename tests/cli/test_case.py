"""CLI integration tests for the ``case`` command group."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from requests.exceptions import HTTPError

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
