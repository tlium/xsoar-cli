import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from xsoar_cli import cli
from xsoar_cli.plugins.manager import PluginManager


class TestPluginManager:
    @pytest.mark.parametrize(
        ("test_scenario", "expected_behavior"),
        [
            ("initialization", "creates_plugins_dir"),
            ("empty_directory", "no_plugins_found"),
            ("with_python_files", "discovers_plugins"),
            ("valid_plugin", "loads_successfully"),
            ("invalid_syntax", "raises_exception"),
            ("no_plugin_class", "raises_exception"),
            ("mixed_plugins", "loads_valid_ignores_invalid"),
            ("create_example", "creates_example_plugin"),
        ],
    )
    def test_plugin_manager(self, test_scenario: str, expected_behavior: str) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            plugins_dir = Path(temp_dir) / "plugins"

            if test_scenario == "initialization":
                manager = PluginManager(plugins_dir=plugins_dir)
                assert manager.plugins_dir == plugins_dir
                assert plugins_dir.exists()
                assert manager.loaded_plugins == {}
                assert manager.failed_plugins == {}

            elif test_scenario == "empty_directory":
                manager = PluginManager(plugins_dir=plugins_dir)
                discovered = manager.discover_plugins()
                assert discovered == []

            elif test_scenario == "with_python_files":
                plugins_dir.mkdir()
                (plugins_dir / "plugin1.py").write_text("# plugin 1")
                (plugins_dir / "plugin2.py").write_text("# plugin 2")
                (plugins_dir / "__init__.py").write_text("# should be ignored")
                (plugins_dir / "not_python.txt").write_text("# not python")
                manager = PluginManager(plugins_dir=plugins_dir)
                discovered = manager.discover_plugins()
                assert sorted(discovered) == ["plugin1", "plugin2"]

            elif test_scenario == "valid_plugin":
                plugins_dir.mkdir()
                plugin_content = """
import click
from xsoar_cli.plugins import XSOARPlugin

class TestPlugin(XSOARPlugin):
    @property
    def name(self):
        return "test"

    @property
    def version(self):
        return "1.0.0"

    @property
    def description(self):
        return "Test plugin"

    def get_command(self):
        @click.command()
        def test_cmd():
            click.echo("test")
        return test_cmd
"""
                (plugins_dir / "test_plugin.py").write_text(plugin_content)
                manager = PluginManager(plugins_dir=plugins_dir)
                plugin = manager.load_plugin("test_plugin")
                assert plugin is not None
                assert plugin.name == "test"
                assert plugin.version == "1.0.0"
                assert "test_plugin" in manager.loaded_plugins

            elif test_scenario == "invalid_syntax":
                plugins_dir.mkdir()
                (plugins_dir / "invalid_plugin.py").write_text("invalid python syntax !!!")
                manager = PluginManager(plugins_dir=plugins_dir)
                with pytest.raises(Exception):
                    manager.load_plugin("invalid_plugin")

            elif test_scenario == "no_plugin_class":
                plugins_dir.mkdir()
                plugin_content = """
import click

def some_function():
    pass
"""
                (plugins_dir / "no_plugin.py").write_text(plugin_content)
                manager = PluginManager(plugins_dir=plugins_dir)
                with pytest.raises(Exception):
                    manager.load_plugin("no_plugin")

            elif test_scenario == "mixed_plugins":
                plugins_dir.mkdir()
                valid_plugin = """
import click
from xsoar_cli.plugins import XSOARPlugin

class ValidPlugin(XSOARPlugin):
    @property
    def name(self):
        return "valid"

    @property
    def version(self):
        return "1.0.0"

    def get_command(self):
        @click.command()
        def valid_cmd():
            pass
        return valid_cmd
"""
                (plugins_dir / "valid_plugin.py").write_text(valid_plugin)
                (plugins_dir / "invalid_plugin.py").write_text("invalid syntax !!!")
                manager = PluginManager(plugins_dir=plugins_dir)
                loaded = manager.load_all_plugins(ignore_errors=True)
                assert len(loaded) == 1
                assert "valid_plugin" in loaded
                assert len(manager.failed_plugins) == 1
                assert "invalid_plugin" in manager.failed_plugins

            elif test_scenario == "create_example":
                manager = PluginManager(plugins_dir=plugins_dir)
                manager.create_example_plugin()
                example_file = plugins_dir / "example_plugin.py"
                assert example_file.exists()
                plugin = manager.load_plugin("example_plugin")
                assert plugin is not None
                assert plugin.name == "example"


