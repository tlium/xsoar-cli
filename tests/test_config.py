from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from xsoar_cli import cli


class TestConfig:
    # @pytest.mark.usefixtures("mock_config_file")
    @patch("xsoar_client.xsoar_client.Client.test_connectivity", MagicMock(return_value=True))
    @patch("pathlib.Path.is_file", MagicMock(return_value=True))
    @pytest.mark.parametrize(
        ("cli_args", "use_fixtures", "expected_return_value"),
        [
            (["config"], True, 0),
            (["config", "validate"], True, 0),
            # (["config", "get"], True, 0),
        ],
    )
    def test_config(self, cli_args: list[str], use_fixtures: bool, expected_return_value: int, request: pytest.FixtureRequest) -> None:  # noqa: FBT001
        if use_fixtures:
            mock_config_file = request.getfixturevalue("mock_config_file")  # noqa: F841
        runner = CliRunner()
        result = runner.invoke(cli.cli, cli_args)
        assert result.exit_code == expected_return_value
        print(result.output)
