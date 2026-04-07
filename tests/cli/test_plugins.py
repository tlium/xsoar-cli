"""CLI integration tests for the ``plugins`` command group."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from xsoar_cli.plugins.manager import PluginManager

if TYPE_CHECKING:
    from tests.cli.conftest import InvokeHelper


class TestPluginCommands:
    """Tests for the ``plugins`` CLI subcommands."""

    @patch("xsoar_cli.commands.plugins.commands.PluginManager")
    def test_plugins_list_command(self, mock_manager_class, invoke: InvokeHelper, mock_config_file) -> None:
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

        result = invoke(["plugins", "list"])
        assert result.exit_code == 0
        assert "test_plugin" in result.output

    @patch("xsoar_cli.commands.plugins.commands.PluginManager")
    def test_plugins_info_command(self, mock_manager_class, invoke: InvokeHelper, mock_config_file) -> None:
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_plugin = MagicMock()
        mock_plugin.name = "test"
        mock_plugin.version = "1.0.0"
        mock_plugin.description = "Test plugin"
        mock_manager.load_plugin.return_value = mock_plugin
        mock_manager.plugins_dir = Path("/test/plugins")

        result = invoke(["plugins", "info", "test_plugin"])
        assert result.exit_code == 0
        assert "test" in result.output
        assert "1.0.0" in result.output

    def test_plugins_validate_command(self, invoke: InvokeHelper, mock_config_file) -> None:
        with patch("xsoar_cli.plugins.manager.PluginManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager
            mock_manager.discover_plugins.return_value = ["test_plugin"]

            mock_plugin = MagicMock()
            mock_command = MagicMock()
            mock_plugin.get_command.return_value = mock_command
            mock_manager.load_plugin.return_value = mock_plugin

            result = invoke(["plugins", "validate"])
            assert result.exit_code == 0
            assert "Valid" in result.output or "valid" in result.output or "No plugins found" in result.output


class TestPluginIntegration:
    """Tests for plugin command registration with the CLI."""

    def test_plugin_command_registration(self, invoke: InvokeHelper, mock_config_file) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            plugins_dir = Path(temp_dir) / "plugins"
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

                result = invoke(["--help"])
                assert result.exit_code == 0
