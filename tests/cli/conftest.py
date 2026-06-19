"""Fixtures for CLI integration tests (CliRunner-based).

Fixtures defined here build on top of the root conftest fixtures and provide
convenience helpers that reduce boilerplate in CLI test modules.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from xsoar_cli import cli

if TYPE_CHECKING:
    import types
    from collections.abc import Iterator

    from click.testing import Result


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
    (for demisto-sdk format), ``Content.attach_item``, and
    ``Content.get_detached``.

    Yields a ``SimpleNamespace`` with attributes:

    * ``config`` -- the config file mock
    * ``connectivity`` -- the ``Client.test_connectivity`` mock
    * ``subprocess_run`` -- the ``subprocess.run`` mock
    * ``attach`` -- the ``Content.attach_item`` mock
    * ``download_playbook`` -- the ``Content.download_playbook`` mock
    * ``download_layout`` -- the ``Content.download_layout`` mock
    * ``get_detached`` -- the ``Content.get_detached`` mock

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
        patch("xsoar_cli.xsoar_client.content.Content.get_detached") as mock_get_detached,
    ):
        ns = _types.SimpleNamespace(
            config=mock_config_file,
            connectivity=mock_conn,
            subprocess_run=mock_subproc,
            attach=mock_attach,
            download_playbook=mock_dl_pb,
            download_layout=mock_dl_layout,
            get_detached=mock_get_detached,
        )
        yield ns


@pytest.fixture
def mock_content_list_env(mock_config_file) -> Iterator[types.SimpleNamespace]:  # noqa: ANN001
    """Mock environment for the ``content list`` command.

    Patches connectivity and ``Content.list``. The ``list`` mock is exposed
    on the yielded namespace so tests can set its return value to the raw
    API shape for the requested content type.

    Yields a ``SimpleNamespace`` with attributes:

    * ``config`` -- the config file mock
    * ``connectivity`` -- the ``Client.test_connectivity`` mock
    * ``list`` -- the ``Content.list`` mock
    """
    import types as _types

    with (
        patch("xsoar_cli.xsoar_client.client.Client.test_connectivity", return_value=True) as mock_conn,
        patch("xsoar_cli.xsoar_client.content.Content.list") as mock_list,
    ):
        ns = _types.SimpleNamespace(
            config=mock_config_file,
            connectivity=mock_conn,
            list=mock_list,
        )
        yield ns


@pytest.fixture
def mock_content_describe_env(mock_config_file) -> Iterator[types.SimpleNamespace]:  # noqa: ANN001
    """Mock environment for the ``content describe`` command.

    Patches connectivity and ``Content.describe``. The ``describe`` mock is
    exposed on the yielded namespace so tests can set its return value to the
    raw record shape (or None for the not-found case).

    Yields a ``SimpleNamespace`` with attributes:

    * ``config`` -- the config file mock
    * ``connectivity`` -- the ``Client.test_connectivity`` mock
    * ``describe`` -- the ``Content.describe`` mock
    """
    import types as _types

    with (
        patch("xsoar_cli.xsoar_client.client.Client.test_connectivity", return_value=True) as mock_conn,
        patch("xsoar_cli.xsoar_client.content.Content.describe") as mock_describe,
    ):
        ns = _types.SimpleNamespace(
            config=mock_config_file,
            connectivity=mock_conn,
            describe=mock_describe,
        )
        yield ns


@pytest.fixture
def mock_plugin_env(mock_config_file) -> Iterator[types.SimpleNamespace]:  # noqa: ANN001
    """Mock environment for ``plugins`` CLI subcommands.

    Patches the module-level ``plugin_manager`` in ``cli.py`` so that plugin
    commands (which obtain the manager via ``_get_plugin_manager()``) see a
    controllable mock instead of the real instance.

    Yields a ``SimpleNamespace`` with attributes:

    * ``config`` -- the config file mock (from ``mock_config_file``)
    * ``manager`` -- the ``MagicMock`` standing in for ``PluginManager``
    * ``loaded_plugins`` -- shortcut dict for ``manager.loaded_plugins``
    * ``failed_plugins`` -- shortcut dict for ``manager.failed_plugins``
    * ``command_conflicts`` -- shortcut list for ``manager.command_conflicts``

    Example::

        def test_list_empty(invoke, mock_plugin_env):
            mock_plugin_env.manager.plugins_dir_exists = True
            result = invoke(["plugins", "list"])
            assert "No plugins found" in result.output
    """
    import types as _types

    mock_manager = MagicMock()
    mock_manager.plugins_dir = Path("/test/plugins")
    mock_manager.plugins_dir_exists = True
    mock_manager.loaded_plugins = {}
    mock_manager.failed_plugins = {}
    mock_manager.command_conflicts = []
    mock_manager.get_plugin_info.return_value = {}
    mock_manager.get_failed_plugins.return_value = {}
    mock_manager.get_command_conflicts.return_value = []

    with patch.object(cli, "plugin_manager", mock_manager):
        ns = _types.SimpleNamespace(
            config=mock_config_file,
            manager=mock_manager,
            loaded_plugins=mock_manager.loaded_plugins,
            failed_plugins=mock_manager.failed_plugins,
            command_conflicts=mock_manager.command_conflicts,
        )
        yield ns


@pytest.fixture
def mock_execute_env(mock_config_file) -> Iterator[types.SimpleNamespace]:  # noqa: ANN001
    """Mock environment for ``execute`` commands.

    Patches connectivity and the ``Execution`` domain methods with default
    success behaviour. The mocks are exposed on the yielded namespace so tests
    can override return values or side effects as needed.

    Yields a ``SimpleNamespace`` with attributes:

    * ``config`` -- the config file mock
    * ``connectivity`` -- the ``Client.test_connectivity`` mock
    * ``resolve_playground_id`` -- the ``Execution.resolve_playground_id`` mock
    * ``execute_command`` -- the ``Execution.execute_command`` mock
    * ``execute_playbook`` -- the ``Execution.execute_playbook`` mock
    """
    import types as _types

    with (
        patch("xsoar_cli.xsoar_client.client.Client.test_connectivity", return_value=True) as mock_conn,
        patch("xsoar_cli.xsoar_client.execution.Execution.resolve_playground_id") as mock_playground,
        patch("xsoar_cli.xsoar_client.execution.Execution.execute_command") as mock_cmd,
        patch("xsoar_cli.xsoar_client.execution.Execution.execute_playbook") as mock_pb,
    ):
        mock_playground.return_value = "playground-id"
        mock_cmd.return_value = {"entries": [{"id": "1@x", "contents": "command output"}]}
        mock_pb.return_value = {"result": "ok"}
        ns = _types.SimpleNamespace(
            config=mock_config_file,
            connectivity=mock_conn,
            resolve_playground_id=mock_playground,
            execute_command=mock_cmd,
            execute_playbook=mock_pb,
        )
        yield ns


@pytest.fixture
def mock_case_env(mock_config_file, make_case_response, make_case_create_response) -> Iterator[types.SimpleNamespace]:  # noqa: ANN001
    """Mock environment for ``case`` commands.

    Patches ``Cases.get``, ``Cases.create``, ``Cases.get_context``,
    ``Cases.get_entry``, and ``Cases.get_entries`` with default success
    responses. The mocks are exposed on the yielded namespace so tests can
    override return values or side effects as needed.
    """
    import types as _types

    with (
        patch("xsoar_cli.xsoar_client.client.Client.test_connectivity", return_value=True) as mock_conn,
        patch("xsoar_cli.xsoar_client.cases.Cases.get") as mock_get,
        patch("xsoar_cli.xsoar_client.cases.Cases.create") as mock_create,
        patch("xsoar_cli.xsoar_client.cases.Cases.get_context") as mock_get_context,
        patch("xsoar_cli.xsoar_client.cases.Cases.get_entry") as mock_get_entry,
        patch("xsoar_cli.xsoar_client.cases.Cases.get_entries") as mock_get_entries,
    ):
        mock_get.return_value = make_case_response()
        mock_create.return_value = make_case_create_response()
        mock_get_context.return_value = {"playbook_name": "My Playbook", "File": []}
        mock_get_entry.return_value = {"id": "112@153483", "contents": "entry data"}
        mock_get_entries.return_value = [{"id": "112@153483", "contents": "entry data"}]
        ns = _types.SimpleNamespace(
            config=mock_config_file,
            connectivity=mock_conn,
            get=mock_get,
            create=mock_create,
            get_context=mock_get_context,
            get_entry=mock_get_entry,
            get_entries=mock_get_entries,
        )
        yield ns
