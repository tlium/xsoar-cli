from __future__ import annotations

import pytest


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
