from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner
from xsoar_cli import cli


def _make_mock_client(connectivity_ok: bool = True, artifacts_ok: bool = True) -> MagicMock:
    """Create a mock XSOAR client with configurable connectivity and artifact behavior."""
    mock_instance = MagicMock()
    if connectivity_ok:
        mock_instance.test_connectivity.return_value = True
    else:
        mock_instance.test_connectivity.side_effect = ConnectionError("Connection refused")

    mock_provider = MagicMock()
    if artifacts_ok:
        mock_provider.test_connection.return_value = True
    else:
        mock_provider.test_connection.side_effect = Exception("Artifact connection failed")
    mock_instance.artifact_provider = mock_provider

    return mock_instance


class TestConfigGroup:
    """Tests for the config command group itself."""

    @patch("xsoar_cli.xsoar_client.client.Client")
    @patch("pathlib.Path.is_file", MagicMock(return_value=True))
    def test_config_group_shows_help(self, mock_client, mock_config_file) -> None:
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["config"])
        assert result.exit_code == 0


class TestConfigValidateDefault:
    """Tests for config validate with no flags (default behavior: test default environment only)."""

    @patch("xsoar_cli.xsoar_client.client.Client")
    @patch("pathlib.Path.is_file", MagicMock(return_value=True))
    def test_default_tests_only_default_environment(self, mock_client, mock_config_file) -> None:
        mock_instance = _make_mock_client()
        mock_client.return_value = mock_instance

        runner = CliRunner()
        result = runner.invoke(cli.cli, ["config", "validate"])

        assert result.exit_code == 0
        assert 'Testing "dev" environment' in result.output
        assert 'Testing "prod" environment' not in result.output

    @patch("xsoar_cli.xsoar_client.client.Client")
    @patch("pathlib.Path.is_file", MagicMock(return_value=True))
    def test_default_tests_xsoar_connectivity_and_artifacts(self, mock_client, mock_config_file) -> None:
        mock_instance = _make_mock_client()
        mock_client.return_value = mock_instance

        runner = CliRunner()
        result = runner.invoke(cli.cli, ["config", "validate"])

        assert result.exit_code == 0
        assert "XSOAR connectivity: OK" in result.output
        assert "Artifacts repository: OK" in result.output

    @patch("xsoar_cli.xsoar_client.client.Client")
    @patch("pathlib.Path.is_file", MagicMock(return_value=True))
    def test_default_connectivity_failure(self, mock_client, mock_config_file) -> None:
        mock_instance = _make_mock_client(connectivity_ok=False)
        mock_client.return_value = mock_instance

        runner = CliRunner()
        result = runner.invoke(cli.cli, ["config", "validate"])

        assert result.exit_code == 1
        assert "XSOAR connectivity: FAILED" in result.output

    @patch("xsoar_cli.xsoar_client.client.Client")
    @patch("pathlib.Path.is_file", MagicMock(return_value=True))
    def test_default_artifacts_failure(self, mock_client, mock_config_file) -> None:
        mock_instance = _make_mock_client(artifacts_ok=False)
        mock_client.return_value = mock_instance

        runner = CliRunner()
        result = runner.invoke(cli.cli, ["config", "validate"])

        assert result.exit_code == 1
        assert "XSOAR connectivity: OK" in result.output
        assert "Artifacts repository: FAILED" in result.output


class TestConfigValidateConnectivityOnly:
    """Tests for config validate --connectivity-only."""

    @patch("xsoar_cli.xsoar_client.client.Client")
    @patch("pathlib.Path.is_file", MagicMock(return_value=True))
    def test_connectivity_only_skips_artifacts(self, mock_client, mock_config_file) -> None:
        mock_instance = _make_mock_client()
        mock_client.return_value = mock_instance

        runner = CliRunner()
        result = runner.invoke(cli.cli, ["config", "validate", "--connectivity-only"])

        assert result.exit_code == 0
        assert "XSOAR connectivity: OK" in result.output
        assert "Artifacts repository" not in result.output

    @patch("xsoar_cli.xsoar_client.client.Client")
    @patch("pathlib.Path.is_file", MagicMock(return_value=True))
    def test_connectivity_only_does_not_fail_on_broken_artifacts(self, mock_client, mock_config_file) -> None:
        mock_instance = _make_mock_client(artifacts_ok=False)
        mock_client.return_value = mock_instance

        runner = CliRunner()
        result = runner.invoke(cli.cli, ["config", "validate", "--connectivity-only"])

        assert result.exit_code == 0
        assert "Artifacts repository" not in result.output

    @patch("xsoar_cli.xsoar_client.client.Client")
    @patch("pathlib.Path.is_file", MagicMock(return_value=True))
    def test_connectivity_only_fails_on_connection_error(self, mock_client, mock_config_file) -> None:
        mock_instance = _make_mock_client(connectivity_ok=False)
        mock_client.return_value = mock_instance

        runner = CliRunner()
        result = runner.invoke(cli.cli, ["config", "validate", "--connectivity-only"])

        assert result.exit_code == 1
        assert "XSOAR connectivity: FAILED" in result.output

    @patch("xsoar_cli.xsoar_client.client.Client")
    @patch("pathlib.Path.is_file", MagicMock(return_value=True))
    def test_connectivity_only_tests_only_default_environment(self, mock_client, mock_config_file) -> None:
        mock_instance = _make_mock_client()
        mock_client.return_value = mock_instance

        runner = CliRunner()
        result = runner.invoke(cli.cli, ["config", "validate", "--connectivity-only"])

        assert result.exit_code == 0
        assert 'Testing "dev" environment' in result.output
        assert 'Testing "prod" environment' not in result.output


