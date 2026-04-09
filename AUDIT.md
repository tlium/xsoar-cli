# Codebase Consistency Audit

This document catalogs inconsistencies in design patterns, conventions, and code style across the
xsoar-cli codebase. The goal is to make the codebase as uniform as possible, improve readability,
and lower the barrier for new contributors.

Findings are grouped by severity and category. Each finding includes the affected files and line
numbers so it can be addressed independently.

---

## Table of Contents

- [1. Bugs and Bug Risks](#1-bugs-and-bug-risks)
- [2. Design Inconsistencies](#2-design-inconsistencies)
- [3. Structural and Convention Inconsistencies](#3-structural-and-convention-inconsistencies)
- [4. Test Suite Inconsistencies](#4-test-suite-inconsistencies)
- [5. Documentation Drift](#5-documentation-drift)
- [Priority Recommendation](#priority-recommendation)

---

## 1. Bugs and Bug Risks

### 1a. Missing `@click.pass_context` on `integration load`

**File:** `src/xsoar_cli/commands/integration/commands.py` (line 48-52)

The function declares `ctx: click.Context` as a parameter but has no `@click.pass_context`
decorator. Click will interpret `ctx` as a positional argument, not the context object. Invoking
this command will fail at runtime with a `TypeError`.

```python
@click.command()
def load(ctx: click.Context) -> None:
    """Load integration instance configuration into XSOAR from a JSON file. Not yet implemented."""
    logger.debug("integration loadconfig command not implemented")
    click.echo("Command not implemented")
```

**Fix:** Either add `@click.pass_context`, or remove the `ctx` parameter since the command is a
no-op stub.

---

### 1b. `PluginManager.__init__` creates real directories at import time

**File:** `src/xsoar_cli/plugins/manager.py` (line 31-36)

When `cli.py` is imported (including during tests), `_load_plugins()` instantiates
`PluginManager`, which unconditionally creates `~/.local/xsoar-cli/plugins/` on the real
filesystem and mutates `sys.path`:

```python
# Ensure plugins directory exists
self.plugins_dir.mkdir(parents=True, exist_ok=True)

# Add plugins directory to Python path if not already there
plugins_dir_str = str(self.plugins_dir)
if plugins_dir_str not in sys.path:
    sys.path.insert(0, plugins_dir_str)
```

Every CLI test that imports `cli` triggers this real filesystem side-effect. The `sys.path`
mutation is permanent and global, and inserting at position 0 means plugin files take precedence
over all other paths.

**Fix:** Defer directory creation to first use (e.g., `discover_plugins`), or make the path
configurable so tests can use a temp directory without side-effects.

---

## 2. Design Inconsistencies

### 2a. Validator decorator calling conventions differ

**File:** `src/xsoar_cli/utilities/validators.py` (line 16, 43)

`validate_xsoar_connectivity` is a factory (called with parentheses), while
`validate_artifacts_provider` is a direct decorator (no parentheses). Both do the same kind of
thing (validate a precondition before a command runs) but require different syntax to apply:

```python
@validate_artifacts_provider
@validate_xsoar_connectivity()
```

`validate_xsoar_connectivity` takes no parameters, so the factory pattern adds no value.

**Fix:** Make both decorators use the same pattern (preferably the simpler direct decorator form).

---

### 2b. `case` command group uses manual error handling instead of `@validate_xsoar_connectivity()`

**File:** `src/xsoar_cli/commands/case/commands.py`

Every other command group that connects to XSOAR uses the `@validate_xsoar_connectivity()`
decorator. The `case` group (`get`, `clone`, `create`) handles errors manually, importing
`ConnectionErrorHandler` and `HTTPErrorHandler` directly and catching exceptions inline. The
`case clone` command has its own inline connectivity check loop (line 82-90), while `case get`
catches `HTTPError` manually (line 51-54).

**Fix:** Refactor to use `@validate_xsoar_connectivity()` for consistency with all other command
groups.

---

### 2c. `CORE_COMMANDS` creates a fragile circular import path

**Files:** `src/xsoar_cli/cli.py` (line 115), `src/xsoar_cli/commands/plugins/commands.py`
(line 156)

`cli.py` exports `CORE_COMMANDS` at module level. `commands/plugins/commands.py` then imports it
back with a deferred `from xsoar_cli.cli import CORE_COMMANDS`. This creates a circular dependency
path (`cli` -> `commands.plugins.commands` -> `cli`) that works only because the import is inside
a function body.

**Fix:** Pass `CORE_COMMANDS` via Click's context object or a shared registry module that both
files can import without circular dependencies.

---

### 2d. Inconsistent error handling in artifact providers

**Files:** `src/xsoar_cli/xsoar_client/artifact_providers/s3.py` (line 34-38),
`src/xsoar_cli/xsoar_client/artifact_providers/azure.py` (line 40-43)

S3 `is_available()` catches a broad `Exception`, silently swallowing authentication errors,
network errors, and other unexpected failures, returning `False` ("pack not available") when the
real problem may be something else entirely. Azure correctly catches only `ResourceNotFoundError`:

S3:
```python
try:
    self.s3.Object(self.bucket_name, key_name).load()
    return True
except Exception:
    return False
```

Azure:
```python
try:
    blob_client.get_blob_properties()
    return True
except ResourceNotFoundError:
    return False
```

**Fix:** Narrow the S3 exception to `botocore.exceptions.ClientError` and check the error code
for 404.

---

### 2e. `print()` instead of `click.echo()` in config show

**File:** `src/xsoar_cli/commands/config/commands.py` (line 70-71)

This is the only `print()` call across all command modules. The convention is `click.echo()` for
all user-facing output. The `ctx.exit()` on the next line is also unnecessary since the function
returns naturally. No other command does this for a successful path.

```python
print(json.dumps(config, indent=4))
ctx.exit()
```

**Fix:** Replace `print()` with `click.echo()` and remove the `ctx.exit()` call.

---

### 2f. Builtin `all` shadowed in `integration dump`

**File:** `src/xsoar_cli/commands/integration/commands.py` (line 24, 29)

The `--all` option uses `all` as the Python parameter name, shadowing the builtin. The option is
also missing help text. Compare with `config validate`, which correctly renames the parameter to
`all_environments`:

```python
@click.option("--all", is_flag=True, default=False)
...
def dump(ctx: click.Context, environment: str | None, name: str | None, all: bool) -> None:
```

**Fix:** Rename the parameter (e.g., `all_instances`) using Click's two-argument option syntax:
`@click.option("--all", "all_instances", ...)`. Add help text.

---

### 2g. Dead code in `PluginManager.discover_plugins()`

**File:** `src/xsoar_cli/plugins/manager.py` (line 43-45)

The `exists()` check is dead code because the constructor already calls
`mkdir(parents=True, exist_ok=True)`. The only way it could fail is if the directory were deleted
between `__init__` and `discover_plugins()`.

```python
if not self.plugins_dir.exists():
    logger.info("Plugins directory does not exist: %s", self.plugins_dir)
    return plugin_names
```

**Fix:** Remove the guard, or if the constructor is changed to defer directory creation (see 1b),
keep it as a legitimate check.

---

### 2h. Redundant re-import in `PluginManager._load_module_from_file`

**File:** `src/xsoar_cli/plugins/manager.py` (line 73-74)

`XSOARPlugin` is already imported at module level (line 11) but is re-imported inside the method
body:

```python
from . import XSOARPlugin

setattr(module, "XSOARPlugin", XSOARPlugin)
```

**Fix:** Remove the deferred import and use the module-level `XSOARPlugin` directly.

---

## 3. Structural and Convention Inconsistencies

### 3a. `from __future__ import annotations` missing in 13 source modules

The convention is to use `from __future__ import annotations` together with a `TYPE_CHECKING`
block so type hints remain clean and unquoted. Only 3 of 10 command modules have it.

**Missing in:**

| File | Notes |
|------|-------|
| `src/xsoar_cli/cli.py` | Entry point |
| `src/xsoar_cli/log.py` | Logging setup |
| `src/xsoar_cli/utilities/config_file.py` | Config I/O |
| `src/xsoar_cli/utilities/validators.py` | Validator decorators |
| `src/xsoar_cli/plugins/__init__.py` | Plugin ABC |
| `src/xsoar_cli/plugins/manager.py` | Plugin manager |
| `src/xsoar_cli/commands/case/commands.py` | Case commands |
| `src/xsoar_cli/commands/config/commands.py` | Config commands |
| `src/xsoar_cli/commands/content/commands.py` | Content commands |
| `src/xsoar_cli/commands/integration/commands.py` | Integration commands |
| `src/xsoar_cli/commands/pack/commands.py` | Pack commands |
| `src/xsoar_cli/commands/rbac/commands.py` | RBAC commands |
| `src/xsoar_cli/commands/plugins/commands.py` | Plugin commands |

**Fix:** Add `from __future__ import annotations` to all source modules in a single sweep.

---

### 3b. `Optional[str]` instead of `str | None` in plugins

**File:** `src/xsoar_cli/plugins/__init__.py` (line 33)

The only source file under `src/xsoar_cli/` that uses the old `typing.Optional` syntax. The
project convention is `str | None` (Python 3.10+).

```python
@property
def description(self) -> Optional[str]:
    """Return an optional description of the plugin."""
```

**Fix:** Replace `Optional[str]` with `str | None` and remove the `Optional` import.

---

### 3c. Click group help text declared inconsistently

Two different patterns are used across the 10 command groups:

| Pattern | Modules |
|---------|---------|
| `help=` in decorator, body is `pass` | case, completions, config, graph, plugins |
| Docstring on function | content, integration, manifest, pack, rbac |

**Fix:** Pick one pattern and apply it across all groups. The `help=` in decorator with `pass`
body is the most common.

---

### 3d. `TYPE_CHECKING` block placement inconsistencies

**Files:**
- `src/xsoar_cli/commands/config/commands.py` (line 7-9): `TYPE_CHECKING` block placed before
  the local imports. All other modules place it after.
- `src/xsoar_cli/commands/case/commands.py` (line 26): `TYPE_CHECKING` block placed after a
  function definition (`parse_string_to_dict`), far from the other imports.

**Fix:** Place `TYPE_CHECKING` blocks consistently after all runtime imports, following PEP 8 /
isort ordering.

---

### 3e. Missing `-> None` return type annotations

**Files:**
- `src/xsoar_cli/commands/plugins/commands.py`: All 4 functions (`plugins`, `list_plugins`,
  `info`, `validate`)
- `src/xsoar_cli/configuration.py` (line 64, 108): `EnvironmentConfig.__init__` and
  `XSOARConfig.__init__`

All other modules consistently annotate `-> None` on void functions.

**Fix:** Add `-> None` to all affected functions.

---

### 3f. Bare `list` return types instead of `list[dict]`

**Files:**
- `src/xsoar_cli/xsoar_client/integrations.py` (line 14): `get_instances() -> list`
- `src/xsoar_cli/xsoar_client/rbac.py` (line 14, 20, 26): `get_users() -> list`,
  `get_roles() -> list`, `get_user_groups() -> list`

Compare with `Packs` and `Content`, which use the more specific `list[dict]`.

**Fix:** Change return types to `list[dict]`.

---

### 3g. Inconsistent JSON output formatting

**Trailing newline:** `integration dump` and all `rbac` commands append `+ "\n"` to
`json.dumps()` output. `click.echo()` already appends a newline, so this produces a double blank
line. Other commands (`case get`, `content get_detached`, `content list`) do not append `"\n"`.

**`sort_keys`:** `integration dump` and `rbac` commands use `sort_keys=True`. Other JSON output
commands do not.

**Files:**
- `src/xsoar_cli/commands/integration/commands.py` (line 45)
- `src/xsoar_cli/commands/rbac/commands.py` (line 32, 41, 50)

**Fix:** Pick a consistent JSON output style (with or without `sort_keys`, without trailing
newline) and apply it everywhere.

---

### 3h. Inconsistent decorator ordering on `graph` commands

**File:** `src/xsoar_cli/commands/graph/commands.py`

`generate` (line 75-80) has `@_common_graph_options` before `@click.command()`, while `export`
(line 96-102) has `@click.command()` first. The ordering affects how Click processes the options.

**Fix:** Use the same decorator ordering on both commands.

---

### 3i. Missing docstrings in domain classes and artifact providers

**File:** `src/xsoar_cli/xsoar_client/content.py`
- `_list_playbooks` (line 116)
- `_list_scripts` (line 123)
- `_list_commands` (line 130)
- `list` (line 136)

**File:** `src/xsoar_cli/xsoar_client/artifact_providers/azure.py`
- `test_connection` (line 33)
- `is_available` (line 37)
- `download` (line 45)
- `get_latest_version` (line 50)

All other domain class methods and S3 provider methods have docstrings.

**Fix:** Add docstrings to all affected methods.

---

### 3j. Missing return type annotations on artifact provider lazy properties

**Files:**
- `src/xsoar_cli/xsoar_client/artifact_providers/s3.py` (line 20-22): `s3` property missing
  return type
- `src/xsoar_cli/xsoar_client/artifact_providers/azure.py` (line 28-30): `container_client`
  property missing return type

Their sibling properties (`session`, `service`) have return types.

**Fix:** Add return type annotations.

---

### 3k. Inconsistent logging in domain classes

**Files with a logger:** `content.py`, `packs.py`

**Files without a logger:** `cases.py`, `integrations.py`, `rbac.py`

Operations like creating a case, fetching integrations, or fetching RBAC data produce no debug
trace.

**Fix:** Add `logger = logging.getLogger(__name__)` to all domain classes and add appropriate
debug logging.

---

### 3l. Formal docstring style in plugin ABC

**File:** `src/xsoar_cli/plugins/__init__.py` (line 38-45)

Uses a formal multi-line docstring style with explicit `Returns:` sections, unlike the rest of
the codebase which uses single-line or short multi-line docstrings without section headers:

```python
def get_command(self) -> click.Command:
    """
    Return the Click command or command group that this plugin provides.

    Returns:
        click.Command: The command to be registered with the CLI
    """
```

Compare with the rest of the codebase:

```python
def get(self, case_id: int) -> dict:
    """Fetches a case by ID."""
```

**Fix:** Simplify to single-line docstrings consistent with the rest of the codebase.

---

### 3m. `assert` for type check in `log.py`

**File:** `src/xsoar_cli/log.py` (line 44)

Uses `assert isinstance(handler, RotatingFileHandler)` to guard idempotent behavior. `assert`
statements are stripped in optimized mode (`python -O`), which would silently return the wrong
handler type.

**Fix:** Replace with an explicit `if not isinstance(...)` check and raise `TypeError`.

---

## 4. Test Suite Inconsistencies

### 4a. `test_content_domain.py` creates `mock_client` inline in all test methods

**File:** `tests/unit/test_content_domain.py`

Every other domain test file (`test_cases.py`, `test_packs.py`, `test_rbac.py`,
`test_integrations.py`) uses the `mock_client` fixture from `tests/unit/conftest.py`.
`test_content_domain.py` creates `mock_client = MagicMock()` inline in all 53 test methods.

**Fix:** Refactor all test methods to use the `mock_client` fixture.

---

### 4b. `test_plugins.py` uses `@patch` decorator stacking instead of composite fixtures

**File:** `tests/cli/test_plugins.py`

The convention says CLI tests should use composite mock fixtures (`mock_xsoar_env`,
`mock_content_env`, `mock_case_env`) instead of stacking `@patch` decorators. `test_plugins.py`
stacks `@patch` decorators and uses `mock_config_file` directly.

Additionally, it inconsistently patches at the import site in some tests (line 28:
`xsoar_cli.commands.plugins.commands.PluginManager`) and at the source in others (line 56:
`xsoar_cli.plugins.manager.PluginManager`) within the same class.

**Fix:** Create a composite mock fixture for plugin tests (or use `mock_config_file` consistently
with a single patching approach). Patch at the source consistently.

---

### 4c. Duplicated `_mock_response` helper in 4 unit test files

**Files:**
- `tests/unit/test_cases.py` (line 47)
- `tests/unit/test_integrations.py` (line 38)
- `tests/unit/test_packs.py` (line 63)
- `tests/unit/test_rbac.py` (line 59)

All four define nearly identical `_mock_response` helpers:

```python
def _mock_response(json_data: dict, *, status_code: int = 200) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data
    response.raise_for_status.return_value = None
    return response
```

**Fix:** Extract into a shared fixture or helper in `tests/unit/conftest.py`.

---

### 4d. Duplicated `_make_http_error` helper

**File:** `tests/unit/test_error_handling.py` (line 69)

Defines its own `_make_http_error` function that exactly duplicates the `make_http_error` factory
fixture from `tests/conftest.py`.

**Fix:** Use the existing `make_http_error` fixture instead.

---

### 4e. Missing `from __future__ import annotations` in test files

**Files:**
- `tests/unit/test_content_domain.py`
- `tests/unit/test_content_handlers.py`
- `tests/unit/test_error_handling.py`
- `tests/unit/test_plugin_manager.py`

**Fix:** Add `from __future__ import annotations` to all four files.

---

### 4f. `test_plugin_manager.py` multiple deviations

**File:** `tests/unit/test_plugin_manager.py`

- All 9 test methods are missing `-> None` return type annotations (unique to this file).
- Uses `tempfile.TemporaryDirectory()` instead of pytest's `tmp_path` fixture. Every other test
  file that needs a temporary directory uses `tmp_path`.
- Missing module docstring.

**Fix:** Add return type annotations, switch to `tmp_path`, add a module docstring.

---

### 4g. Module-level handler instances in `test_error_handling.py`

**File:** `tests/unit/test_error_handling.py` (line 67-68)

Instantiates handlers at module level:

```python
connection_handler = ConnectionErrorHandler()
http_handler = HTTPErrorHandler()
```

No other test file uses module-level instances. All other tests create instances inside test
methods or use fixtures.

**Fix:** Move instantiation into a fixture or into individual test methods.

---

### 4h. `test_base.py` missing type hints and imports

**File:** `tests/cli/test_base.py` (line 14)

The `invoke` parameter is not type-hinted as `InvokeHelper`, and the file lacks the
`TYPE_CHECKING` import block that all other CLI test files include. Also missing a module
docstring.

**Fix:** Add the `TYPE_CHECKING` block, type-hint `invoke` as `InvokeHelper`, add a module
docstring.

---

### 4i. Missing class docstring

**File:** `tests/cli/test_content.py` (line 168)

`TestContentDownloadMissingType` has no class docstring while all other classes in the same file
have one.

**Fix:** Add a class docstring.

---

## 5. Documentation Drift

### 5a. CLAUDE.md references files that do not exist

**File:** `CLAUDE.md` (line 127-128)

```
uv pip install -r requirements.txt
uv pip install -r requirements_dev.txt
```

Neither `requirements.txt` nor `requirements_dev.txt` exist. Dependencies are managed via
`pyproject.toml` and `uv.lock`.

**Fix:** Remove or replace the stale install commands.

---

### 5b. `commands/completions/` not listed in CLAUDE.md project layout

**File:** `CLAUDE.md`

The `completions` command group is imported, registered in `cli.py`, and has its own `README.md`,
but is entirely absent from the project layout section in CLAUDE.md.

**Fix:** Add `completions/` to the project layout.

---

### 5c. Empty `description` in `pyproject.toml`

**File:** `pyproject.toml` (line 8)

```toml
description = ''
```

The package has no summary. This shows up empty on PyPI and in `pip show`.

**Fix:** Add a meaningful description.

---

## Priority Recommendation

Tackle these in the following order:

1. **Bugs** (1a-1b): Fix the `integration load` decorator, address the `PluginManager`
   side-effect.

2. **Design inconsistencies** (2a-2h): Normalize validator decorators, bring `case` commands in
   line with the error-handling pattern, resolve the circular import, fix the builtin shadowing,
   use `click.echo()` consistently, remove dead code.

3. **Sweep: `from __future__ import annotations`** (3a): A single focused pass across all 13
   source modules.

4. **Sweep: Type hints and return annotations** (3b, 3e, 3f, 3j): Normalize `Optional` to
   `str | None`, add missing `-> None`, use `list[dict]` consistently.

5. **Sweep: Docstrings and structural patterns** (3c, 3d, 3g, 3h, 3i, 3k, 3l, 3m):
   Normalize Click group declarations, `TYPE_CHECKING` placement, JSON output formatting,
   decorator ordering, add missing docstrings and loggers.

6. **Test cleanup** (4a-4i): Extract shared helpers, normalize fixture usage, add missing
   annotations and docstrings.

7. **Documentation** (5a-5c): Update CLAUDE.md, fill in pyproject description.