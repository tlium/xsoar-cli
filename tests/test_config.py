from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from click.testing import CliRunner

from xsoar_cli import cli


class TestConfig:
    @patch("xsoar_cli.configuration.Client")
    @patch("pathlib.Path.is_file", MagicMock(return_value=True))
    @pytest.mark.parametrize(
        ("cli_args", "use_fixtures", "expected_return_value"),
        [
            (["config"], True, 0),
            (["config", "validate"], True, 0),
            # (["config", "get"], True, 0),
        ],
    )
    def test_config(
        self, mock_client, cli_args: list[str], use_fixtures: bool, expected_return_value: int, request: pytest.FixtureRequest
    ) -> None:  # noqa: FBT001
        mock_instance = MagicMock()
        mock_instance.test_connectivity.return_value = True
        mock_provider = MagicMock()
        mock_provider.test_connection.return_value = True
        mock_instance.artifact_provider = mock_provider
        mock_client.return_value = mock_instance

        if use_fixtures:
            mock_config_file = request.getfixturevalue("mock_config_file")  # noqa: F841
        runner = CliRunner()
        result = runner.invoke(cli.cli, cli_args)
        assert result.exit_code == expected_return_value
