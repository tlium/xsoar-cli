"""Fixtures for CLI integration tests (CliRunner-based).

Fixtures defined here build on top of the root conftest fixtures and provide
convenience helpers that reduce boilerplate in CLI test modules.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from xsoar_cli import cli

if TYPE_CHECKING:
    import types
    from collections.abc import Callable, Iterator

    from click.testing import Result


# ---------------------------------------------------------------------------
# CLI invocation helper
# ---------------------------------------------------------------------------


class InvokeHelper:
    """Thin wrapper around ``CliRunner.invoke`` bound to the root CLI group.

    Keeps a reference to the last ``Result`` for convenience, but every call
    also returns it directly.
    """

    def __init__(self) -> None:
        self._runner = CliRunner()
        self.last_result: Result | None = None

    def __call__(self, args: list[str], *, input: str | None = None) -> Result:  # noqa: A002
        self.last_result = self._runner.invoke(cli.cli, args, input=input)
        return self.last_result


@pytest.fixture
def invoke() -> InvokeHelper:
    """Return a callable that invokes the CLI and returns the Click ``Result``.

    Example::

        def test_help(invoke):
            result = invoke(["--help"])
            assert result.exit_code == 0
    """
    return InvokeHelper()


# ---------------------------------------------------------------------------
# Composite mock fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_xsoar_env(mock_config_file) -> Iterator[types.SimpleNamespace]:  # noqa: ANN001
    """Standard mock environment for commands that talk to XSOAR.

    Patches the Client constructor on top of the ``mock_config_file`` fixture
    (which already handles config I/O and ``Path.is_file``).

    Yields a ``SimpleNamespace`` with the following attributes:

    * ``config`` -- the mock for ``get_config_file_contents``
    * ``client_cls`` -- the mock for ``Client`` (the class itself)
    * ``client`` -- shortcut to ``client_cls.return_value`` (the instance)

    Tests can customize the mock client before invoking a command::

        def test_connectivity_failure(invoke, mock_xsoar_env):
            mock_xsoar_env.client.test_connectivity.side_effect = ConnectionError()
            result = invoke(["config", "validate"])
            assert result.exit_code == 1
    """
    import types as _types

    with patch("xsoar_cli.xsoar_client.client.Client") as mock_client_cls:
        ns = _types.SimpleNamespace(
            config=mock_config_file,
            client_cls=mock_client_cls,
            client=mock_client_cls.return_value,
        )
        yield ns


@pytest.fixture
def mock_content_env(mock_config_file) -> Iterator[types.SimpleNamespace]:  # noqa: ANN001
    """Mock environment for ``content download`` commands.

    Patches connectivity, ``Content`` download methods, ``subprocess.run``
    (for demisto-sdk format), and ``Content.attach_item``.

    Yields a ``SimpleNamespace`` with attributes:

    * ``config`` -- the config file mock
    * ``connectivity`` -- the ``Client.test_connectivity`` mock
    * ``subprocess_run`` -- the ``subprocess.run`` mock
    * ``attach`` -- the ``Content.attach_item`` mock
    * ``download_playbook`` -- the ``Content.download_playbook`` mock
    * ``download_layout`` -- the ``Content.download_layout`` mock

    Example::

        def test_download(invoke, mock_content_env, tmp_path, monkeypatch):
            monkeypatch.chdir(tmp_path)
            mock_content_env.download_playbook.return_value = b"id: pb\\n"
            result = invoke(["content", "download", "--type", "playbook", "My PB"])
    """
    import types as _types

    with (
        patch("xsoar_cli.xsoar_client.client.Client.test_connectivity", return_value=True) as mock_conn,
        patch("xsoar_cli.commands.content.commands.subprocess.run") as mock_subproc,
        patch("xsoar_cli.xsoar_client.content.Content.attach_item") as mock_attach,
        patch("xsoar_cli.xsoar_client.content.Content.download_playbook") as mock_dl_pb,
        patch("xsoar_cli.xsoar_client.content.Content.download_layout") as mock_dl_layout,
    ):
        ns = _types.SimpleNamespace(
            config=mock_config_file,
            connectivity=mock_conn,
            subprocess_run=mock_subproc,
            attach=mock_attach,
            download_playbook=mock_dl_pb,
            download_layout=mock_dl_layout,
        )
        yield ns


# ---------------------------------------------------------------------------
# Case-specific mock fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_case_env(mock_config_file, make_case_response, make_case_create_response) -> Iterator[types.SimpleNamespace]:  # noqa: ANN001
    """Mock environment for ``case`` commands.

    Patches ``Cases.get`` and ``Cases.create`` with default success responses.
    The mocks are exposed on the yielded namespace so tests can override
    return values or side effects as needed.
    """
    import types as _types

    with (
        patch("xsoar_cli.xsoar_client.cases.Cases.get") as mock_get,
        patch("xsoar_cli.xsoar_client.cases.Cases.create") as mock_create,
    ):
        mock_get.return_value = make_case_response()
        mock_create.return_value = make_case_create_response()
        ns = _types.SimpleNamespace(
            config=mock_config_file,
            get=mock_get,
            create=mock_create,
        )
        yield ns
