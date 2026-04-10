# Plugin System Refactor Plan

This document describes the planned refactor of the xsoar-cli plugin system to align it with the project's code conventions and design patterns.

## Breaking Changes

Removing the magic `XSOARPlugin` injection from `_load_module_from_file` means existing plugins that rely on `XSOARPlugin` being available without an import will fail with a `NameError`. Plugin authors must add an explicit import:

```python
from xsoar_cli.plugins import XSOARPlugin
```

This is the only breaking change. All other plugin behavior (discovery, loading, registration, conflict detection) remains the same once the plugins directory exists.

## Step 1: Fix `plugins/__init__.py`

Align the base class module with project conventions.

### Changes

- Add `from __future__ import annotations`.
- Replace `Optional[str]` with `str | None` and remove the `typing` import.
- Trim the module docstring and method docstrings to match the terse, direct style used elsewhere.
- Remove the Google-style `Returns:` block from `get_command`.

### Files modified

- `src/xsoar_cli/plugins/__init__.py`

## Step 2: Refactor `plugins/manager.py`

Remove side effects from the constructor and drop unnecessary magic.

### Changes

- Remove `self.plugins_dir.mkdir(parents=True, exist_ok=True)` from `__init__`. Directory creation moves to the new `plugins init` command (step 3).
- Remove the `sys.path` manipulation entirely. `spec_from_file_location` loads modules by full path and does not need `sys.path`. Inter-plugin imports are not supported (documented in step 6).
- Remove `XSOARPlugin` injection (`setattr(module, "XSOARPlugin", XSOARPlugin)`) from `_load_module_from_file`. Plugins must use an explicit import.
- Add a directory-existence guard at the top of `discover_plugins`: if `self.plugins_dir` does not exist, log a debug message and return an empty list.
- Add a `plugins_dir_exists` property that returns `bool`. Commands use this to emit "not initialized" errors.
- Trim docstrings to match project style.

### Implementation notes

`load_all_plugins` already calls `discover_plugins`, which will return an empty list when the directory is missing. No additional guard is needed in `load_all_plugins` itself.

The `import types` and `import sys` imports at the top of the file can be cleaned up: `types` is still needed for the return type of `_load_module_from_file`, but `sys` is only needed for `sys.modules` (used when registering loaded modules). The `sys.path` lines are the only ones being removed.

### Files modified

- `src/xsoar_cli/plugins/manager.py`

## Step 3: Add `plugins init` command, refactor existing plugin commands

Introduce explicit initialization and fix command-level conventions.

### New command: `plugins init`

Creates the plugins directory at `~/.local/xsoar-cli/plugins/` and drops a hello world example plugin into it. Behavior mirrors `config create`:

- If the directory already exists, prompt for confirmation before overwriting the example plugin.
- If the directory does not exist, create it (including parents).
- Write a single `hello.py` file that demonstrates the plugin contract.

Example plugin content:

```python
import click

from xsoar_cli.plugins import XSOARPlugin


class HelloPlugin(XSOARPlugin):
    @property
    def name(self) -> str:
        return "hello"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Example plugin. Modify or replace this file."

    def get_command(self) -> click.Command:
        @click.command()
        @click.option("--name", default="World", help="Name to greet")
        def hello(name: str) -> None:
            """Say hello."""
            click.echo(f"Hello, {name}!")

        return hello
```

### Refactor existing commands: `list`, `info`, `validate`

- Stop creating new `PluginManager()` instances. Access the module-level `plugin_manager` from `cli.py` via a lazy import (`from xsoar_cli.cli import plugin_manager`). This gives commands access to the actual loaded state rather than a freshly constructed manager.
- Before doing any work, check `plugin_manager.plugins_dir_exists`. If false, print a clear error: `Plugin directory not initialized. Run "xsoar-cli plugins init" to set up the plugins directory.` and exit with code 1.
- Add `-> None` return type annotations to all command functions.
- Defer the `PluginManager` import (for `init`, which still needs the class to know the default path) into the function body with the `# Lazy import for performance reasons` comment.
- Remove the top-level `from xsoar_cli.plugins.manager import PluginManager` import.
- Make `@click.pass_context` usage consistent: add it to commands that need `ctx` for exit codes, remove it from commands that don't use `ctx`.

### Implementation notes

