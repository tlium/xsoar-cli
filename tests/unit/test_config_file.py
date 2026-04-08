"""Unit tests for config file utilities (``xsoar_cli.utilities.config_file``).

Tests mock Click context and filesystem I/O to verify that ``load_config``,
``read_config_file``, and ``get_config_file_path`` behave correctly without
touching the real config file.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import click
from click.testing import CliRunner

from xsoar_cli.configuration import XSOARConfig
from xsoar_cli.utilities.config_file import get_config_file_path, load_config, read_config_file

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_CONFIG = {
    "default_environment": "dev",
    "custom_pack_authors": ["MyOrg"],
    "default_new_case_type": "Unclassified",
    "server_config": {
        "dev": {
            "base_url": "https://xsoar-dev.example.com",
            "api_token": "dev-token",
            "server_version": 6,
        },
        "prod": {
            "base_url": "https://xsoar.example.com",
            "api_token": "prod-token",
            "server_version": 8,
        },
    },
}


# ===========================================================================
# get_config_file_path
# ===========================================================================


class TestGetConfigFilePath:
    def test_returns_path_under_home(self) -> None:
        result = get_config_file_path()
        assert isinstance(result, Path)
        assert result.name == "config.json"
        assert ".config/xsoar-cli" in str(result)

    def test_path_is_absolute(self) -> None:
        result = get_config_file_path()
        assert result.is_absolute()


# ===========================================================================
# read_config_file
# ===========================================================================


class TestReadConfigFile:
    def test_returns_none_when_file_missing(self) -> None:
        with (
            patch("xsoar_cli.utilities.config_file.get_config_file_path") as mock_path,
            patch("pathlib.Path.is_file", return_value=False),
        ):
            mock_path.return_value = Path("/nonexistent/config.json")
            result = read_config_file()

        assert result is None

    def test_returns_parsed_json_when_file_exists(self) -> None:
        import json

        with (
            patch("xsoar_cli.utilities.config_file.get_config_file_path") as mock_path,
            patch("pathlib.Path.is_file", return_value=True),
            patch("xsoar_cli.utilities.config_file.get_config_file_contents") as mock_get,
        ):
            mock_path.return_value = Path("/fake/config.json")
            mock_get.return_value = _VALID_CONFIG
            result = read_config_file()

        assert result == _VALID_CONFIG


# ===========================================================================
# load_config decorator
# ===========================================================================


class TestLoadConfig:
    def test_prompts_when_config_missing(self) -> None:
        @click.command()
        @load_config
        @click.pass_context
        def dummy(ctx: click.Context) -> None:
            click.echo("should not run")

        runner = CliRunner()
        with patch("xsoar_cli.utilities.config_file.read_config_file", return_value=None):
            result = runner.invoke(dummy, [])

        assert result.exit_code != 0
        assert "Config file not found" in result.output
        assert "xsoar-cli config create" in result.output

    def test_loads_config_from_file(self) -> None:
        @click.command()
        @load_config
        @click.pass_context
        def dummy(ctx: click.Context) -> None:
            assert isinstance(ctx.obj, XSOARConfig)
            click.echo("executed")

        runner = CliRunner()
        with patch("xsoar_cli.utilities.config_file.read_config_file", return_value=_VALID_CONFIG):
            result = runner.invoke(dummy, [])

        assert result.exit_code == 0
        assert "executed" in result.output

    def test_reuses_existing_xsoar_config(self) -> None:
        existing_config = XSOARConfig(_VALID_CONFIG)

        @click.command()
        @load_config
        @click.pass_context
        def dummy(ctx: click.Context) -> None:
            assert ctx.obj is existing_config
            click.echo("reused")

        runner = CliRunner()
        result = runner.invoke(dummy, [], obj=existing_config)

        assert result.exit_code == 0
        assert "reused" in result.output

    def test_reuses_dict_from_context(self) -> None:
        @click.command()
        @load_config
        @click.pass_context
        def dummy(ctx: click.Context) -> None:
            assert isinstance(ctx.obj, XSOARConfig)
            click.echo("from-dict")

        runner = CliRunner()
        # Passing a raw dict as obj simulates main() storing config_dict on ctx.obj
        with patch("xsoar_cli.utilities.config_file.read_config_file") as mock_read:
            result = runner.invoke(dummy, [], obj=_VALID_CONFIG)

        # read_config_file should not be called when ctx.obj is already a dict
        mock_read.assert_not_called()
        assert result.exit_code == 0
        assert "from-dict" in result.output

    def test_invalid_environment_exits(self) -> None:
        @click.command()
        @click.option("--environment", default=None)
        @load_config
        @click.pass_context
        def dummy(ctx: click.Context, environment: str | None) -> None:
            click.echo("should not run")

        runner = CliRunner()
        with patch("xsoar_cli.utilities.config_file.read_config_file", return_value=_VALID_CONFIG):
            result = runner.invoke(dummy, ["--environment", "nonexistent"])

        assert result.exit_code != 0
        assert "Invalid environment" in result.output
        assert "nonexistent" in result.output
        assert "should not run" not in result.output

    def test_valid_environment_passes(self) -> None:
        @click.command()
        @click.option("--environment", default=None)
        @load_config
        @click.pass_context
        def dummy(ctx: click.Context, environment: str | None) -> None:
            click.echo("executed")

        runner = CliRunner()
        with patch("xsoar_cli.utilities.config_file.read_config_file", return_value=_VALID_CONFIG):
            result = runner.invoke(dummy, ["--environment", "prod"])

        assert result.exit_code == 0
        assert "executed" in result.output

    def test_none_environment_skips_validation(self) -> None:
        @click.command()
        @click.option("--environment", default=None)
        @load_config
        @click.pass_context
        def dummy(ctx: click.Context, environment: str | None) -> None:
            click.echo("executed")

        runner = CliRunner()
        with patch("xsoar_cli.utilities.config_file.read_config_file", return_value=_VALID_CONFIG):
            result = runner.invoke(dummy, [])

        assert result.exit_code == 0
        assert "executed" in result.output

    def test_shows_available_environments_on_invalid(self) -> None:
        @click.command()
        @click.option("--environment", default=None)
        @load_config
        @click.pass_context
        def dummy(ctx: click.Context, environment: str | None) -> None:
            click.echo("should not run")

        runner = CliRunner()
        with patch("xsoar_cli.utilities.config_file.read_config_file", return_value=_VALID_CONFIG):
            result = runner.invoke(dummy, ["--environment", "bad"])

        assert "Available environments" in result.output
