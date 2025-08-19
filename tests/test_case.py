from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from xsoar_cli import cli


class TestCase:
    @patch("pathlib.Path.is_file", MagicMock(return_value=True))
    @pytest.mark.parametrize(
        ("cli_args", "use_fixtures", "expected_return_value"),
        [
            (["case"], False, 0),
            (["case", "--help"], False, 0),
            (["case", "get", "152230"], True, 0),
            (["case", "get", "152230"], False, 1),
            (["case", "create"], True, 0),
            (["case", "clone", "152230"], True, 0),
            (["case", "clone", "--dest", "bogus", "--source", "bogus", "152230"], True, 1),
        ],
    )
    def test_case(self, cli_args: list[str], use_fixtures: bool, expected_return_value: int, request: pytest.FixtureRequest) -> None:  # noqa: FBT001
        if "get" in cli_args and not use_fixtures:
            mock_config_file = request.getfixturevalue("mock_config_file")
            mock_xsoar_client_get_case = request.getfixturevalue("mock_xsoar_client_get_case_zero")
            mock_xsoar_client_create_case = request.getfixturevalue("mock_xsoar_client_create_case")

        else:
            mock_config_file = request.getfixturevalue("mock_config_file")  # noqa: F841
            mock_xsoar_client_get_case = request.getfixturevalue("mock_xsoar_client_get_case")  # noqa: F841
            mock_xsoar_client_create_case = request.getfixturevalue("mock_xsoar_client_create_case")  # noqa: F841

        runner = CliRunner()
        result = runner.invoke(cli.cli, cli_args)
        print(result.output)
        assert result.exit_code == expected_return_value
