import pytest
from click.testing import CliRunner

from xsoar_cli import cli


class TestPack:
    @pytest.mark.parametrize(
        ("cli_args", "expected_return_value"),
        [
            (["pack"], 0),
        ],
    )
    def test_pack(self, cli_args: list[str], expected_return_value: int) -> None:
        runner = CliRunner()
        result = runner.invoke(cli.cli, cli_args)
        assert result.exit_code == expected_return_value
