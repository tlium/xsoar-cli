# Refactoring Analysis

Codebase analysis identifying areas that could or should be refactored to improve
maintainability, consistency, and readiness for future expansion.

Items are grouped into tiers by effort and risk. Each item includes the
rationale, affected files, and a concrete description of what the fix looks like.

## Summary

| #   | Item | Type | Effort | Risk | Impact | Files | Reason | Status |
|-----|------|------|--------|------|--------|-------|--------|--------|
| 1.1 | `print()` in `Packs.get_outdated` | Consistency | Trivial | None | Low | `xsoar_client/packs.py` L108-109 | Breaks logging convention; domain layer should not produce user output | Done |
| 1.1a | Surface "pack not in artifacts repo" warning to user | Improvement | Low | Low | Medium | `commands/pack/commands.py` | Item 1.1 removed user-facing output; the CLI layer should re-surface this warning | Done |
| 1.2 | Missing return types in `Content` | Consistency | Trivial | None | Low | `xsoar_client/content.py` L83, L90, L97, L102 | Inconsistent with the rest of the codebase; hinders static analysis | Done |
| 1.3 | `list` builtin shadowed in content command | Bugfix | Trivial | None | Low | `commands/content/commands.py` L59 | Prevents use of `isinstance(..., list)` and invites subtle bugs | Done |
| 1.4 | "Uknown" typo in `Content` errors | Bugfix | Trivial | None | Low | `xsoar_client/content.py` L63, L73, L82 | Typo in user-facing error messages (three occurrences) | Done |
| 2.1 | Repeated `item_type` dispatch in `Content` | Refactor | Low | Low | Medium | `xsoar_client/content.py` L57-84 | Three methods share copy-pasted `if/else`; adding a content type means editing all three | |
| 2.2 | Broken temp file handling in `Packs.deploy` | Bugfix | Low | Low | Medium | `xsoar_client/packs.py` L92-93 | File never cleaned up; fails on Windows; two noqa comments suppressing real issues | Done |
| 2.3 | Redundant `skip_validation` logic in `Packs.deploy` | Cleanup | Low | Low | Low | `xsoar_client/packs.py` L86-91 | Both branches set `skip_validation` to the same value; `deploy` duplicates `deploy_zip` | Done |
| 2.4 | Eager init in S3 vs lazy init in Azure provider | Consistency | Low | Low | Medium | `artifact_providers/s3.py` L12-16, `artifact_providers/azure.py` L23-33 | Inconsistent patterns; S3 fails at construction even when provider is unused | Done |
| 3.1 | Domain classes lack a common base class | Refactor | Medium | Low | High | `xsoar_client/cases.py` L10, `integrations.py` L10, `rbac.py` L10, `content.py` L14, `packs.py` L18 | Five classes duplicate the same `__init__`; no shared hook for cross-cutting concerns | |
| 3.2 | Inconsistent `raise_for_status()` in domain classes | Robustness | Medium | Low | High | `xsoar_client/content.py` L20, `client.py` L56-78 | Some methods silently swallow HTTP errors, causing confusing downstream failures | |
| 3.3 | Repeated `--environment` / client setup boilerplate | Refactor | Medium | Medium | High | All `commands/*/commands.py` (see 3.3 detail below) | ~5 identical lines in every command; adding a new command requires copying boilerplate | |
| 3.4 | Manifest `commands.py` mixes CLI and business logic | Refactor | Medium | Low | Medium | `commands/manifest/commands.py` L25-113 (helpers), 447 lines total | 447-line file; business logic not independently testable without Click | |
| 3.5 | Error handling layer underutilized | Improvement | Medium | Medium | Medium | `error_handling/http.py` L8-22, `commands/case/commands.py` L55-57 | `HTTPErrorHandler` used in one command; all others handle errors ad-hoc | |
| 4.1 | `Packs.deploy` mixes download and upload | Refactor | Low | Low | Low | `xsoar_client/packs.py` L82-101 | Overlaps with `deploy_zip`; neither path is independently testable | |
| 4.2 | `validate_xsoar_connectivity` decorator complexity | Cleanup | Low | Low | Low | `utilities/validators.py` L19-68 | Accepts four input shapes; hard to predict behavior at a glance | Done |
| 4.3 | Test coverage gaps in command groups | Testing | High | Low | High | `tests/test_graph.py`, `test_manifest.py`, `test_pack.py`, `test_playbook.py` | Most command groups have only "exits 0" tests; prerequisite for safe refactoring | |

