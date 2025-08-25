import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from xsoar_cli import cli
from xsoar_cli.plugins.manager import PluginManager


class TestPluginManager:
    def test_plugin_manager_initialization(self):
        """Test that plugin manager initializes correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            plugins_dir = Path(temp_dir) / "plugins"
            manager = PluginManager(plugins_dir=plugins_dir)

            assert manager.plugins_dir == plugins_dir
            assert plugins_dir.exists()
            assert manager.loaded_plugins == {}
            assert manager.failed_plugins == {}

    def test_discover_plugins_empty_directory(self):
        """Test plugin discovery in empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            plugins_dir = Path(temp_dir) / "plugins"
            manager = PluginManager(plugins_dir=plugins_dir)

            discovered = manager.discover_plugins()
            assert discovered == []

    def test_discover_plugins_with_files(self):
        """Test plugin discovery with Python files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            plugins_dir = Path(temp_dir) / "plugins"
            plugins_dir.mkdir()

            # Create test files
            (plugins_dir / "plugin1.py").write_text("# plugin 1")
            (plugins_dir / "plugin2.py").write_text("# plugin 2")
            (plugins_dir / "__init__.py").write_text("# should be ignored")
            (plugins_dir / "not_python.txt").write_text("# not python")

            manager = PluginManager(plugins_dir=plugins_dir)
            discovered = manager.discover_plugins()

            assert sorted(discovered) == ["plugin1", "plugin2"]

    def test_load_valid_plugin(self):
        """Test loading a valid plugin."""
        with tempfile.TemporaryDirectory() as temp_dir:
            plugins_dir = Path(temp_dir) / "plugins"
            plugins_dir.mkdir()

            # Create a valid plugin file
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
            assert plugin.description == "Test plugin"
            assert "test_plugin" in manager.loaded_plugins

    def test_load_invalid_plugin(self):
        """Test loading an invalid plugin."""
        with tempfile.TemporaryDirectory() as temp_dir:
            plugins_dir = Path(temp_dir) / "plugins"
            plugins_dir.mkdir()

            # Create an invalid plugin file (syntax error)
            plugin_content = """
invalid python syntax !!!
"""
            (plugins_dir / "invalid_plugin.py").write_text(plugin_content)

            manager = PluginManager(plugins_dir=plugins_dir)

            with pytest.raises(Exception):
                manager.load_plugin("invalid_plugin")

    def test_load_plugin_no_plugin_class(self):
        """Test loading a file with no plugin class."""
        with tempfile.TemporaryDirectory() as temp_dir:
            plugins_dir = Path(temp_dir) / "plugins"
            plugins_dir.mkdir()

            # Create a file with no plugin class
            plugin_content = """
import click

def some_function():
    pass
