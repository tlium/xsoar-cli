"""CLI integration tests for the ``completions`` command group."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    from pathlib import Path

    from tests.cli.conftest import InvokeHelper


class TestCompletionsGroup:
    """Tests for the ``completions`` group itself."""

    def test_shows_help(self, invoke: InvokeHelper) -> None:
        result = invoke(["completions"])
        assert result.exit_code == 0
        assert "install" in result.output
        assert "uninstall" in result.output

    def test_help_flag(self, invoke: InvokeHelper) -> None:
        result = invoke(["completions", "--help"])
        assert result.exit_code == 0
        assert "Install and manage shell completion" in result.output


class TestCompletionsInstall:
    """Tests for ``completions install``."""

    def test_install_zsh_plain(self, invoke: InvokeHelper, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SHELL", "/bin/zsh")
        monkeypatch.delenv("ZSH_CUSTOM", raising=False)
        fake_home = tmp_path / "home"
        fake_home.mkdir()

        with patch("xsoar_cli.commands.completions.commands.Path.home", return_value=fake_home):
            result = invoke(["completions", "install"])

        assert result.exit_code == 0
        target = fake_home / ".zfunc" / "_xsoar-cli"
        assert target.is_file()
        assert "Completion script written to" in result.output
        assert "fpath+=~/.zfunc" in result.output

    def test_install_zsh_ohmyzsh_via_env(self, invoke: InvokeHelper, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SHELL", "/bin/zsh")
        custom_dir = tmp_path / "custom"
        custom_dir.mkdir()
        monkeypatch.setenv("ZSH_CUSTOM", str(custom_dir))

        result = invoke(["completions", "install"])

        assert result.exit_code == 0
        target = custom_dir / "completions" / "_xsoar-cli"
        assert target.is_file()
        assert "Completion script written to" in result.output
        assert "exec zsh" in result.output
        assert "fpath" not in result.output

    def test_install_zsh_ohmyzsh_via_directory(self, invoke: InvokeHelper, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SHELL", "/bin/zsh")
        monkeypatch.delenv("ZSH_CUSTOM", raising=False)
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        (fake_home / ".oh-my-zsh").mkdir()

        with patch("xsoar_cli.commands.completions.commands.Path.home", return_value=fake_home):
            result = invoke(["completions", "install"])

        assert result.exit_code == 0
        target = fake_home / ".oh-my-zsh" / "custom" / "completions" / "_xsoar-cli"
        assert target.is_file()
        assert "exec zsh" in result.output
        assert "fpath" not in result.output

    def test_install_bash(self, invoke: InvokeHelper, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SHELL", "/bin/bash")
        fake_home = tmp_path / "home"
        fake_home.mkdir()

        with patch("xsoar_cli.commands.completions.commands.Path.home", return_value=fake_home):
            result = invoke(["completions", "install"])

        assert result.exit_code == 0
        target = fake_home / ".xsoar-cli-complete.bash"
        assert target.is_file()
        assert "source" in result.output
        assert ".bashrc" in result.output

    def test_install_fish(self, invoke: InvokeHelper, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SHELL", "/usr/bin/fish")
        fake_home = tmp_path / "home"
        fake_home.mkdir()

        with patch("xsoar_cli.commands.completions.commands.Path.home", return_value=fake_home):
            result = invoke(["completions", "install"])

        assert result.exit_code == 0
        target = fake_home / ".config" / "fish" / "completions" / "xsoar-cli.fish"
        assert target.is_file()
        assert "No further configuration needed" in result.output

    def test_install_explicit_shell_overrides_env(self, invoke: InvokeHelper, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SHELL", "/bin/zsh")
        fake_home = tmp_path / "home"
        fake_home.mkdir()

        with patch("xsoar_cli.commands.completions.commands.Path.home", return_value=fake_home):
            result = invoke(["completions", "install", "--shell", "bash"])

        assert result.exit_code == 0
        target = fake_home / ".xsoar-cli-complete.bash"
        assert target.is_file()

    def test_install_no_shell_detected(self, invoke: InvokeHelper, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SHELL", raising=False)
        result = invoke(["completions", "install"])
        assert result.exit_code != 0
        assert "Could not detect shell" in result.output

    def test_install_unsupported_shell_env(self, invoke: InvokeHelper, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SHELL", "/bin/csh")
        result = invoke(["completions", "install"])
        assert result.exit_code != 0
        assert "Could not detect shell" in result.output

    def test_install_overwrites_existing(self, invoke: InvokeHelper, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SHELL", "/bin/bash")
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        target = fake_home / ".xsoar-cli-complete.bash"
        target.write_text("old content")

        with patch("xsoar_cli.commands.completions.commands.Path.home", return_value=fake_home):
            result = invoke(["completions", "install"])

        assert result.exit_code == 0
        assert target.read_text() != "old content"

    def test_install_generates_valid_script(self, invoke: InvokeHelper, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SHELL", "/bin/zsh")
        monkeypatch.delenv("ZSH_CUSTOM", raising=False)
        fake_home = tmp_path / "home"
        fake_home.mkdir()

        with patch("xsoar_cli.commands.completions.commands.Path.home", return_value=fake_home):
            result = invoke(["completions", "install"])

        assert result.exit_code == 0
        target = fake_home / ".zfunc" / "_xsoar-cli"
        content = target.read_text()
        assert "_xsoar_cli_completion" in content or "compdef" in content or "XSOAR_CLI_COMPLETE" in content


class TestCompletionsUninstall:
    """Tests for ``completions uninstall``."""

    def test_uninstall_removes_file(self, invoke: InvokeHelper, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SHELL", "/bin/bash")
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        target = fake_home / ".xsoar-cli-complete.bash"
        target.write_text("completion script content")

        with patch("xsoar_cli.commands.completions.commands.Path.home", return_value=fake_home):
            result = invoke(["completions", "uninstall"])

        assert result.exit_code == 0
        assert not target.exists()
        assert "Removed completion file" in result.output

    def test_uninstall_file_not_found(self, invoke: InvokeHelper, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SHELL", "/bin/bash")
        fake_home = tmp_path / "home"
        fake_home.mkdir()

        with patch("xsoar_cli.commands.completions.commands.Path.home", return_value=fake_home):
            result = invoke(["completions", "uninstall"])

        assert result.exit_code == 0
        assert "No completion file found" in result.output

    def test_uninstall_zsh_ohmyzsh(self, invoke: InvokeHelper, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SHELL", "/bin/zsh")
        custom_dir = tmp_path / "custom"
        completions_dir = custom_dir / "completions"
        completions_dir.mkdir(parents=True)
        target = completions_dir / "_xsoar-cli"
        target.write_text("completion script content")
        monkeypatch.setenv("ZSH_CUSTOM", str(custom_dir))

        result = invoke(["completions", "uninstall"])

        assert result.exit_code == 0
        assert not target.exists()
        assert "Removed completion file" in result.output

    def test_uninstall_fish(self, invoke: InvokeHelper, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SHELL", "/usr/bin/fish")
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        target = fake_home / ".config" / "fish" / "completions" / "xsoar-cli.fish"
        target.parent.mkdir(parents=True)
        target.write_text("completion script content")

        with patch("xsoar_cli.commands.completions.commands.Path.home", return_value=fake_home):
            result = invoke(["completions", "uninstall"])

        assert result.exit_code == 0
        assert not target.exists()

    def test_uninstall_explicit_shell(self, invoke: InvokeHelper, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SHELL", "/bin/zsh")
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        target = fake_home / ".xsoar-cli-complete.bash"
        target.write_text("completion script content")

        with patch("xsoar_cli.commands.completions.commands.Path.home", return_value=fake_home):
            result = invoke(["completions", "uninstall", "--shell", "bash"])

        assert result.exit_code == 0
        assert not target.exists()

    def test_uninstall_no_shell_detected(self, invoke: InvokeHelper, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SHELL", raising=False)
        result = invoke(["completions", "uninstall"])
        assert result.exit_code != 0
        assert "Could not detect shell" in result.output

    def test_uninstall_bash_shows_bashrc_reminder(self, invoke: InvokeHelper, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SHELL", "/bin/bash")
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        target = fake_home / ".xsoar-cli-complete.bash"
        target.write_text("completion script content")

        with patch("xsoar_cli.commands.completions.commands.Path.home", return_value=fake_home):
            result = invoke(["completions", "uninstall"])

        assert result.exit_code == 0
        assert ".bashrc" in result.output


class TestCompletionsRoundTrip:
    """Tests that install followed by uninstall leaves no artifacts."""

    def test_install_then_uninstall(self, invoke: InvokeHelper, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SHELL", "/bin/bash")
        fake_home = tmp_path / "home"
        fake_home.mkdir()

        with patch("xsoar_cli.commands.completions.commands.Path.home", return_value=fake_home):
            result = invoke(["completions", "install"])
            assert result.exit_code == 0

            target = fake_home / ".xsoar-cli-complete.bash"
            assert target.is_file()

            result = invoke(["completions", "uninstall"])
            assert result.exit_code == 0
            assert not target.exists()