The `validate` command currently imports `CORE_COMMANDS` from `xsoar_cli.cli` and reconstructs a temporary Click group to check conflicts. With access to the real `plugin_manager`, this can be simplified: the manager already tracks `command_conflicts` from the startup registration. `validate` can just read that list and re-run `load_plugin` + `get_command` validation per plugin.

The `info` command currently catches bare `Exception`. After the refactor it will access the already-loaded plugin from `plugin_manager.loaded_plugins` (or report it as failed if it's in `plugin_manager.failed_plugins`), removing the need for a try/except around loading.

### Files modified

- `src/xsoar_cli/commands/plugins/commands.py`

## Step 4: Update `cli.py`

Adjust startup plugin loading to handle missing directory gracefully.

### Changes

- In `_load_plugins`, the `PluginManager` constructor no longer creates the directory or modifies `sys.path`. If the directory doesn't exist, `discover_plugins` returns an empty list and `load_all_plugins` returns an empty dict. No plugins are registered. Log a debug message: `"Plugins directory not found, skipping plugin loading"`.
- Remove the `click.echo` warning for failed plugin registration in `_load_plugins`. Replace with `logger.warning` calls. (At this point in startup, logging is not yet configured for the file handler, but the message will be visible if `--debug` is used. This matches the existing pattern where module-level code avoids `click.echo` side effects.)
- In `XSOARCliGroup.resolve_command`, handle the case where no plugins directory exists. Currently it checks `plugin_manager.get_failed_plugins()` and reports them. After the refactor, if the directory doesn't exist, `failed_plugins` will be empty and the error falls through to the normal "No such command" message, which is correct.

### Implementation notes

The module-level `plugin_manager` remains a `PluginManager` instance regardless of whether the directory exists. Commands access it via `from xsoar_cli.cli import plugin_manager`. The `plugins_dir_exists` property on the manager is the canonical way to check initialization state.

### Files modified

- `src/xsoar_cli/cli.py`

## Step 5: Refactor tests

Align plugin tests with the project's test conventions.

### CLI tests (`tests/cli/test_plugins.py`)

- Introduce a `mock_plugin_env` composite fixture in `tests/cli/conftest.py`. It should yield a `SimpleNamespace` with attributes for the mocked `plugin_manager` and its sub-mocks (loaded plugins, failed plugins, plugin info, etc.).
- Replace `@patch` decorator stacking in `TestPluginCommands` with the new fixture.
- Add test cases for the new `plugins init` command (directory creation, example plugin written, already-exists prompt).
- Add test cases for the "not initialized" error path on `list`, `info`, and `validate`.
- Add a test verifying that `plugins init` followed by `plugins list` shows the hello plugin.

### Unit tests (`tests/unit/test_plugin_manager.py`)

- Replace `tempfile.TemporaryDirectory()` context managers with pytest's `tmp_path` fixture.
- Add a test for `plugins_dir_exists` returning `False` when the directory is missing.
- Add a test for `discover_plugins` returning an empty list when the directory is missing (without raising).
- Update `TestPluginConflicts.test_command_conflict_detection` to use an explicit `from xsoar_cli.plugins import XSOARPlugin` import in the plugin content string (matching the new requirement).
- Align test class and method naming with the conventions in other unit test files.

### Files modified

- `tests/cli/conftest.py` (add `mock_plugin_env` fixture)
- `tests/cli/test_plugins.py`
- `tests/unit/test_plugin_manager.py`

## Step 6: Update documentation

### `src/xsoar_cli/plugins/README.md`

- Add `xsoar-cli plugins init` as the first step in the Quick Start section.
- Update the example plugin to include `from xsoar_cli.plugins import XSOARPlugin`.
- Remove the sentence "The XSOARPlugin base class is automatically available in plugin files without any imports."
- Add a "Limitations" section stating that each plugin must be a single self-contained `.py` file and that imports between plugin files in the plugins directory are not supported.

### `src/xsoar_cli/commands/plugins/README.md`

- Add documentation for the `init` subcommand with syntax, description, and examples.

### `CHANGELOG.md`

Add entries under `[Unreleased]`:

- **Added**: `plugins init` command to create the plugins directory and generate an example plugin.
- **Changed**: Plugin commands (`list`, `info`, `validate`) now report a clear error when the plugins directory has not been initialized.
- **Changed**: Plugins must explicitly import `XSOARPlugin` (`from xsoar_cli.plugins import XSOARPlugin`). The base class is no longer injected automatically.
- **Removed**: Automatic creation of the plugins directory on CLI startup.