class TestConfigValidateAll:
    """Tests for config validate --all."""

    @patch("xsoar_cli.xsoar_client.client.Client")
    @patch("pathlib.Path.is_file", MagicMock(return_value=True))
    def test_all_tests_every_environment(self, mock_client, mock_config_file) -> None:
        mock_instance = _make_mock_client()
        mock_client.return_value = mock_instance

        runner = CliRunner()
        result = runner.invoke(cli.cli, ["config", "validate", "--all"])

        assert result.exit_code == 0
        assert 'Testing "dev" environment' in result.output
        assert 'Testing "prod" environment' in result.output

    @patch("xsoar_cli.xsoar_client.client.Client")
    @patch("pathlib.Path.is_file", MagicMock(return_value=True))
    def test_all_tests_connectivity_and_artifacts(self, mock_client, mock_config_file) -> None:
        mock_instance = _make_mock_client()
        mock_client.return_value = mock_instance

        runner = CliRunner()
        result = runner.invoke(cli.cli, ["config", "validate", "--all"])

        assert result.exit_code == 0
        assert result.output.count("XSOAR connectivity: OK") == 2
        assert result.output.count("Artifacts repository: OK") == 2

    @patch("xsoar_cli.xsoar_client.client.Client")
    @patch("pathlib.Path.is_file", MagicMock(return_value=True))
    def test_all_connectivity_only_skips_artifacts(self, mock_client, mock_config_file) -> None:
        mock_instance = _make_mock_client()
        mock_client.return_value = mock_instance

        runner = CliRunner()
        result = runner.invoke(cli.cli, ["config", "validate", "--all", "--connectivity-only"])

        assert result.exit_code == 0
        assert 'Testing "dev" environment' in result.output
        assert 'Testing "prod" environment' in result.output
        assert result.output.count("XSOAR connectivity: OK") == 2
        assert "Artifacts repository" not in result.output


class TestConfigValidateOnlyTestEnvironment:
    """Tests for config validate --only-test-environment."""

    @patch("xsoar_cli.xsoar_client.client.Client")
    @patch("pathlib.Path.is_file", MagicMock(return_value=True))
    def test_only_test_environment_tests_specified_env(self, mock_client, mock_config_file) -> None:
        mock_instance = _make_mock_client()
        mock_client.return_value = mock_instance

        runner = CliRunner()
        result = runner.invoke(cli.cli, ["config", "validate", "--only-test-environment", "prod"])

        assert result.exit_code == 0
        assert 'Testing "prod" environment' in result.output
        assert 'Testing "dev" environment' not in result.output

    @patch("xsoar_cli.xsoar_client.client.Client")
    @patch("pathlib.Path.is_file", MagicMock(return_value=True))
    def test_only_test_environment_with_connectivity_only(self, mock_client, mock_config_file) -> None:
        mock_instance = _make_mock_client()
        mock_client.return_value = mock_instance

        runner = CliRunner()
        result = runner.invoke(cli.cli, ["config", "validate", "--only-test-environment", "prod", "--connectivity-only"])

        assert result.exit_code == 0
        assert 'Testing "prod" environment' in result.output
        assert "XSOAR connectivity: OK" in result.output
        assert "Artifacts repository" not in result.output

    @patch("xsoar_cli.xsoar_client.client.Client")
    @patch("pathlib.Path.is_file", MagicMock(return_value=True))
    def test_only_test_environment_nonexistent(self, mock_client, mock_config_file) -> None:
        mock_instance = _make_mock_client()
        mock_client.return_value = mock_instance

        runner = CliRunner()
        result = runner.invoke(cli.cli, ["config", "validate", "--only-test-environment", "nonexistent"])

        assert result.exit_code == 1
        assert 'environment "nonexistent" not found' in result.output


class TestConfigValidateMutualExclusivity:
    """Tests for mutual exclusivity between --all and --only-test-environment."""

    @patch("xsoar_cli.xsoar_client.client.Client")
    @patch("pathlib.Path.is_file", MagicMock(return_value=True))
    def test_all_and_only_test_environment_are_mutually_exclusive(self, mock_client, mock_config_file) -> None:
        mock_instance = _make_mock_client()
        mock_client.return_value = mock_instance

        runner = CliRunner()
        result = runner.invoke(cli.cli, ["config", "validate", "--all", "--only-test-environment", "prod"])

        assert result.exit_code != 0
        assert "mutually exclusive" in result.output


class TestConfigValidateVerbose:
    """Tests for config validate --verbose."""

    @patch("xsoar_cli.xsoar_client.client.Client")
    @patch("pathlib.Path.is_file", MagicMock(return_value=True))
    def test_verbose_shows_error_message_on_connectivity_failure(self, mock_client, mock_config_file) -> None:
        mock_instance = _make_mock_client(connectivity_ok=False)
        mock_client.return_value = mock_instance

        runner = CliRunner()
        result = runner.invoke(cli.cli, ["config", "validate", "--verbose"])

        assert result.exit_code == 1
        assert "Connection refused" in result.output

    @patch("xsoar_cli.xsoar_client.client.Client")
    @patch("pathlib.Path.is_file", MagicMock(return_value=True))
    def test_verbose_shows_error_message_on_artifacts_failure(self, mock_client, mock_config_file) -> None:
        mock_instance = _make_mock_client(artifacts_ok=False)
        mock_client.return_value = mock_instance

        runner = CliRunner()
        result = runner.invoke(cli.cli, ["config", "validate", "--verbose"])

        assert result.exit_code == 1
        assert "Artifact connection failed" in result.output