All file paths in the table are relative to `src/xsoar_cli/`.

---

## Tier 1: Trivial fixes (low effort, no risk)

These are isolated corrections that can each be done in a single commit with no
behavioral change.

### 1.1 `Packs.get_outdated` uses `print()` instead of `logging`

**File:** `src/xsoar_cli/xsoar_client/packs.py` lines 108-109

```python
except ValueError:
    msg = f"WARNING: custom pack {pack['id']} installed on XSOAR server, ..."
    print(msg, file=sys.stderr)
```

This is the only place in the entire codebase that uses `print()` for warnings.
Domain classes (the `xsoar_client` layer) should not produce user-facing output;
that responsibility belongs to the CLI layer. Using `print()` here also bypasses
the logging infrastructure entirely, so the warning never appears in the log file.

**Fix:** Replace with `logger.warning(...)`. If the CLI layer needs to surface
this to the user, it should catch the condition itself or inspect the return
value.

**Follow-up (1.1a):** The `print()` call was the only way this warning reached
the user. Now that it is logged instead, the CLI layer (`pack/commands.py` or
any other caller of `get_outdated()`) should detect skipped packs and display a
warning via `click.echo()`. This could be done by having `get_outdated()` return
the skipped pack IDs alongside the outdated list, or by accepting a callback.

---

### 1.2 Missing return type annotations in `Content`

**File:** `src/xsoar_cli/xsoar_client/content.py`

Four methods lack return type annotations:

| Method | Line | Suggested return type |
|--------|------|----------------------|
| `_list_playbooks` | L83 | `list[dict]` |
| `_list_scripts` | L90 | `list[dict]` |
| `_list_commands` | L97 | `list[dict]` |
| `list` | L102 | `list[dict] \| dict[str, list[dict]]` |

The rest of the codebase consistently uses type hints. These should follow suit.

**Fix:** Add explicit return types to all four methods.

---

### 1.3 Content command function shadows Python builtin `list`

**File:** `src/xsoar_cli/commands/content/commands.py` line 59

```python
def list(ctx, environment, content_type, detail, verbose):
```

The function name shadows the Python builtin `list`. The file itself
acknowledges the problem with a workaround comment at lines 71-72:

```python
# Note: isinstance(json_blob, list) cannot be used here because the function
# name "list" shadows the builtin.
```

**Fix:** Rename the function to `list_content` (or similar) and use
`@click.command("list")` to preserve the CLI-facing name. This removes the
need for the workaround comment and prevents future bugs from the shadowed
builtin.

---

### 1.4 Typo: "Uknown" in `Content` error messages

**File:** `src/xsoar_cli/xsoar_client/content.py`

The string `"Uknown"` appears in three `ValueError` messages:

| Line | Method |
|------|--------|
| L63 | `download_item` |
| L73 | `attach_item` |
| L82 | `detach_item` |

Should be `"Unknown"`.

**Fix:** Fix the typo in all three places (related to item 2.1 below, which
refactors the dispatch pattern these messages live in).

---

## Tier 2: Small refactors (low effort, low risk)

Each of these touches one or two files and can be done independently.

### 2.1 Repeated `item_type` dispatch in `Content`

**File:** `src/xsoar_cli/xsoar_client/content.py` lines 57-84

Three methods (`download_item` at L57, `attach_item` at L67, `detach_item` at
L77) share the exact same structure:

```python
def download_item(self, item_type: str, item_id: str) -> bytes:
    if item_type == "playbook":
        endpoint = f"/{item_type}/{item_id}/yaml"
        response = self.client.make_request(endpoint=endpoint, method="GET")
    else:
        msg = 'Uknown item_type selected for download. Must be one of ["playbook"]'
        raise ValueError(msg)
    response.raise_for_status()
    return response.content
```

