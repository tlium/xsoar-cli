import pytest
from click.testing import CliRunner

from xsoar_cli import cli


class TestBase:
    @pytest.mark.usefixtures("mock_xsoar_client_get_case")
    @pytest.mark.parametrize(
        ("cli_args", "expected_return_value"),
        [
            ([], 0),
            (["--version"], 0),
            (["--help"], 0),
        ],
    )
    def test_base(self, cli_args: list[str], expected_return_value: int) -> None:
        runner = CliRunner()
        result = runner.invoke(cli.cli, cli_args)
        assert result.exit_code == expected_return_value
