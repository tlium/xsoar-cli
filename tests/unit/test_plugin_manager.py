from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import click
import pytest

from xsoar_cli.plugins.manager import PluginManager


class TestPluginManager:
    def test_plugin_manager_initialization(self, tmp_path: Path):
        """Test that plugin manager initializes correctly."""
        plugins_dir = tmp_path / "plugins"
        manager = PluginManager(plugins_dir=plugins_dir)

        assert manager.plugins_dir == plugins_dir
        assert not plugins_dir.exists()
        assert manager.loaded_plugins == {}
        assert manager.failed_plugins == {}

    def test_plugins_dir_exists_false(self, tmp_path: Path):
        """Test plugins_dir_exists returns False for non-existent directory."""
        plugins_dir = tmp_path / "plugins"
        manager = PluginManager(plugins_dir=plugins_dir)

        assert manager.plugins_dir_exists is False

    def test_plugins_dir_exists_true(self, tmp_path: Path):
        """Test plugins_dir_exists returns True for existing directory."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()
        manager = PluginManager(plugins_dir=plugins_dir)

        assert manager.plugins_dir_exists is True

    def test_discover_plugins_missing_directory(self, tmp_path: Path):
        """Test that discover_plugins returns empty list when directory does not exist."""
        plugins_dir = tmp_path / "plugins"
        manager = PluginManager(plugins_dir=plugins_dir)

        discovered = manager.discover_plugins()
        assert discovered == []

    def test_discover_plugins_empty_directory(self, tmp_path: Path):
        """Test plugin discovery in empty directory."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()
        manager = PluginManager(plugins_dir=plugins_dir)

        discovered = manager.discover_plugins()
        assert discovered == []

    def test_discover_plugins_with_files(self, tmp_path: Path):
        """Test plugin discovery with Python files."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        (plugins_dir / "plugin1.py").write_text("# plugin 1")
        (plugins_dir / "plugin2.py").write_text("# plugin 2")
        (plugins_dir / "__init__.py").write_text("# should be ignored")
        (plugins_dir / "not_python.txt").write_text("# not python")

        manager = PluginManager(plugins_dir=plugins_dir)
        discovered = manager.discover_plugins()

        assert sorted(discovered) == ["plugin1", "plugin2"]

    def test_load_valid_plugin(self, tmp_path: Path):
        """Test loading a valid plugin."""
        plugins_dir = tmp_path / "plugins"
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
        assert plugin.description == "Test plugin"
        assert "test_plugin" in manager.loaded_plugins

    def test_load_invalid_plugin(self, tmp_path: Path):
        """Test loading an invalid plugin."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        plugin_content = """
invalid python syntax !!!
"""
        (plugins_dir / "invalid_plugin.py").write_text(plugin_content)

        manager = PluginManager(plugins_dir=plugins_dir)

        with pytest.raises(Exception):
            manager.load_plugin("invalid_plugin")

    def test_load_plugin_no_plugin_class(self, tmp_path: Path):
        """Test loading a file with no plugin class."""
        plugins_dir = tmp_path / "plugins"
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

    def test_load_all_plugins(self, tmp_path: Path):
        """Test loading all plugins with mixed valid/invalid."""
        plugins_dir = tmp_path / "plugins"
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

    def test_register_continues_past_failure(self, tmp_path: Path):
        """Test that register_plugin_commands continues after one plugin fails."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        plugin_a_content = """
import click
from xsoar_cli.plugins import XSOARPlugin

class PluginA(XSOARPlugin):
    @property
    def name(self):
        return "plugin_a"

    @property
    def version(self):
        return "1.0.0"

    def get_command(self):
        @click.command()
        def cmd_a():
            click.echo("a")
        return cmd_a
"""
        plugin_b_content = """
import click
from xsoar_cli.plugins import XSOARPlugin

class PluginB(XSOARPlugin):
    @property
    def name(self):
        return "plugin_b"

    @property
    def version(self):
        return "1.0.0"

    def get_command(self):
        @click.command()
        def cmd_b():
            click.echo("b")
        return cmd_b
"""
        (plugins_dir / "plugin_a.py").write_text(plugin_a_content)
        (plugins_dir / "plugin_b.py").write_text(plugin_b_content)

        manager = PluginManager(plugins_dir=plugins_dir)
        manager.load_all_plugins(ignore_errors=True)

        assert "plugin_a" in manager.loaded_plugins
        assert "plugin_b" in manager.loaded_plugins

        # Mock get_command on the first plugin to raise an exception.
        plugin_a_instance = manager.loaded_plugins["plugin_a"]
        with patch.object(plugin_a_instance, "get_command", side_effect=RuntimeError("boom")):
            mock_cli = click.Group()
            manager.register_plugin_commands(mock_cli)

        # plugin_b's command should have been registered despite plugin_a's failure.
        # Click converts underscores to hyphens in command names by default.
        assert "cmd-b" in mock_cli.commands
        assert "plugin_a" in manager.failed_plugins

    def test_sys_modules_not_polluted(self, tmp_path: Path):
        """Test that loading a plugin does not leave bare module names in sys.modules."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        plugin_content = """
import click
from xsoar_cli.plugins import XSOARPlugin

class CleanPlugin(XSOARPlugin):
    @property
    def name(self):
        return "clean"

    @property
    def version(self):
        return "1.0.0"

    def get_command(self):
        @click.command()
        def clean_cmd():
            click.echo("clean")
        return clean_cmd
"""
        (plugins_dir / "test_plugin.py").write_text(plugin_content)

        manager = PluginManager(plugins_dir=plugins_dir)
        manager.load_plugin("test_plugin")

        assert "test_plugin" not in sys.modules


class TestPluginConflicts:
    def test_command_conflict_detection(self, tmp_path: Path):
        """Test that command conflicts are detected and handled properly."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        conflict_plugin = """
import click
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

        # Create a mock CLI group with core commands
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

        # Core command should still be there (plugin command should not overwrite it)
        assert "case" in mock_cli.commands