The `if item_type == "playbook" ... else raise ValueError` block is copy-pasted
three times. When a new content type is added (e.g. `"script"`), all three
methods need to be updated in lockstep, which is error-prone.

**Fix options (pick one):**

- **Validation helper:** Extract a `_validate_item_type(item_type)` method that
  raises `ValueError` for unsupported types. Each method calls it once and then
  proceeds with endpoint construction without the `if/else`.

- **Endpoint map:** A class-level dict mapping `(action, item_type)` to endpoint
  templates. Each method does a lookup and raises if the key is missing. Adding
  a new content type becomes a single dict entry.

Either approach also fixes the typo from item 1.4.

---

### 2.2 Temporary file handling in `Packs.deploy`

**File:** `src/xsoar_cli/xsoar_client/packs.py` lines 92-93

```python
tmp = tempfile.NamedTemporaryFile()  # noqa: SIM115
with open(tmp.name, "wb") as f:     # noqa: PTH123
    f.write(filedata)
```

Problems:

1. `NamedTemporaryFile` is created but never used as a context manager. The file
   object is not explicitly closed or cleaned up.
2. The file is opened a second time via `open(tmp.name, "wb")`, which on Windows
   would fail because `NamedTemporaryFile` keeps the file open by default.
3. Two `noqa` comments suppress linter warnings that are flagging real issues.

**Fix:**

```python
with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
    tmp.write(filedata)
    tmp.flush()
    tmp_path = tmp.name

try:
    self.client.demisto_py_instance.upload_content_packs(tmp_path, **params)
except ApiException as ex:
    ...
finally:
    Path(tmp_path).unlink(missing_ok=True)
```

This also eliminates the need for the two `noqa` comments.

---

### 2.3 `Packs.deploy` duplicates `skip_validation`/`skip_verify` logic

**File:** `src/xsoar_cli/xsoar_client/packs.py` lines 86-91

```python
if custom:
    params["skip_validation"] = "false"
    params["skip_verify"] = "true"
else:
    params["skip_validation"] = "false"
    params["skip_verify"] = "false"
```

`skip_validation` is `"false"` in both branches. Only `skip_verify` differs.
This can be simplified to:

```python
params = {
    "skip_validation": "false",
    "skip_verify": "true" if custom else "false",
}
```

The existing `deploy_zip` method (L79-85) also accepts `skip_validation`/
`skip_verify` as booleans and converts them to strings internally. The two
methods overlap in responsibility. Consider having `deploy` call `deploy_zip`
after downloading, rather than reimplementing the upload step.

---

### 2.4 S3 provider eager init vs Azure lazy init

**Files:**
- `src/xsoar_cli/xsoar_client/artifact_providers/s3.py` lines 12-16
- `src/xsoar_cli/xsoar_client/artifact_providers/azure.py` lines 23-33

`S3ArtifactProvider.__init__` eagerly creates the boto3 session and S3 resource:

```python
# s3.py L12-16
def __init__(self, *, bucket_name, verify_ssl=True):
    self.bucket_name = bucket_name
    self.verify_ssl = verify_ssl
    self.session = boto3.session.Session()
    self.s3 = self.session.resource("s3")
```

`AzureArtifactProvider` uses lazy `@property` accessors that defer creation
until first use (L23-33).

This inconsistency means:

- S3 provider creation fails immediately if AWS credentials are missing, even if
  the current command does not need the artifact provider.
- Azure defers the failure to the point of actual use, which is the better
  behavior.

**Fix:** Make S3 follow the same lazy pattern as Azure. Store `bucket_name` and
`verify_ssl` in `__init__`, create the session/resource in a `@property`.

---

## Tier 3: Medium refactors (medium effort, low-to-medium risk)

These touch multiple files or introduce new abstractions. Each should be done as
an isolated step.

### 3.1 Domain classes lack a common base class

**Files** (all under `src/xsoar_cli/xsoar_client/`):

