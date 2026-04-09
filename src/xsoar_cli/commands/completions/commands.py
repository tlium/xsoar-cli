"""Shell completion install and uninstall commands."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import click

logger = logging.getLogger(__name__)

SHELLS = ("bash", "zsh", "fish")
PROG_NAME = "xsoar-cli"
COMPLETE_VAR = "_XSOAR_CLI_COMPLETE"


def _detect_shell() -> str | None:
    """Detect the current shell from the SHELL environment variable."""
    shell_path = os.environ.get("SHELL", "")
    if not shell_path:
        return None
    shell_name = Path(shell_path).name
    if shell_name in SHELLS:
        return shell_name
    return None


def _get_completion_path(shell: str) -> Path:
    """Return the target path for the completion script."""
    home = Path.home()
    if shell == "zsh":
        # Prefer Oh My Zsh custom completions directory if available.
        zsh_custom = os.environ.get("ZSH_CUSTOM")
        if zsh_custom:
            return Path(zsh_custom) / "completions" / f"_{PROG_NAME}"
        omz_default = home / ".oh-my-zsh"
        if omz_default.is_dir():
            return omz_default / "custom" / "completions" / f"_{PROG_NAME}"
        return home / ".zfunc" / f"_{PROG_NAME}"
    if shell == "bash":
        return home / f".{PROG_NAME}-complete.bash"
    if shell == "fish":
        return home / ".config" / "fish" / "completions" / f"{PROG_NAME}.fish"
    msg = f"Unsupported shell: {shell}"
    raise ValueError(msg)


def _generate_completion_script(shell: str) -> str:
    """Generate the Click completion script for the given shell."""
    # Lazy import to avoid circular import at module load time. The cli
    # module imports this command group at startup, but this function is
    # only called when the user runs "completions install".
    from click.shell_completion import get_completion_class  # Lazy import for performance reasons

    from xsoar_cli.cli import cli as cli_group  # Lazy import for performance reasons

    cls = get_completion_class(shell)
    if cls is None:
        msg = f"No completion support for shell: {shell}"
        raise click.ClickException(msg)
    comp = cls(cli_group, {}, PROG_NAME, COMPLETE_VAR)
    return comp.source()


def _resolve_shell(shell_name: str | None) -> str:
    """Return a validated shell name, auto-detecting if not provided."""
    if shell_name is not None:
        return shell_name
    detected = _detect_shell()
    if detected is None:
        raise click.ClickException("Could not detect shell from $SHELL. Use --shell to specify it explicitly.")
    return detected


@click.group()
def completions() -> None:
    """Install and manage shell completion for xsoar-cli"""
    pass


@click.command()
@click.option(
    "--shell",
    "shell_name",
    type=click.Choice(SHELLS),
    default=None,
    help="Target shell. Auto-detected from $SHELL if not specified.",
)
def install(shell_name: str | None) -> None:
    """Install shell completion for xsoar-cli."""
    shell = _resolve_shell(shell_name)
    script = _generate_completion_script(shell)
    target = _get_completion_path(shell)

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(script)
    logger.info("Wrote %s completion script to %s", shell, target)
    click.echo(f"Completion script written to {target}")

    if shell == "zsh":
        zsh_custom = os.environ.get("ZSH_CUSTOM")
        omz_dir = Path.home() / ".oh-my-zsh"
        if not zsh_custom and not omz_dir.is_dir():
            click.echo(
                "\nAdd the following to your ~/.zshrc (before compinit):"
                "\n\n  fpath+=~/.zfunc"
                "\n  autoload -Uz compinit && compinit"
                "\n\nThen reload with: exec zsh"
            )
        else:
            click.echo("\nReload your shell with: exec zsh")
    elif shell == "bash":
        click.echo(f"\nAdd the following to your ~/.bashrc:\n\n  source {target}\n\nThen reload with: source ~/.bashrc")
    elif shell == "fish":
        click.echo("\nNo further configuration needed. Reload with: exec fish")


@click.command()
@click.option(
    "--shell",
    "shell_name",
    type=click.Choice(SHELLS),
    default=None,
    help="Target shell. Auto-detected from $SHELL if not specified.",
)
def uninstall(shell_name: str | None) -> None:
    """Remove shell completion for xsoar-cli."""
    shell = _resolve_shell(shell_name)
    target = _get_completion_path(shell)

    if not target.is_file():
        click.echo(f"No completion file found at {target}")
        return

    target.unlink()
    logger.info("Removed %s completion script from %s", shell, target)
    click.echo(f"Removed completion file {target}")

    if shell == "bash":
        click.echo(f"\nRemember to remove the following line from your ~/.bashrc:\n\n  source {target}")


completions.add_command(install)
completions.add_command(uninstall)
