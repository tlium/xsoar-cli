# CLAUDE.md

Project reference for AI assistants working with the xsoar-cli codebase.

## Project Overview

This is a CLI tool for managing Palo Alto Networks XSOAR (Cortex XSOAR). Built with Python and Click. Supports XSOAR server versions 6 and 8.
The primary purpose for xsoar-cli is to be used both in CICD pipelines to deploy new content to XSOAR, as well as a tool for daily use by
developers and power users who want to automate daily tasks.

We aim to not break backwards compatibility, but the user base is small and actively communicating, so breaking backwards compatibility may
be acceptable if there are clear benefits in doing so.

The xsoar-cli project is tightly integrated with two other Python modules:
 - xsoar-client (hosted on https://github.com/tlium/xsoar-client)
 - xsoar-dependency-graph (hosted on https://github.com/tlium/xsoar-dependency-graph)
Development on xsoar-client, xsoar-dependency-graph and xsoar-cli is all done by the same developers. Suggesting modifications in the two
aforementioned Python packages is acceptable if such modifications are required for new functionality or bugfixes in xsoar-cli.

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
src/xsoar_cli/           # Main package (src layout)
  __about__.py            # Version (dynamic, read by hatch)
  cli.py                  # Entry point, Click group, plugin loading
  configuration.py        # XSOARConfig class
  connection_errors.py    # Error handling
  log.py                  # Logging setup
  utilities.py            # Shared helpers, decorators
  case/                   # Case operations command group
  config/                 # Config management command group
  graph/                  # Dependency graph command group
  manifest/               # Manifest validate/deploy command group
  pack/                   # Pack operations command group
  playbook/               # Playbook download command group
  plugins/                # Plugin system and manager
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
- Each command group lives in its own subpackage under `src/xsoar_cli/` with a `commands.py` module
- Each command group has its own `README.md` documenting usage
- Commands are registered on the root Click group in `cli.py` via `cli.add_command()`
- The `@load_config` decorator (in `utilities.py`) handles config loading and injects `XSOARConfig` into `ctx.obj`
- Use `click.echo()` for user-facing output, `logging` for debug/file logs
- Commands that iterate over both `custom_packs` and `marketplace_packs` must use a `pack_type` variable (`"Custom"` / `"Marketplace"`) and include it in all log messages so the pack origin is always explicit in debug output
- Logging setup in `cli.py` is intentionally deferred to `main()`. Command and plugin registration happen at module level, but `_configure_logging()` must not be moved there -- see inline comments in `cli.py` for details
- Ruff noqa comments are used where rules are intentionally suppressed (e.g., `# noqa: PLR0913` for many parameters, `# noqa: ANN201` for fixture return types)
- Type hints are used throughout; `str | None` union syntax (Python 3.10+)
- Tests must not produce side effects on the real filesystem, such as writing to the log file. Tests invoke `cli()` directly via Click's `CliRunner`, bypassing `main()` and its logging setup
- Tests use `unittest.mock.patch` to mock external dependencies (`xsoar_client`, config file I/O)
- Test classes follow `class TestX` naming; test methods use `test_` prefix
- Fixtures are defined in `tests/conftest.py` and requested via `request.getfixturevalue()` for conditional use

## Configuration

- User config lives at `~/.config/xsoar-cli/config.json`
- Template generation: `xsoar-cli config create`
- Supports multiple named environments under `server_config`
- `default_environment` selects the active environment
- `custom_pack_authors` distinguishes custom packs from marketplace packs

## Workflow

- Prefer plain, natural language in comments and documentation. Avoid formal or academic wording where a simpler alternative exists
- Never start with code. Always plan changes properly before implementation. Ask for clarification in case of inconsistencies or missing information. Do not make assumptions. Confirm with user before generating code.
- In case of larger modifications, do implementation in logically grouped steps. Complex modifications may be broken down further.
- After completing each step, stop and wait for the user to review and confirm before proceeding to the next step.
- Each step should be small enough to be comfortably reviewed -- as a rule of thumb, no more than one or two files modified per step.

## Plugin System

- Plugins extend the CLI with custom Click commands
- `PluginManager` in `src/xsoar_cli/plugins/manager.py` handles discovery, loading, and registration
- Plugins are loaded after core commands; failures are warned but non-fatal
- Core command names are captured before plugin registration to prevent conflicts