| Class | File | `__init__` line |
|-------|------|-----------------|
| `Cases` | `cases.py` | L10 |
| `Content` | `content.py` | L14 |
| `Integrations` | `integrations.py` | L10 |
| `Packs` | `packs.py` | L18 |
| `Rbac` | `rbac.py` | L10 |

All five domain classes follow the same pattern:

```python
class Cases:
    def __init__(self, client: Client) -> None:
        self.client = client
```

A `BaseDomain` class would:

- Eliminate the duplicated `__init__` in each class.
- Provide a natural place to add shared behavior later (automatic
  `raise_for_status()`, response logging, retry logic, request tracing).
- Make it explicit that these classes share a contract.

**Sketch:**

```python
class BaseDomain:
    def __init__(self, client: Client) -> None:
        self.client = client

class Cases(BaseDomain):
    def get(self, case_id: int) -> dict:
        ...
```

`Packs` has a slightly different `__init__` (extra `custom_pack_authors`
parameter). It would call `super().__init__(client)` and then set its own
attributes.

The base class could live in a new file `src/xsoar_cli/xsoar_client/base.py`
or in the existing `__init__.py`.

---

### 3.2 Inconsistent HTTP response error handling in domain classes

**Files:** All domain classes under `src/xsoar_cli/xsoar_client/`,
`client.py` L56-78 (`make_request`)

Some methods call `response.raise_for_status()`, some don't:

| Method | File | Line | Calls `raise_for_status()`? |
|--------|------|------|-----------------------------|
| `Cases.get()` | `cases.py` | L13 | Yes |
| `Cases.create()` | `cases.py` | L20 | Yes |
| `Content.get_bundle()` | `content.py` | L17 | **No** |
| `Content.get_detached()` | `content.py` | L38 | Yes |
| `Packs.get_installed()` | `packs.py` | L24 | Yes |
| `Rbac.get_users()` | `rbac.py` | L14 | Yes |

If `Content.get_bundle()` receives a non-2xx response, it silently tries to
untar the error body and fails with a confusing `tarfile` error rather than a
clear HTTP error.

**Fix options:**

1. **Audit and add:** Go through every method, add `raise_for_status()` where
   missing. Simple but requires ongoing discipline.

2. **Default-safe `make_request`:** Add a `raise_for_status=True` parameter to
   `Client.make_request()` (L56) so the default is safe. Methods that need the
   raw response can opt out. This ties in well with a `BaseDomain` class
   (item 3.1) that could wrap requests uniformly.

Option 2 is preferable because it makes the safe path the default and shifts
the burden to the rare cases that need raw responses.

---

### 3.3 Repeated `--environment` option and client setup boilerplate

**Files:** Every `commands.py` under `src/xsoar_cli/commands/`

Almost every command repeats this pattern:

```python
@click.option("--environment", default=None, help="Default environment set in config file.")
@click.pass_context
@load_config
@validate_xsoar_connectivity()
def some_command(ctx, environment, ...):
    config = get_xsoar_config(ctx)
    xsoar_client: Client = config.get_client(environment)
    active_env = environment or config.default_environment
    ...
```

The `--environment` option appears at the following locations:

| File | Lines | Commands |
|------|-------|----------|
| `commands/case/commands.py` | L36, L132 | `get`, `create` |
| `commands/pack/commands.py` | L23, L47 | `delete`, `get_outdated` |
| `commands/rbac/commands.py` | L24, L34, L44 | `getroles`, `getusers`, `getusergroups` |
| `commands/manifest/commands.py` | L122, L153, L229, L300, L356 | `generate`, `update`, `validate`, `diff`, `deploy` |
| `commands/content/commands.py` | L23, L52 | `get_detached`, `list` |
| `commands/integration/commands.py` | L24 | `dump` |
| `commands/playbook/commands.py` | L26 | `download` |
| `commands/graph/commands.py` | L30 | All graph subcommands (via `_common_graph_options`) |

That is 16 occurrences of the same option definition, plus 15+ repetitions of
the `get_xsoar_config` / `get_client` / `active_env` setup block.

