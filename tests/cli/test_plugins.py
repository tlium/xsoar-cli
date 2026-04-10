"""CLI integration tests for the ``plugins`` command group."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import click

if TYPE_CHECKING:
    from tests.cli.conftest import InvokeHelper


class TestPluginsInit:
    """Tests for the ``plugins init`` subcommand."""

    def test_init_creates_directory_and_example(self, invoke: InvokeHelper, mock_config_file, tmp_path: Path) -> None:
        plugins_dir = tmp_path / "plugins"
        with patch("xsoar_cli.plugins.manager.PluginManager.DEFAULT_PLUGINS_DIR", plugins_dir):
            result = invoke(["plugins", "init"])

        assert result.exit_code == 0
        assert plugins_dir.exists()
        example_file = plugins_dir / "hello.py"
        assert example_file.exists()
        content = example_file.read_text()
        assert "from xsoar_cli.plugins import XSOARPlugin" in content
        assert "class HelloPlugin" in content
        assert "Created plugins directory" in result.output
        assert "Wrote example plugin" in result.output

    def test_init_existing_directory_no_example(self, invoke: InvokeHelper, mock_config_file, tmp_path: Path) -> None:
        """When the directory exists but the example file does not, write without prompting."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()
        with patch("xsoar_cli.plugins.manager.PluginManager.DEFAULT_PLUGINS_DIR", plugins_dir):
            result = invoke(["plugins", "init"])

        assert result.exit_code == 0
        assert (plugins_dir / "hello.py").exists()
        # Should NOT say "Created plugins directory" since it already existed.
        assert "Created plugins directory" not in result.output

    def test_init_overwrite_prompt_confirmed(self, invoke: InvokeHelper, mock_config_file, tmp_path: Path) -> None:
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()
        example_file = plugins_dir / "hello.py"
        example_file.write_text("# old content")

        with patch("xsoar_cli.plugins.manager.PluginManager.DEFAULT_PLUGINS_DIR", plugins_dir):
            result = invoke(["plugins", "init"], input="y\n")

        assert result.exit_code == 0
        assert "class HelloPlugin" in example_file.read_text()

    def test_init_overwrite_prompt_aborted(self, invoke: InvokeHelper, mock_config_file, tmp_path: Path) -> None:
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()
        example_file = plugins_dir / "hello.py"
        example_file.write_text("# old content")

        with patch("xsoar_cli.plugins.manager.PluginManager.DEFAULT_PLUGINS_DIR", plugins_dir):
            result = invoke(["plugins", "init"], input="n\n")

        assert result.exit_code == 1
        assert example_file.read_text() == "# old content"


class TestPluginsList:
    """Tests for the ``plugins list`` subcommand."""

    def test_list_not_initialized(self, invoke: InvokeHelper, mock_plugin_env) -> None:
        mock_plugin_env.manager.plugins_dir_exists = False

        result = invoke(["plugins", "list"])

        assert result.exit_code == 1
        assert "not initialized" in result.output.lower() or "not initialized" in (result.output + getattr(result, "stderr", "")).lower()

    def test_list_empty_directory(self, invoke: InvokeHelper, mock_plugin_env) -> None:
        result = invoke(["plugins", "list"])

        assert result.exit_code == 0
        assert "No plugins found" in result.output

    def test_list_with_loaded_plugins(self, invoke: InvokeHelper, mock_plugin_env) -> None:
        mock_plugin_env.manager.get_plugin_info.return_value = {
            "test_plugin": {
                "name": "test",
                "version": "1.0.0",
                "description": "Test plugin",
            },
        }

        result = invoke(["plugins", "list"])

        assert result.exit_code == 0
        assert "test_plugin" in result.output
        assert "1.0.0" in result.output

    def test_list_verbose(self, invoke: InvokeHelper, mock_plugin_env) -> None:
        mock_plugin_env.manager.get_plugin_info.return_value = {
            "test_plugin": {
                "name": "test",
                "version": "1.0.0",
                "description": "Test plugin",
            },
        }

        result = invoke(["plugins", "list", "--verbose"])

        assert result.exit_code == 0
        assert "Name: test" in result.output
        assert "Version: 1.0.0" in result.output
        assert "Description: Test plugin" in result.output

    def test_list_with_failed_plugins(self, invoke: InvokeHelper, mock_plugin_env) -> None:
        mock_plugin_env.manager.get_failed_plugins.return_value = {
            "broken_plugin": "SyntaxError: invalid syntax",
        }

        result = invoke(["plugins", "list"])

        assert result.exit_code == 0
        assert "broken_plugin" in result.output

    def test_list_with_conflicts(self, invoke: InvokeHelper, mock_plugin_env) -> None:
        mock_plugin_env.manager.get_plugin_info.return_value = {
            "my_plugin": {"name": "my", "version": "1.0.0", "description": "My plugin"},
        }
        mock_plugin_env.manager.get_command_conflicts.return_value = [
            {"plugin_name": "my_plugin", "command_name": "case", "plugin_version": "1.0.0"},
        ]

        result = invoke(["plugins", "list"])

        assert result.exit_code == 0
        assert "Command Conflicts" in result.output
        assert "case" in result.output


