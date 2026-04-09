# Codebase Consistency Audit

This document catalogs inconsistencies in design patterns, conventions, and code style across the
xsoar-cli codebase. The goal is to make the codebase as uniform as possible, improve readability,
and lower the barrier for new contributors.

Findings are grouped by severity and category. Each finding includes the affected files and line
numbers so it can be addressed independently.

---

## Table of Contents

- [1. Design Inconsistencies](#1-design-inconsistencies)
- [2. Structural and Convention Inconsistencies](#2-structural-and-convention-inconsistencies)
- [3. Test Suite Inconsistencies](#3-test-suite-inconsistencies)
- [Priority Recommendation](#priority-recommendation)

---

## 1. Design Inconsistencies

### 1a. Inconsistent error handling in artifact providers

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

## 2. Structural and Convention Inconsistencies

### 2a. Bare `list` return types instead of `list[dict]`

**Files:**
- `src/xsoar_cli/xsoar_client/integrations.py` (line 14): `get_instances() -> list`
- `src/xsoar_cli/xsoar_client/rbac.py` (line 14, 20, 26): `get_users() -> list`,
  `get_roles() -> list`, `get_user_groups() -> list`

Compare with `Packs` and `Content`, which use the more specific `list[dict]`.

**Fix:** Change return types to `list[dict]`.

---

### 2b. Inconsistent decorator ordering on `graph` commands

**File:** `src/xsoar_cli/commands/graph/commands.py`

`generate` (line 75-80) has `@_common_graph_options` before `@click.command()`, while `export`
(line 96-102) has `@click.command()` first. The ordering affects how Click processes the options.

**Fix:** Use the same decorator ordering on both commands.

---

### 2c. Missing return type annotations on artifact provider lazy properties

**Files:**
- `src/xsoar_cli/xsoar_client/artifact_providers/s3.py` (line 20-22): `s3` property missing
  return type
- `src/xsoar_cli/xsoar_client/artifact_providers/azure.py` (line 28-30): `container_client`
  property missing return type

Their sibling properties (`session`, `service`) have return types.

**Fix:** Add return type annotations.

---

### 2d. Inconsistent logging in domain classes

**Files with a logger:** `content.py`, `packs.py`

**Files without a logger:** `cases.py`, `integrations.py`, `rbac.py`

Operations like creating a case, fetching integrations, or fetching RBAC data produce no debug
trace.

**Fix:** Add `logger = logging.getLogger(__name__)` to all domain classes and add appropriate
debug logging.

---

### 2e. `assert` for type check in `log.py`

**File:** `src/xsoar_cli/log.py` (line 44)

Uses `assert isinstance(handler, RotatingFileHandler)` to guard idempotent behavior. `assert`
statements are stripped in optimized mode (`python -O`), which would silently return the wrong
handler type.

**Fix:** Replace with an explicit `if not isinstance(...)` check and raise `TypeError`.

---

## 3. Test Suite Inconsistencies

### 3a. `test_base.py` missing type hints and imports

**File:** `tests/cli/test_base.py` (line 14)

The `invoke` parameter is not type-hinted as `InvokeHelper`, and the file lacks the
`TYPE_CHECKING` import block that all other CLI test files include. Also missing a module
docstring.

**Fix:** Add the `TYPE_CHECKING` block, type-hint `invoke` as `InvokeHelper`, add a module
docstring.

---

### 3b. Missing class docstring

**File:** `tests/cli/test_content.py` (line 168)

`TestContentDownloadMissingType` has no class docstring while all other classes in the same file
have one.

**Fix:** Add a class docstring.

---

## Priority Recommendation

Tackle these in the following order:

1. **Design inconsistency** (1a): Fix the S3 exception handling.

2. **Sweep: Type hints and return annotations** (2a, 2c): Use `list[dict]` consistently, add
   missing return types on artifact provider properties.

3. **Sweep: Structural patterns** (2b, 2d, 2e): Normalize decorator ordering, add missing
   loggers, replace `assert` with explicit type check.

4. **Test cleanup** (3a-3b): Add missing type hints, imports, and docstrings.