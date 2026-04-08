"""Unit tests for validator decorators (``xsoar_cli.utilities.validators``).

Tests mock the Click context, ``get_xsoar_config``, and the XSOAR client to
verify that the decorators correctly gate command execution based on
connectivity and artifact provider status.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import click
import pytest
from click.testing import CliRunner

from xsoar_cli.utilities.validators import (
    validate_artifacts_provider,
    validate_xsoar_connectivity,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(
    *,
    default_environment: str = "dev",
    connectivity_ok: bool = True,
    has_artifacts: bool = False,
    artifacts_ok: bool = True,
) -> MagicMock:
    """Build a mock XSOARConfig with configurable behavior."""
    config = MagicMock()
    config.default_environment = default_environment

    env_config = MagicMock()
    client = MagicMock()

    if connectivity_ok:
        client.test_connectivity.return_value = True
    else:
        client.test_connectivity.side_effect = ConnectionError("Connection refused")

    if has_artifacts:
        provider = MagicMock()
        if artifacts_ok:
            provider.test_connection.return_value = True
        else:
            provider.test_connection.side_effect = Exception("Artifact connection failed")
        client.artifact_provider = provider
    else:
        client.artifact_provider = None

    env_config.client = client
    config.get_environment.return_value = env_config
    config.environment_has_artifacts.return_value = has_artifacts
    config.has_environment.return_value = True

    return config


# ===========================================================================
# validate_xsoar_connectivity
# ===========================================================================


class TestValidateXsoarConnectivity:
    def test_passes_through_on_success(self) -> None:
        config = _make_config(connectivity_ok=True)

        @click.command()
        @validate_xsoar_connectivity()
        @click.pass_context
        def dummy(ctx: click.Context) -> None:
            click.echo("executed")

        runner = CliRunner()
        with patch("xsoar_cli.utilities.validators.get_xsoar_config", return_value=config):
            result = runner.invoke(dummy, [], obj=config)

        assert result.exit_code == 0
        assert "executed" in result.output

    def test_exits_on_connection_error(self) -> None:
        config = _make_config(connectivity_ok=False)

        @click.command()
        @validate_xsoar_connectivity()
        @click.pass_context
        def dummy(ctx: click.Context) -> None:
            click.echo("should not run")

        runner = CliRunner()
        with patch("xsoar_cli.utilities.validators.get_xsoar_config", return_value=config):
            result = runner.invoke(dummy, [], obj=config)

        assert result.exit_code != 0
        assert "Connection failed" in result.output
        assert "should not run" not in result.output

    def test_uses_environment_param(self) -> None:
        config = _make_config(default_environment="dev", connectivity_ok=True)

        @click.command()
        @click.option("--environment", default=None)
        @validate_xsoar_connectivity()
        @click.pass_context
        def dummy(ctx: click.Context, environment: str | None) -> None:
            click.echo("executed")

        runner = CliRunner()
        with patch("xsoar_cli.utilities.validators.get_xsoar_config", return_value=config):
            result = runner.invoke(dummy, ["--environment", "prod"], obj=config)

        config.get_environment.assert_called_with("prod")

    def test_falls_back_to_default_environment(self) -> None:
        config = _make_config(default_environment="dev", connectivity_ok=True)

        @click.command()
        @validate_xsoar_connectivity()
        @click.pass_context
        def dummy(ctx: click.Context) -> None:
            click.echo("executed")

        runner = CliRunner()
        with patch("xsoar_cli.utilities.validators.get_xsoar_config", return_value=config):
            result = runner.invoke(dummy, [], obj=config)

        config.get_environment.assert_called_with("dev")


# ===========================================================================
# validate_artifacts_provider
# ===========================================================================


class TestValidateArtifactsProvider:
    def test_passes_through_on_success(self) -> None:
        config = _make_config(has_artifacts=True, artifacts_ok=True)

        @click.command()
        @validate_artifacts_provider
        @click.pass_context
        def dummy(ctx: click.Context) -> None:
            click.echo("executed")

        runner = CliRunner()
        with patch("xsoar_cli.utilities.validators.get_xsoar_config", return_value=config):
            result = runner.invoke(dummy, [], obj=config)

        assert result.exit_code == 0
        assert "executed" in result.output

    def test_skips_validation_when_no_provider(self) -> None:
        config = _make_config(has_artifacts=False)

        @click.command()
        @validate_artifacts_provider
        @click.pass_context
        def dummy(ctx: click.Context) -> None:
            click.echo("executed")

        runner = CliRunner()
        with patch("xsoar_cli.utilities.validators.get_xsoar_config", return_value=config):
            result = runner.invoke(dummy, [], obj=config)

        assert result.exit_code == 0
        assert "executed" in result.output

    def test_exits_on_connection_failure(self) -> None:
        config = _make_config(has_artifacts=True, artifacts_ok=False)

        @click.command()
        @validate_artifacts_provider
        @click.pass_context
        def dummy(ctx: click.Context) -> None:
            click.echo("should not run")

        runner = CliRunner()
        with patch("xsoar_cli.utilities.validators.get_xsoar_config", return_value=config):
            result = runner.invoke(dummy, [], obj=config)

        assert result.exit_code != 0
        assert "Artifact repository connection failed" in result.output
        assert "should not run" not in result.output

    def test_uses_environment_param(self) -> None:
        config = _make_config(has_artifacts=True, artifacts_ok=True)

        @click.command()
        @click.option("--environment", default=None)
        @validate_artifacts_provider
        @click.pass_context
        def dummy(ctx: click.Context, environment: str | None) -> None:
            click.echo("executed")

        runner = CliRunner()
        with patch("xsoar_cli.utilities.validators.get_xsoar_config", return_value=config):
            result = runner.invoke(dummy, ["--environment", "staging"], obj=config)

        config.get_environment.assert_called_with("staging")

    def test_suggests_config_validate_on_failure(self) -> None:
        config = _make_config(has_artifacts=True, artifacts_ok=False)

        @click.command()
        @validate_artifacts_provider
        @click.pass_context
        def dummy(ctx: click.Context) -> None:
            click.echo("should not run")

        runner = CliRunner()
        with patch("xsoar_cli.utilities.validators.get_xsoar_config", return_value=config):
            result = runner.invoke(dummy, [], obj=config)

        assert "xsoar-cli config validate" in result.output