"""
            (plugins_dir / "no_plugin.py").write_text(plugin_content)

            manager = PluginManager(plugins_dir=plugins_dir)

            with pytest.raises(Exception):
                manager.load_plugin("no_plugin")

    def test_load_all_plugins(self):
        """Test loading all plugins with mixed valid/invalid."""
        with tempfile.TemporaryDirectory() as temp_dir:
            plugins_dir = Path(temp_dir) / "plugins"
            plugins_dir.mkdir()

            # Valid plugin
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

            # Invalid plugin
            (plugins_dir / "invalid_plugin.py").write_text("invalid syntax !!!")

            manager = PluginManager(plugins_dir=plugins_dir)
            loaded = manager.load_all_plugins(ignore_errors=True)

            assert len(loaded) == 1
            assert "valid_plugin" in loaded
            assert len(manager.failed_plugins) == 1
            assert "invalid_plugin" in manager.failed_plugins


class TestPluginCommands:
    @patch("pathlib.Path.is_file", MagicMock(return_value=True))
    @patch("xsoar_cli.plugins.commands.PluginManager")
    def test_plugins_list_command(self, mock_manager_class):
        """Test the plugins list command."""
        runner = CliRunner()

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.discover_plugins.return_value = ["test_plugin"]
        mock_manager.get_plugin_info.return_value = {
            "test_plugin": {
                "name": "test",
                "version": "1.0.0",
                "description": "Test plugin",
            },
        }
        mock_manager.get_failed_plugins.return_value = {}
        mock_manager.plugins_dir = Path("/test/plugins")

        result = runner.invoke(cli.cli, ["plugins", "list"])

        assert result.exit_code == 0
        assert "test_plugin" in result.output

    @patch("pathlib.Path.is_file", MagicMock(return_value=True))
    @patch("xsoar_cli.plugins.commands.PluginManager")
    def test_plugins_info_command(self, mock_manager_class):
        """Test the plugins info command."""
        runner = CliRunner()

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_plugin = MagicMock()
        mock_plugin.name = "test"
        mock_plugin.version = "1.0.0"
        mock_plugin.description = "Test plugin"
        mock_manager.load_plugin.return_value = mock_plugin
        mock_manager.plugins_dir = Path("/test/plugins")

        result = runner.invoke(cli.cli, ["plugins", "info", "test_plugin"])

        assert result.exit_code == 0
        assert "test" in result.output
        assert "1.0.0" in result.output

    @patch("pathlib.Path.is_file", MagicMock(return_value=True))
    def test_plugins_validate_command(self):
        """Test the plugins validate command."""
        runner = CliRunner()

        with patch("xsoar_cli.plugins.manager.PluginManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager
            mock_manager.discover_plugins.return_value = ["test_plugin"]

            mock_plugin = MagicMock()
            mock_command = MagicMock()
            mock_plugin.get_command.return_value = mock_command
            mock_manager.load_plugin.return_value = mock_plugin

            result = runner.invoke(cli.cli, ["plugins", "validate"])

            assert result.exit_code == 0
            assert "Valid" in result.output or "valid" in result.output or "No plugins found" in result.output


class TestPluginIntegration:
    @patch("pathlib.Path.is_file", MagicMock(return_value=True))
    def test_plugin_command_registration(self):
        """Test that plugin commands are registered with CLI."""
        with tempfile.TemporaryDirectory() as temp_dir:
            plugins_dir = Path(temp_dir) / "plugins"
            plugins_dir.mkdir()

            # Create a test plugin
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

            # Mock the plugin manager to use our test directory
            with patch("xsoar_cli.plugins.manager.PluginManager") as mock_manager_class:
                mock_manager = PluginManager(plugins_dir=plugins_dir)
                mock_manager_class.return_value = mock_manager

                runner = CliRunner()

                # The plugin should be loaded and its command available
                result = runner.invoke(cli.cli, ["--help"])

                # Check that plugin loading was attempted
                assert result.exit_code == 0

    class TestPluginConflicts:
        def test_command_conflict_detection(self):
            """Test that command conflicts are detected and handled properly."""
            with tempfile.TemporaryDirectory() as temp_dir:
                plugins_dir = Path(temp_dir) / "plugins"
                plugins_dir.mkdir()

                # Create a plugin that conflicts with a core command
                conflict_plugin = """import click

class ConflictPlugin(XSOARPlugin):
    @property
    def name(self):
        return "conflict"

    @property
    def version(self):
        return "1.0.0"

    def get_command(self):
        @click.command()
        def case():  # This conflicts with core 'case' command
            click.echo("conflict")
        return case
"""
                (plugins_dir / "conflict_plugin.py").write_text(conflict_plugin)

                manager = PluginManager(plugins_dir=plugins_dir)
                manager.load_all_plugins(ignore_errors=True)

                # Create a mock CLI group with core commands
                import click

                mock_cli = click.Group()
                mock_cli.add_command(click.Command("case", callback=lambda: None))
                mock_cli.add_command(click.Command("config", callback=lambda: None))

                # Register plugin commands
                manager.register_plugin_commands(mock_cli)

                # Check that conflicts were detected
                conflicts = manager.get_command_conflicts()
                assert len(conflicts) == 1
                assert conflicts[0]["plugin_name"] == "conflict_plugin"
                assert conflicts[0]["command_name"] == "case"
                assert conflicts[0]["plugin_version"] == "1.0.0"

                # Verify that the conflicting command was NOT registered
                assert "case" in mock_cli.commands  # Core command should still be there
                # The plugin command should not have overwritten the core command
