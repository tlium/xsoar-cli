# CLAUDE.md

Project reference for AI assistants working with the xsoar-cli codebase.

## Project Overview

This is a CLI tool for managing Palo Alto Networks XSOAR (Cortex XSOAR). Built with Python and Click. Supports XSOAR server versions 6 and 8.
The primary purpose for xsoar-cli is to be used both in CICD pipelines to deploy new content to XSOAR, as well as a tool for daily use by
developers and power users who want to automate daily tasks.

Backwards compatibility matters for the CLI surface: commands, arguments, and options should remain stable. Internal APIs (module layout,
class imports, helper functions) can change freely, but changes with a wide blast radius should be made carefully to avoid introducing
bugs silently. The user base is small and actively communicating, so even CLI-level breaking changes may be acceptable if there are clear
benefits in doing so.

The xsoar-cli project includes an integrated XSOAR API client (`xsoar_cli.xsoar_client`), which was previously a standalone package
(xsoar-client). It is also tightly integrated with xsoar-dependency-graph (hosted on https://github.com/tlium/xsoar-dependency-graph).
Development on xsoar-dependency-graph and xsoar-cli is all done by the same developers. Suggesting modifications in
xsoar-dependency-graph is acceptable if such modifications are required for new functionality or bugfixes in xsoar-cli.

Properly debugging the various functionality in xsoar-cli depends on connectivity to XSOAR, AWS/Azure credentials and other things. Always ask a user
for confirmation before executing any terminal commands as they may have consequences you may not be fully aware of.

## Tech Stack

- **Language**: Python 3.10+
- **CLI Framework**: Click
- **Build System**: Hatchling (`pyproject.toml`)
- **Package Manager**: uv (`uv.lock`)
- **Linting**: Ruff
- **Formatting**: Black
- **Testing**: pytest, pytest-cov
- **CI**: GitHub Actions (Python 3.10-3.14)

## Project Layout

```
CHANGELOG.md              # Changelog (Keep a Changelog format)
src/xsoar_cli/            # Main package (src layout)
  cli.py                  # Entry point, Click group, plugin loading
  configuration.py        # XSOARConfig class, EnvironmentConfig
  log.py                  # Logging setup
  error_handling/         # Error handling
    connection.py         # ConnectionErrorHandler
    http.py               # HTTPErrorHandler
  utilities/              # Shared helpers and validators
    config_file.py        # Config file I/O, get_xsoar_config, load_config
    validators.py         # Connectivity and artifact provider validators
    manifest.py           # Manifest comparison helpers
    generic.py            # General-purpose helpers
  xsoar_client/           # XSOAR API client (merged from xsoar-client)
    client.py             # Client class, HTTP request handling
    config.py             # ClientConfig dataclass
    constants.py          # Shared constants (XSOAR_OLD_VERSION, HTTP_CALL_TIMEOUT)
    cases.py              # Cases domain class
    content.py            # Content domain class
    integrations.py       # Integrations domain class
    packs.py              # Packs domain class
    rbac.py               # Rbac domain class
    artifact_providers/   # Artifact storage providers
      base.py             # BaseArtifactProvider ABC
      s3.py               # S3ArtifactProvider (AWS)
      azure.py            # AzureArtifactProvider (Azure Blob Storage)
  commands/               # CLI command groups
    case/                 # Case operations command group
    config/               # Config management command group
    graph/                # Dependency graph command group
    integration/          # Integration instance config command group
    manifest/             # Manifest validate/deploy command group
    pack/                 # Pack operations command group
    playbook/             # Playbook download command group
    plugins/              # Plugin CLI commands
    rbac/                 # RBAC dump command group
  plugins/                # Plugin system infrastructure
    manager.py            # PluginManager
tests/                    # Test suite
  conftest.py             # Shared fixtures
  test_*.py               # Test modules per command group
```

## Common Commands

```sh
# Install dependencies
uv sync
uv pip install -r requirements.txt
uv pip install -r requirements_dev.txt
uv pip install -e .

# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=src/xsoar_cli

# Run a single test file
uv run pytest tests/test_manifest.py

# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Run the CLI
uv run xsoar-cli --help
```

## Code Conventions

- Entry point: `xsoar_cli.cli:main` (defined in `pyproject.toml` under `[project.scripts]`)
- Each command group lives in its own subpackage under `src/xsoar_cli/commands/` with a `commands.py` module
- Each command group has its own `README.md` documenting usage
- Commands are registered on the root Click group in `cli.py` via `cli.add_command()`
- The `@load_config` decorator (in `utilities/config_file.py`) handles config loading and injects `XSOARConfig` into `ctx.obj`
- Use `click.echo()` for user-facing output, `logging` for debug/file logs
- Commands that iterate over both `custom_packs` and `marketplace_packs` must use a `pack_type` variable (`"Custom"` / `"Marketplace"`) and include it in all log messages so the pack origin is always explicit in debug output
- Logging setup in `cli.py` is intentionally deferred to `main()`. Command and plugin registration happen at module level, but `_configure_logging()` must not be moved there. See inline comments in `cli.py` for details
- Ruff noqa comments are used where rules are intentionally suppressed (e.g., `# noqa: PLR0913` for many parameters, `# noqa: ANN201` for fixture return types)
- Type hints are used throughout; `str | None` union syntax (Python 3.10+)
- Heavy third-party imports (`xsoar_cli.xsoar_client`, `xsoar_dependency_graph`, `demisto_client`, etc.) must be deferred into the function or method bodies that use them, not imported at module level. This avoids loading slow transitive dependencies (boto3, azure-storage-blob, matplotlib, networkx, etc.) at CLI startup, keeping `--help` and `--version` fast. Use `from __future__ import annotations` together with a `TYPE_CHECKING` block so type hints remain clean and unquoted. Mark each deferred import with the comment `# Lazy import for performance reasons`. When patching deferred imports in tests, patch at the source (e.g., `xsoar_cli.xsoar_client.client.Client`) rather than the importing module (`xsoar_cli.configuration.Client`)
- The XSOAR client uses domain classes (`client.cases`, `client.packs`, `client.rbac`, etc.) for API operations. Command modules should call the domain class methods directly (e.g., `xsoar_client.cases.get()`) rather than methods on the Client class itself
- Tests must not produce side effects on the real filesystem, such as writing to the log file or modifying the user's config file. Tests invoke `cli()` directly via Click's `CliRunner`, bypassing `main()` and its logging setup
- Tests must mock all config file I/O. Any test that exercises code paths touching `get_config_file_contents`, `get_config_file_path`, or `Path.write_text` on the config file must patch these to prevent real filesystem access. The `mock_config_file` fixture in `conftest.py` is the standard way to do this
- Tests use `unittest.mock.patch` to mock external dependencies (`xsoar_cli.xsoar_client`, config file I/O)
- Test classes follow `class TestX` naming; test methods use `test_` prefix
- Fixtures are defined in `tests/conftest.py` and requested via `request.getfixturevalue()` for conditional use

## Configuration

- User config lives at `~/.config/xsoar-cli/config.json`
- Template generation: `xsoar-cli config create`
- Supports multiple named environments under `server_config`
- `default_environment` selects the active environment
- `custom_pack_authors` distinguishes custom packs from marketplace packs

## Sensitive Files

The user's live configuration at `~/.config/xsoar-cli/config.json` contains API tokens and other credentials. Corrupting or overwriting this file breaks the user's ability to interact with XSOAR.

- Never under any circumstance read, write, or execute commands that touch `~/.config/xsoar-cli/config.json` without explicit user permission. This includes running `xsoar-cli config create`, `xsoar-cli config set-credentials`, `xsoar-cli config set-azure-token`, or `xsoar-cli config show --unmask`
- Never run `xsoar-cli` subcommands via terminal that could modify the user's live configuration. When testing CLI changes, rely on the test suite (`uv run pytest`), not direct CLI invocations
- When editing config-related code (`config_file.py`, `commands/config/commands.py`, `configuration.py`), never propose changes that remove or weaken the existing mocking of `get_config_file_contents` or `get_config_file_path` in tests

## Workflow

- Write comments and documentation in plain, natural language. Avoid formal or academic wording where a simpler alternative exists. Do not use em dashes ("--" or "—") as parenthetical separators; use periods, commas, or parentheses instead. Avoid filler phrases like "It is worth noting that" or "It should be noted that". Keep sentences short and direct.
- Never start with code. Always plan changes properly before implementation. Ask for clarification in case of inconsistencies or missing information. Do not make assumptions. Confirm with user before generating code.
- In case of larger modifications, do implementation in logically grouped steps. Complex modifications may be broken down further.
- After completing each step, stop and wait for the user to review and confirm before proceeding to the next step.
- Each step should be small enough to be comfortably reviewed. As a rule of thumb, no more than one or two files modified per step.

## Changelog

- The project maintains a `CHANGELOG.md` in the repository root.
- The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
- All user-facing changes must be documented in `CHANGELOG.md`. This includes:
  - Adding, removing, or renaming commands, options, or arguments (`Added` / `Removed`)
  - Changes to default behavior or output format (`Changed`)
  - Bug fixes (`Fixed`)
  - Refactors or internal changes that alter observable behavior (`Changed`)
- When an option or command is renamed, document both the addition of the new name (`Added` or `Changed`) and the removal of the old name (`Removed`).
- Internal refactors that do not affect CLI behavior do not need a changelog entry.
- New entries go under the `## [Unreleased]` section, grouped by type: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`.
- When a release is cut, the `[Unreleased]` entries are moved under a new version heading with the release date.

## Plugin System

- Plugins extend the CLI with custom Click commands
- `PluginManager` in `src/xsoar_cli/plugins/manager.py` handles discovery, loading, and registration
- Plugins are loaded after core commands; failures are warned but non-fatal
- Core command names are captured before plugin registration to prevent conflicts