**Fix:** Create a shared decorator (e.g., `@xsoar_command`) that:

1. Adds `--environment` as a Click option.
2. Applies `@load_config`.
3. Resolves `config`, `xsoar_client`, and `active_env` and passes them to the
   decorated function (either via context or as injected parameters).

Optionally, this decorator could accept flags to also apply
`@validate_xsoar_connectivity()` and/or `@validate_artifacts_provider`.

This would reduce each command to its unique logic and make adding new commands
less error-prone. The decorator should live in `utilities/` alongside the
existing `load_config`.

Note that `graph/commands.py` already partially solves this with
`_common_graph_options` (L22-34). A project-wide decorator would subsume that
pattern.

**Risk note:** This touches many files but each change is mechanical. It should
be done in one pass to keep the pattern consistent, with the test suite
validating each command still works.

---

### 3.4 Extract manifest business logic from `commands.py`

**File:** `src/xsoar_cli/commands/manifest/commands.py` (447 lines)

This is the largest command file by a wide margin. It contains both CLI wiring
(Click decorators, `click.echo()` calls, `ctx.exit()`) and business logic
(manifest file I/O, version comparison loops, pack availability checking).

The following helpers could move to `src/xsoar_cli/utilities/manifest.py`:

| Function | Current location | Lines |
|----------|-----------------|-------|
| `load_manifest` | `manifest/commands.py` | L25-34 |
| `write_manifest` | `manifest/commands.py` | L37-43 |
| `_pack_found_locally` | `manifest/commands.py` | L46-59 |
| `_validate_manifest_keys` | `manifest/commands.py` | L62-73 |
| `_check_pack_availability` | `manifest/commands.py` | L76-113 |

`utilities/manifest.py` already holds some manifest-related logic
(`find_installed_packs_not_in_manifest`, `find_packs_in_manifest_not_installed`,
`find_version_mismatch`). The split is partially done. Completing it would:

- Keep `commands.py` focused on Click wiring and user-facing output.
- Make the business logic independently testable without invoking Click.
- Reduce the file to a more reviewable size.

`_check_pack_availability` currently calls `click.echo()` for progress dots and
raises `click.ClickException`. To move it cleanly, it should either accept a
progress callback or return results that the command layer formats. Similarly,
`load_manifest` currently raises `click.ClickException`; it should raise a plain
exception that the command layer catches and converts.

---

### 3.5 Error handling layer is underutilized

**Files:**
- `src/xsoar_cli/error_handling/http.py` L8-22 (`HTTPErrorHandler` class and `_messages` dict)
- `src/xsoar_cli/error_handling/connection.py` L9-56 (`ConnectionErrorHandler`)
- All command modules

The `error_handling/` package defines two well-structured handler classes:

- `HTTPErrorHandler` (L8): maps HTTP status codes to user-friendly messages,
  with per-context customization via `_messages` (L17-22).
- `ConnectionErrorHandler`: extracts actionable messages from exception chains.

However, `HTTPErrorHandler` is only used in `commands/case/commands.py` at
L55-57:

```python
except HTTPError as ex:
    handler = HTTPErrorHandler()
    click.echo(f"Error: {handler.get_message(ex, context='case')}")
```

All other commands that handle HTTP errors do so ad-hoc:

- `commands/manifest/commands.py` `deploy` (L397-415): catches `RuntimeError`
  wrapping `ApiException`, manually parses the JSON error body.
- `commands/pack/commands.py`, `commands/rbac/commands.py`,
  `commands/integration/commands.py`: let exceptions from `raise_for_status()`
  propagate uncaught (Click prints the traceback).

`ConnectionErrorHandler` is only used in `utilities/validators.py` L59.

**Fix:** Expand the `HTTPErrorHandler._messages` dict with entries for contexts
used by other commands (`"pack"`, `"manifest"`, `"integration"`, etc.) and
apply the handler consistently. This could also be tied into the common
decorator from item 3.3, where a top-level exception handler wraps every
command invocation.

This is a gradual process. No need to do it all at once, but each new command
should use the error handling layer from the start.

---