class TestPluginsInfo:
    """Tests for the ``plugins info`` subcommand."""

    def test_info_not_initialized(self, invoke: InvokeHelper, mock_plugin_env) -> None:
        mock_plugin_env.manager.plugins_dir_exists = False

        result = invoke(["plugins", "info", "test_plugin"])

        assert result.exit_code == 1

    def test_info_plugin_not_found(self, invoke: InvokeHelper, mock_plugin_env) -> None:
        mock_plugin_env.manager.get_failed_plugins.return_value = {}

        result = invoke(["plugins", "info", "nonexistent"])

        assert result.exit_code == 1
        assert "Plugin not found" in result.output

    def test_info_plugin_failed(self, invoke: InvokeHelper, mock_plugin_env) -> None:
        mock_plugin_env.manager.get_failed_plugins.return_value = {
            "broken": "SyntaxError: invalid syntax",
        }

        result = invoke(["plugins", "info", "broken"])

        assert result.exit_code == 1
        assert "failed to load" in result.output

    def test_info_loaded_plugin(self, invoke: InvokeHelper, mock_plugin_env) -> None:
        mock_plugin = MagicMock()
        mock_plugin.name = "test"
        mock_plugin.version = "1.0.0"
        mock_plugin.description = "Test plugin"
        mock_command = click.Command("test", callback=lambda: None)
        mock_plugin.get_command.return_value = mock_command

        mock_plugin_env.manager.loaded_plugins["test_plugin"] = mock_plugin
        mock_plugin_env.manager.plugins_dir = Path("/test/plugins")

        result = invoke(["plugins", "info", "test_plugin"])

        assert result.exit_code == 0
        assert "Name: test" in result.output
        assert "Version: 1.0.0" in result.output
        assert "Description: Test plugin" in result.output
        assert "File:" in result.output
        assert "test_plugin.py" in result.output


class TestPluginsValidate:
    """Tests for the ``plugins validate`` subcommand."""

    def test_validate_not_initialized(self, invoke: InvokeHelper, mock_plugin_env) -> None:
        mock_plugin_env.manager.plugins_dir_exists = False

        result = invoke(["plugins", "validate"])

        assert result.exit_code == 1

    def test_validate_no_plugins(self, invoke: InvokeHelper, mock_plugin_env) -> None:
        result = invoke(["plugins", "validate"])

        assert result.exit_code == 0
        assert "No plugins found" in result.output

    def test_validate_all_valid(self, invoke: InvokeHelper, mock_plugin_env) -> None:
        mock_plugin = MagicMock()
        mock_command = click.Command("test", callback=lambda: None)
        mock_plugin.get_command.return_value = mock_command

        mock_plugin_env.manager.loaded_plugins["test_plugin"] = mock_plugin

        result = invoke(["plugins", "validate"])

        assert result.exit_code == 0
        assert "test_plugin: Valid" in result.output
        assert "All plugins are valid!" in result.output

    def test_validate_with_failed_plugins(self, invoke: InvokeHelper, mock_plugin_env) -> None:
        mock_plugin_env.manager.get_failed_plugins.return_value = {
            "broken": "SyntaxError: invalid syntax",
        }

        result = invoke(["plugins", "validate"])

        assert result.exit_code == 0
        assert "broken: SyntaxError" in result.output
        assert "Some plugins have validation errors." in result.output

    def test_validate_with_conflicts(self, invoke: InvokeHelper, mock_plugin_env) -> None:
        mock_plugin = MagicMock()
        mock_plugin.get_command.return_value = click.Command("test", callback=lambda: None)
        mock_plugin_env.manager.loaded_plugins["test_plugin"] = mock_plugin
        mock_plugin_env.manager.get_command_conflicts.return_value = [
            {"plugin_name": "test_plugin", "command_name": "case", "plugin_version": "1.0.0"},
        ]

        result = invoke(["plugins", "validate"])

        assert result.exit_code == 0
        assert "Command Conflicts Detected" in result.output
        assert "Some plugins have validation errors." in result.output
