from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from xsoar_cli import cli


class TestManifest:
    @patch("pathlib.Path.is_file", MagicMock(return_value=True))
    @pytest.mark.parametrize(
        ("cli_args", "use_fixtures", "expected_return_value"),
        [
            (["manifest"], False, 0),
            (["manifest", "validate", "tests/test_data/manifest_base.json"], True, 0),
            (["manifest", "validate", "tests/test_data/manifest_invalid.json"], "invalid", 1),
            (["manifest", "validate", "tests/test_data/manifest_with_pack_not_on_server.json"], "not_on_server", 0),
        ],
    )
    def test_manifest(
        self, cli_args: list[str], use_fixtures: bool | str, expected_return_value: int, request: pytest.FixtureRequest
    ) -> None:  # noqa: FBT001
        if use_fixtures == "invalid":
            mock_config_file = request.getfixturevalue("mock_config_file")  # noqa: F841
            mock_manifest = request.getfixturevalue("mock_manifest_invalid")  # noqa: F841
            mock_is_pack_available = request.getfixturevalue("mock_xsoar_client_is_pack_available")  # noqa: F841
        elif use_fixtures == "not_on_server":
            mock_config_file = request.getfixturevalue("mock_config_file")  # noqa: F841
            mock_manifest = request.getfixturevalue("mock_manifest_with_pack_not_on_server")  # noqa: F841
            mock_is_pack_available = request.getfixturevalue("mock_xsoar_client_is_pack_available")  # noqa: F841
        elif use_fixtures:
            mock_config_file = request.getfixturevalue("mock_config_file")  # noqa: F841
            mock_manifest = request.getfixturevalue("mock_manifest_base")  # noqa: F841
            mock_is_pack_available = request.getfixturevalue("mock_xsoar_client_is_pack_available")  # noqa: F841

        runner = CliRunner()
        result = runner.invoke(cli.cli, cli_args)
        print(result.output)
        assert result.exit_code == expected_return_value