## Tier 4: Larger structural improvements (higher effort)

These are not urgent but would pay off as the codebase grows.

### 4.1 `Packs.deploy` mixes download and upload responsibilities

**File:** `src/xsoar_cli/xsoar_client/packs.py` lines 82-101

The `deploy` method:

1. Downloads the pack (via `self.download()`, called at L84).
2. Determines `skip_validation`/`skip_verify` params (L86-91).
3. Writes data to a temp file (L92-93).
4. Uploads it (via `demisto_py_instance.upload_content_packs()`, L96).

Meanwhile, `deploy_zip` (L79-85) exists as a separate method that handles step 4
from a user-provided file path. The two methods overlap but don't share code.

**Fix:** Have `deploy` download the pack, write it to a temp file, and then
call `deploy_zip` for the upload step. This avoids duplicating the
`upload_content_packs` call and its error handling, and makes both paths
independently testable.

---

### 4.2 `validate_xsoar_connectivity` decorator complexity

**File:** `src/xsoar_cli/utilities/validators.py` lines 19-68

The `validate_xsoar_connectivity` decorator accepts environments as `None`,
`str`, `list[str]`, or `Callable` (union type at L20-21):

```python
def validate_xsoar_connectivity(
    environments: str | list[str] | Callable[[click.Context], str | list[str]] | None = None,
) -> Callable:
```

This flexibility is powerful but makes the decorator's behavior hard to predict
at a glance. The `Callable` variant is used only once, in
`commands/case/commands.py` for the `clone` command:

```python
@validate_xsoar_connectivity(lambda ctx: [ctx.params["source"], ctx.params["dest"]])
```

If the common decorator from item 3.3 is introduced, the multi-environment
validation could be handled more explicitly (e.g., the decorator accepts a list
of parameter names to resolve environments from). This would simplify the type
signature and make the intent clearer.

Not urgent, but worth revisiting if item 3.3 is implemented.

---

### 4.3 Test coverage gaps

**Files:**

| Test file | Commands covered | Depth |
|-----------|-----------------|-------|
| `tests/test_config.py` | `config validate` | Thorough (7 test classes, edge cases) |
| `tests/test_case.py` | `case get`, `case create`, `case clone` | Good (success + error paths) |
| `tests/test_error_handling.py` | Error handler classes | Good (parametrized) |
| `tests/test_plugins.py` | Plugin system | Good (unit + integration) |
| `tests/test_base.py` | Root CLI group | Minimal (3 parametrized cases) |
| `tests/test_graph.py` | `graph` | Minimal (single "exits 0" test) |
| `tests/test_manifest.py` | `manifest` | Minimal (single "exits 0" test) |
| `tests/test_pack.py` | `pack` | Minimal (single "exits 0" test) |
| `tests/test_playbook.py` | `playbook` | Minimal (single "exits 0" test) |

The `test_config.py` and `test_case.py` files demonstrate how to properly test
commands with mocked clients and config. The same patterns should be applied to
the other command groups.

This is not a refactoring item per se, but test coverage is a prerequisite for
safely performing the refactors listed above. Expanding tests for `manifest`,
`pack`, and `playbook` commands before refactoring those modules reduces the
risk of regressions.

---

## Suggested execution order

The items below are ordered to minimize risk and maximize incremental value.
Each step should be a separate commit or PR.

1. **Tier 1 quick wins** (items 1.1 through 1.4). These are independent and can
   all be done in a single batch.
2. **Tier 2 small refactors** (items 2.1 through 2.4). Each is independent and
   can be done in any order.
3. **Item 3.1** (domain base class). Introduces the abstraction that item 3.2
   depends on.
4. **Item 3.2** (consistent `raise_for_status()`). Builds on the base class.
5. **Item 3.4** (extract manifest business logic). Independent of items 3.1-3.2.
6. **Item 3.3** (common `--environment` decorator). Largest single change. Should
   come after the simpler refactors are settled and test coverage is solid.
7. **Item 3.5** (standardize error handling). Gradual, can be done command by
   command alongside other work.
8. **Tier 4 items** as opportunities arise.