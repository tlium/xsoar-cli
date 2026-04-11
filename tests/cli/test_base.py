from __future__ import annotations

import click
import pytest

from xsoar_cli.cli import cli


class TestBase:
    @pytest.mark.parametrize(
        ("cli_args", "expected_exit_code"),
        [
            ([], 0),
            (["--version"], 0),
            (["--help"], 0),
        ],
    )
    def test_base_commands(self, invoke, cli_args: list[str], expected_exit_code: int) -> None:
        result = invoke(cli_args)
        assert result.exit_code == expected_exit_code


class TestHelpSections:
    """Verify that --help separates core commands from plugin commands."""

    def test_help_shows_commands_section(self, invoke) -> None:
        result = invoke(["--help"])
        assert "Commands:" in result.output

    def test_help_hides_plugins_section_when_no_plugins(self, invoke) -> None:
        plugin_cmds = {name: cmd for name, cmd in cli.commands.items() if name not in cli.core_commands}
        for name in plugin_cmds:
            cli.commands.pop(name)
        try:
            result = invoke(["--help"])
            assert "Plugins:" not in result.output
        finally:
            cli.commands.update(plugin_cmds)

    def test_help_shows_plugins_section_for_plugin_commands(self, invoke) -> None:
        @click.command()
        def fake_plugin():
            """A fake plugin command."""

        cli.add_command(fake_plugin)
        try:
            result = invoke(["--help"])
            assert "Plugins:" in result.output
            assert "fake-plugin" in result.output
            # Core commands should still be under "Commands:"
            assert "Commands:" in result.output
        finally:
            cli.commands.pop("fake-plugin", None)

    def test_core_commands_not_listed_under_plugins(self, invoke) -> None:
        @click.command()
        def fake_plugin():
            """A fake plugin command."""

        cli.add_command(fake_plugin)
        try:
            result = invoke(["--help"])
            # Split output into sections and verify core commands are not in the Plugins section
            parts = result.output.split("Plugins:")
            assert len(parts) == 2
            plugins_section = parts[1]
            assert "config" not in plugins_section
            assert "pack" not in plugins_section
            assert "fake-plugin" in plugins_section
        finally:
            cli.commands.pop("fake-plugin", None)
