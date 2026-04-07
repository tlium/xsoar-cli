"""CLI integration tests for the ``config`` command group."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tests.cli.conftest import InvokeHelper


class TestConfigGroup:
    """Tests for the config command group itself."""

    def test_config_group_shows_help(self, invoke: InvokeHelper, mock_xsoar_env) -> None:
        result = invoke(["config"])
        assert result.exit_code == 0


class TestConfigValidateDefault:
    """Tests for config validate with no flags (default behavior: test default environment only)."""

    def test_default_tests_only_default_environment(self, invoke: InvokeHelper, mock_xsoar_env, make_mock_client) -> None:
        mock_xsoar_env.client_cls.return_value = make_mock_client()
        result = invoke(["config", "validate"])
        assert result.exit_code == 0
        assert 'Testing "dev" environment' in result.output
        assert 'Testing "prod" environment' not in result.output

    def test_default_tests_xsoar_connectivity_and_artifacts(self, invoke: InvokeHelper, mock_xsoar_env, make_mock_client) -> None:
        mock_xsoar_env.client_cls.return_value = make_mock_client()
        result = invoke(["config", "validate"])
        assert result.exit_code == 0
        assert "XSOAR connectivity: OK" in result.output
        assert "Artifacts repository: OK" in result.output

    def test_default_connectivity_failure(self, invoke: InvokeHelper, mock_xsoar_env, make_mock_client) -> None:
        mock_xsoar_env.client_cls.return_value = make_mock_client(connectivity_ok=False)
        result = invoke(["config", "validate"])
        assert result.exit_code == 1
        assert "XSOAR connectivity: FAILED" in result.output

    def test_default_artifacts_failure(self, invoke: InvokeHelper, mock_xsoar_env, make_mock_client) -> None:
        mock_xsoar_env.client_cls.return_value = make_mock_client(artifacts_ok=False)
        result = invoke(["config", "validate"])
        assert result.exit_code == 1
        assert "XSOAR connectivity: OK" in result.output
        assert "Artifacts repository: FAILED" in result.output


class TestConfigValidateConnectivityOnly:
    """Tests for config validate --connectivity-only."""

    def test_connectivity_only_skips_artifacts(self, invoke: InvokeHelper, mock_xsoar_env, make_mock_client) -> None:
        mock_xsoar_env.client_cls.return_value = make_mock_client()
        result = invoke(["config", "validate", "--connectivity-only"])
        assert result.exit_code == 0
        assert "XSOAR connectivity: OK" in result.output
        assert "Artifacts repository" not in result.output

    def test_connectivity_only_does_not_fail_on_broken_artifacts(self, invoke: InvokeHelper, mock_xsoar_env, make_mock_client) -> None:
        mock_xsoar_env.client_cls.return_value = make_mock_client(artifacts_ok=False)
        result = invoke(["config", "validate", "--connectivity-only"])
        assert result.exit_code == 0
        assert "Artifacts repository" not in result.output

    def test_connectivity_only_fails_on_connection_error(self, invoke: InvokeHelper, mock_xsoar_env, make_mock_client) -> None:
        mock_xsoar_env.client_cls.return_value = make_mock_client(connectivity_ok=False)
        result = invoke(["config", "validate", "--connectivity-only"])
        assert result.exit_code == 1
        assert "XSOAR connectivity: FAILED" in result.output

    def test_connectivity_only_tests_only_default_environment(self, invoke: InvokeHelper, mock_xsoar_env, make_mock_client) -> None:
        mock_xsoar_env.client_cls.return_value = make_mock_client()
        result = invoke(["config", "validate", "--connectivity-only"])
        assert result.exit_code == 0
        assert 'Testing "dev" environment' in result.output
        assert 'Testing "prod" environment' not in result.output


class TestConfigValidateAll:
    """Tests for config validate --all."""

    def test_all_tests_every_environment(self, invoke: InvokeHelper, mock_xsoar_env, make_mock_client) -> None:
        mock_xsoar_env.client_cls.return_value = make_mock_client()
        result = invoke(["config", "validate", "--all"])
        assert result.exit_code == 0
        assert 'Testing "dev" environment' in result.output
        assert 'Testing "prod" environment' in result.output

    def test_all_tests_connectivity_and_artifacts(self, invoke: InvokeHelper, mock_xsoar_env, make_mock_client) -> None:
        mock_xsoar_env.client_cls.return_value = make_mock_client()
        result = invoke(["config", "validate", "--all"])
        assert result.exit_code == 0
        assert result.output.count("XSOAR connectivity: OK") == 2
        assert result.output.count("Artifacts repository: OK") == 2

    def test_all_connectivity_only_skips_artifacts(self, invoke: InvokeHelper, mock_xsoar_env, make_mock_client) -> None:
        mock_xsoar_env.client_cls.return_value = make_mock_client()
        result = invoke(["config", "validate", "--all", "--connectivity-only"])
        assert result.exit_code == 0
        assert 'Testing "dev" environment' in result.output
        assert 'Testing "prod" environment' in result.output
        assert result.output.count("XSOAR connectivity: OK") == 2
        assert "Artifacts repository" not in result.output


class TestConfigValidateOnlyTestEnvironment:
    """Tests for config validate --only-test-environment."""

    def test_only_test_environment_tests_specified_env(self, invoke: InvokeHelper, mock_xsoar_env, make_mock_client) -> None:
        mock_xsoar_env.client_cls.return_value = make_mock_client()
        result = invoke(["config", "validate", "--only-test-environment", "prod"])
        assert result.exit_code == 0
        assert 'Testing "prod" environment' in result.output
        assert 'Testing "dev" environment' not in result.output

    def test_only_test_environment_with_connectivity_only(self, invoke: InvokeHelper, mock_xsoar_env, make_mock_client) -> None:
        mock_xsoar_env.client_cls.return_value = make_mock_client()
        result = invoke(["config", "validate", "--only-test-environment", "prod", "--connectivity-only"])
        assert result.exit_code == 0
        assert 'Testing "prod" environment' in result.output
        assert "XSOAR connectivity: OK" in result.output
        assert "Artifacts repository" not in result.output

    def test_only_test_environment_nonexistent(self, invoke: InvokeHelper, mock_xsoar_env, make_mock_client) -> None:
        mock_xsoar_env.client_cls.return_value = make_mock_client()
        result = invoke(["config", "validate", "--only-test-environment", "nonexistent"])
        assert result.exit_code == 1
        assert 'environment "nonexistent" not found' in result.output


class TestConfigValidateMutualExclusivity:
    """Tests for mutual exclusivity between --all and --only-test-environment."""

    def test_all_and_only_test_environment_are_mutually_exclusive(self, invoke: InvokeHelper, mock_xsoar_env, make_mock_client) -> None:
        mock_xsoar_env.client_cls.return_value = make_mock_client()
        result = invoke(["config", "validate", "--all", "--only-test-environment", "prod"])
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output


class TestConfigValidateVerbose:
    """Tests for config validate --verbose."""

    def test_verbose_shows_error_message_on_connectivity_failure(self, invoke: InvokeHelper, mock_xsoar_env, make_mock_client) -> None:
        mock_xsoar_env.client_cls.return_value = make_mock_client(connectivity_ok=False)
        result = invoke(["config", "validate", "--verbose"])
        assert result.exit_code == 1
        assert "Connection refused" in result.output

    def test_verbose_shows_error_message_on_artifacts_failure(self, invoke: InvokeHelper, mock_xsoar_env, make_mock_client) -> None:
        mock_xsoar_env.client_cls.return_value = make_mock_client(artifacts_ok=False)
        result = invoke(["config", "validate", "--verbose"])
        assert result.exit_code == 1
        assert "Artifact connection failed" in result.output
