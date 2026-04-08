"""Tests for the main() entry point in cli.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestMainCompletionBypass:
    """Verify that main() skips logging and version check during shell completion."""

    @pytest.fixture(autouse=True)
    def _patch_cli_group(self):
        """Patch cli() so it doesn't actually invoke Click machinery."""
        with patch("xsoar_cli.cli.cli") as mock_cli:
            # Simulate a normal Click exit.
            mock_cli.side_effect = SystemExit(0)
            self.mock_cli = mock_cli
            yield

    @pytest.fixture
    def _set_complete_env(self, monkeypatch):
        """Set the _XSOAR_CLI_COMPLETE env var."""
        monkeypatch.setenv("_XSOAR_CLI_COMPLETE", "zsh_source")

    @patch("xsoar_cli.cli.check_for_update")
    @patch("xsoar_cli.cli._configure_logging")
    @patch("xsoar_cli.cli.read_config_file")
    def test_normal_invocation_runs_version_check(self, mock_read_config, mock_logging, mock_update) -> None:
        from xsoar_cli.cli import main

        mock_read_config.return_value = {}
        mock_logging.return_value = MagicMock()
        mock_update.return_value = None

        with pytest.raises(SystemExit):
            main()

        mock_read_config.assert_called_once()
        mock_logging.assert_called_once()
        mock_update.assert_called_once()

    @pytest.mark.usefixtures("_set_complete_env")
    @patch("xsoar_cli.cli.check_for_update")
    @patch("xsoar_cli.cli._configure_logging")
    @patch("xsoar_cli.cli.read_config_file")
    def test_completion_skips_version_check(self, mock_read_config, mock_logging, mock_update) -> None:
        from xsoar_cli.cli import main

        self.mock_cli.side_effect = None

        main()

        mock_read_config.assert_not_called()
        mock_logging.assert_not_called()
        mock_update.assert_not_called()

    @pytest.mark.usefixtures("_set_complete_env")
    def test_completion_calls_cli_without_args(self) -> None:
        from xsoar_cli.cli import main

        self.mock_cli.side_effect = None

        main()

        self.mock_cli.assert_called_once_with()

    @pytest.mark.usefixtures("_set_complete_env")
    @patch("xsoar_cli.cli.check_for_update")
    @patch("xsoar_cli.cli._configure_logging")
    @patch("xsoar_cli.cli.read_config_file")
    @pytest.mark.parametrize(
        "complete_value",
        ["zsh_source", "zsh_complete", "bash_source", "bash_complete", "fish_source", "fish_complete"],
    )
    def test_completion_skips_for_all_shells(self, mock_read_config, mock_logging, mock_update, complete_value, monkeypatch) -> None:
        from xsoar_cli.cli import main

        monkeypatch.setenv("_XSOAR_CLI_COMPLETE", complete_value)
        self.mock_cli.side_effect = None

        main()

        mock_read_config.assert_not_called()
        mock_logging.assert_not_called()
        mock_update.assert_not_called()