class TestPluginCommands:
    @patch("pathlib.Path.is_file", MagicMock(return_value=True))
    @pytest.mark.parametrize(
        ("cli_args", "mock_setup", "expected_in_output"),
        [
            (["plugins", "list"], "list_plugins", "test_plugin"),
            (["plugins", "create-example"], "create_example", None),
            (["plugins", "info", "test_plugin"], "plugin_info", "1.0.0"),
            (["plugins", "validate"], "validate_plugins", "test_plugin"),
        ],
    )
    def test_plugin_commands(self, cli_args: list[str], mock_setup: str, expected_in_output: str | None) -> None:
        runner = CliRunner()

        with patch("xsoar_cli.plugins.commands.PluginManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager
            mock_manager.plugins_dir = Path("/test/plugins")

            if mock_setup == "list_plugins":
                mock_manager.discover_plugins.return_value = ["test_plugin"]
                mock_manager.get_plugin_info.return_value = {
                    "test_plugin": {
                        "name": "test",
                        "version": "1.0.0",
                        "description": "Test plugin",
                    },
                }
                mock_manager.get_failed_plugins.return_value = {}

            elif mock_setup == "create_example":
                pass  # Just need mock manager

            elif mock_setup == "plugin_info":
                mock_plugin = MagicMock()
                mock_plugin.name = "test"
                mock_plugin.version = "1.0.0"
                mock_plugin.description = "Test plugin"
                mock_manager.load_plugin.return_value = mock_plugin

            elif mock_setup == "validate_plugins":
                mock_manager.discover_plugins.return_value = ["test_plugin"]
                mock_plugin = MagicMock()
                mock_command = MagicMock()
                mock_plugin.get_command.return_value = mock_command
                mock_manager.load_plugin.return_value = mock_plugin

            result = runner.invoke(cli.cli, cli_args)

            assert result.exit_code == 0
            if expected_in_output:
                assert expected_in_output in result.output

            if mock_setup == "create_example":
                mock_manager.create_example_plugin.assert_called_once()


class TestPluginIntegration:
    @patch("pathlib.Path.is_file", MagicMock(return_value=True))
    @pytest.mark.parametrize(
        ("test_scenario", "expected_result"),
        [
            ("command_registration", "plugin_loaded"),
            ("command_conflict", "conflict_detected"),
        ],
    )
    def test_plugin_integration(self, test_scenario: str, expected_result: str) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            plugins_dir = Path(temp_dir) / "plugins"
            plugins_dir.mkdir()

            if test_scenario == "command_registration":
                plugin_content = """
import click
from xsoar_cli.plugins import XSOARPlugin

class TestPlugin(XSOARPlugin):
    @property
    def name(self):
        return "test"

    @property
    def version(self):
        return "1.0.0"

    def get_command(self):
        @click.command(help="Test command")
        def testcmd():
            click.echo("Hello from test plugin!")
        return testcmd
"""
                (plugins_dir / "test_plugin.py").write_text(plugin_content)

                with patch("xsoar_cli.plugins.manager.PluginManager") as mock_manager_class:
                    mock_manager = PluginManager(plugins_dir=plugins_dir)
                    mock_manager_class.return_value = mock_manager
                    runner = CliRunner()
                    result = runner.invoke(cli.cli, ["--help"])
                    assert result.exit_code == 0

            elif test_scenario == "command_conflict":
                conflict_plugin = """import click
from xsoar_cli.plugins import XSOARPlugin

class ConflictPlugin(XSOARPlugin):
    @property
    def name(self):
        return "conflict"

    @property
    def version(self):
        return "1.0.0"

    def get_command(self):
        @click.command()
        def case():
            click.echo("conflict")
        return case
"""
                (plugins_dir / "conflict_plugin.py").write_text(conflict_plugin)
                manager = PluginManager(plugins_dir=plugins_dir)
                manager.load_all_plugins(ignore_errors=True)

                import click

                mock_cli = click.Group()
                mock_cli.add_command(click.Command("case", callback=lambda: None))
                mock_cli.add_command(click.Command("config", callback=lambda: None))

                manager.register_plugin_commands(mock_cli)
                conflicts = manager.get_command_conflicts()
                assert len(conflicts) == 1
                assert conflicts[0]["plugin_name"] == "conflict_plugin"
                assert conflicts[0]["command_name"] == "case"
                assert conflicts[0]["plugin_version"] == "1.0.0"
                assert "case" in mock_cli.commands
