# Test Coverage Improvement Plan

Current coverage: **62% (970 missed statements out of 2981)**. Target: **85%+**.

## Summary

| # | Area | File(s) | Current | Est. Recoverable Stmts | Priority | Depends On |
|---|------|---------|---------|------------------------|----------|------------|
| 1 | Test data restructuring | `tests/test_data/` | -- | -- | Pre-req | -- |
| 2 | Shared test fixture | `tests/unit/conftest.py` | -- | -- | Pre-req | 1 |
| 3 | Content filter utilities | `utilities/content.py` | 11% | ~50 | High | -- |
| 4 | Manifest comparison helpers | `utilities/manifest.py` | 18% | ~22 | High | 1 |
| 5 | Version check utilities | `utilities/version_check.py` | 22% | ~25 | Medium | -- |
| 6 | Cases domain class | `xsoar_client/cases.py` | 47% | ~8 | Medium | 1, 2 |
| 7 | RBAC domain class | `xsoar_client/rbac.py` | 40% | ~12 | Medium | 1, 2 |
| 8 | Integrations domain class | `xsoar_client/integrations.py` | 58% | ~5 | Medium | 1, 2 |
| 9 | Content domain class (remaining) | `xsoar_client/content.py` | 42% | ~35 | High | 1, 2 |
| 10 | Packs domain class | `xsoar_client/packs.py` | 21% | ~65 | High | 1, 2 |
| 11 | Client core | `xsoar_client/client.py` | 62% | ~16 | Medium | 2 |
| 12 | S3 artifact provider | `artifact_providers/s3.py` | 40% | ~20 | Medium | 2 |
| 13 | Azure artifact provider | `artifact_providers/azure.py` | 0% | ~49 | Medium | 2 |
| 14 | Base artifact provider | `artifact_providers/base.py` | 71% | ~5 | Low | -- |
| 15 | Validators | `utilities/validators.py` | 50% | ~25 | Low | 2 |
| 16 | Config file utilities | `utilities/config_file.py` | 68% | ~11 | Low | -- |

Estimated total recoverable: **~350 statements**, which would bring coverage to roughly **84%**.

---

## Phase 1: Infrastructure

### 1. Restructure test data directory

Reorganize `tests/test_data/` so fixtures are grouped by API domain instead of sitting in a flat directory. Existing files move into subdirectories; nothing is deleted.

**Target layout:**

```
tests/test_data/
  manifest/                              # existing manifest + server response files
    manifest_base.json
    manifest_invalid.json
    manifest_with_pack_not_on_server.json
    server_base_response.json
    server_base_response_missing_one_pack.json
    server_base_response_with_updates.json
    server_base_response_with_updates_and_one_extra.json
  packs/                                 # NEW
    installed.json                       # GET /contentpacks/metadata/installed
    installed_expired.json               # GET /contentpacks/installed-expired
  cases/                                 # NEW
    get.json                             # GET /incident/load/{id}
    create.json                          # POST /incident
  rbac/                                  # NEW
    users.json                           # GET /users
    roles.json                           # GET /roles
    user_groups.json                     # GET /user_groups
  integrations/                          # NEW
    instances.json                       # GET /integration/instances
  content/                               # NEW
    playbook_search.json                 # POST /playbook/search
    automation_search.json               # POST /automation/search
    user_commands.json                   # GET /user/commands
  Packs/                                 # unchanged (pack directory structures for graph tests)
  Download/                              # unchanged
```

**Tasks:**

- [ ] Create subdirectories under `tests/test_data/`
- [ ] Move existing manifest and server response JSON files into `test_data/manifest/`
- [ ] Update all imports/paths in existing tests that reference the moved files
- [ ] Create realistic JSON fixtures for each new subdirectory (see per-domain sections below for field requirements)
- [ ] Verify all existing tests still pass after the move

---

### 2. Add shared test data loader fixture

Add a `load_test_data` fixture to `tests/unit/conftest.py` that standardizes how unit tests load JSON fixtures.

```python
@pytest.fixture
def load_test_data():
    """Load a JSON fixture from the test_data directory by relative path."""
    def _load(relative_path: str) -> dict | list:
        path = Path(__file__).parent.parent / "test_data" / relative_path
        return json.loads(path.read_text())
    return _load
```

**Tasks:**

- [ ] Add `load_test_data` fixture to `tests/unit/conftest.py`
- [ ] Verify fixture works with an existing test as a smoke check

---

## Phase 2: Pure Function Tests (no mocking needed)

### 3. Content filter utilities (`utilities/content.py`, 11% coverage)

Every function in this module is a pure data transformation. Tests only need realistic input dicts. These tests can reuse the JSON fixtures created for the content domain class (see [Appendix A.5](#a5-contentplaybook_searchjson), [A.6](#a6-contentautomation_searchjson), [A.7](#a7-contentuser_commandsjson)), or define inline dicts since the functions are small and self-contained.

**Functions to cover:**

- `summarize_scripts(scripts)` -- returns `[{id, comment}]`
- `filter_scripts(scripts)` -- returns `[{id, comment, arguments}]`, handles `None` arguments
- `summarize_playbooks(playbooks)` -- returns `[{id, name}]`
- `filter_playbooks(playbooks)` -- returns `[{id, name, inputs, outputs}]`, handles `None` inputs/outputs
- `_group_commands_by_brand(instances)` -- deduplicates by brand
- `summarize_commands(instances)` -- returns `[{brand, commands}]`
- `filter_commands(instances)` -- returns `[{brand, commands}]` with arguments/outputs per command
- `filter_content(raw, detail=False)` -- dispatch function, both `detail=True` and `detail=False`

**Input field requirements (all accessed via `.get()` with defaults, so missing fields are safe):**

Scripts:
- `id` (str), `comment` (str) -- used by both summarize and filter
- `arguments` (list[dict] | None) -- filter only. Each argument: `name`, `required`, `deprecated`, `description`

Playbooks:
- `id` (str), `name` (str) -- used by both summarize and filter
- `inputs` (list[dict] | None) -- filter only. Each input: `key`, `description`
- `outputs` (list[dict] | None) -- filter only. Each output: `contextPath`, `description`, `type`

Commands (integration instances):
- `brand` (str) -- deduplication key in `_group_commands_by_brand`
- `commands` (list[dict] | None) -- each command: `name`, `description`, `arguments` (same shape as scripts), `outputs` (same shape as playbook outputs)

**Test file:** `tests/unit/test_content_filters.py`

**Tasks:**

- [ ] Create `test_content_filters.py`
- [ ] Test each summarize function with typical input
- [ ] Test each filter function with typical input
- [ ] Test edge cases: empty lists, `None` values for optional fields (arguments, inputs, outputs)
- [ ] Test `_group_commands_by_brand` deduplication (multiple instances of the same brand)
- [ ] Test `filter_content` dispatch for each content type and both detail modes
- [ ] Test `filter_content` with `"all"` key combination

---

### 4. Manifest comparison helpers (`utilities/manifest.py`, 18% coverage)

Pure functions that compare installed packs against manifest definitions. The existing JSON fixtures in `test_data/manifest/` already provide realistic data for these tests.

**Functions to cover:**

- `_all_manifest_packs(manifest_data)` -- flattens custom_packs + marketplace_packs
- `find_installed_packs_not_in_manifest(installed, manifest)` -- packs on server but not in manifest
- `find_packs_in_manifest_not_installed(installed, manifest)` -- packs in manifest but not on server
- `find_version_mismatch(installed, manifest)` -- version differences

**Test file:** `tests/unit/test_manifest_utils.py`

**Tasks:**

- [ ] Create `test_manifest_utils.py`
- [ ] Test `_all_manifest_packs` with both sections populated, one empty, both empty
- [ ] Test `find_installed_packs_not_in_manifest` using `server_base_response_with_updates_and_one_extra.json` + `manifest_base.json`
- [ ] Test `find_packs_in_manifest_not_installed` using `server_base_response_missing_one_pack.json` + `manifest_base.json`
- [ ] Test `find_version_mismatch` using `server_base_response_with_updates.json` + `manifest_base.json`
- [ ] Test all-match scenario (no differences)
- [ ] Test empty inputs (no installed packs, empty manifest)

---

## Phase 3: Domain Class Unit Tests

All domain classes follow the same pattern: thin wrappers around `client.make_request()`. Tests mock the client, configure `make_request` return values with the JSON fixtures, and assert the domain method returns the expected result.

### 5. Version check utilities (`utilities/version_check.py`, 22% coverage)

**Functions to cover:**

- `is_pypi_install(package_name)` -- checks `direct_url.json` presence
- `get_installed_version(package_name)` -- reads installed version via `importlib.metadata`
- `get_latest_version(package_name)` -- fetches from PyPI Simple API
- `check_for_update(config_data)` -- orchestrator, returns update message or None

**Test file:** `tests/unit/test_version_check.py`

**Tasks:**

- [ ] Create `test_version_check.py`
- [ ] Test `is_pypi_install`: mock `importlib.metadata.distribution` to return/not return `direct_url.json`
- [ ] Test `get_installed_version`: mock distribution to return a known version string
- [ ] Test `get_latest_version`: mock `requests.get` with a realistic PyPI Simple API JSON response
- [ ] Test `check_for_update` with config that disables version check (`skip_version_check: True`)
- [ ] Test `check_for_update` with config that enables version check, non-PyPI install (should skip)
- [ ] Test `check_for_update` with update available (latest > installed)
- [ ] Test `check_for_update` with no update available (latest == installed)
- [ ] Test `check_for_update` with `None` config

---

### 6. Cases domain class (`xsoar_client/cases.py`, 47% coverage)

**Methods to cover:**

- `Cases.get(case_id)` -- `GET /incident/load/{id}`, calls `raise_for_status()`, returns `.json()`
- `Cases.create(data)` -- `POST /incident` (v6) or `/xsoar/public/v1/incident` (v8)

**JSON fixtures needed:** `test_data/cases/get.json`, `test_data/cases/create.json` (see [Appendix A.1](#a1-casesgetjson) and [A.2](#a2-casescreatejson) for full structures)

The `get.json` fixture must include all fields that `clone` pops with bare `.pop(key)` (no default), meaning a missing field causes `KeyError`. The full set:

| Field | Access | Used by |
|---|---|---|
| `id` | `results.pop("id")` | `clone` (removed before creating clone) |
| `version` | `results.pop("version")` | `clone` |
| `created` | `results.pop("created")` | `clone` |
| `modified` | `results.pop("modified")` | `clone` |
| `cacheVersn` | `results.pop("cacheVersn")` | `clone` |
| `sizeInBytes` | `results.pop("sizeInBytes")` | `clone` |
| `attachment` | `results.pop("attachment")` | `clone` |
| `labels` | `results.pop("labels")` | `clone` (popped, then merged back into cloned case) |
| `owner` | `results.pop("owner")` | `clone` |
| `name` | passthrough | `get` (dumped as JSON) |
| `details` | passthrough | `get` (dumped as JSON) |
| `dbotMirrorId` | `results.pop(...)` | `clone` |
| `dbotMirrorInstance` | `results.pop(...)` | `clone` |
| `dbotMirrorDirection` | `results.pop(...)` | `clone` |
| `dbotDirtyFields` | `results.pop(...)` | `clone` |
| `dbotCurrentDirtyFields` | `results.pop(...)` | `clone` |
| `dbotMirrorTags` | `results.pop(...)` | `clone` |
| `dbotMirrorLastSync` | `results.pop(...)` | `clone` |

Note: The existing `make_case_response` fixture in root `conftest.py` is missing `version`, `cacheVersn`, `sizeInBytes`, `attachment`, `labels`, and `owner`. These must be present in the JSON fixture for clone tests to work.

The `create.json` fixture only needs `id` (accessed as `case_data["id"]` in both `clone` and `create` commands). Include `name` and `created` for realism.

**Test file:** `tests/unit/test_cases.py`

**Tasks:**

- [ ] Create `test_data/cases/get.json` with realistic case response
- [ ] Create `test_data/cases/create.json` with realistic create response
- [ ] Create `test_cases.py`
- [ ] Test `Cases.get()` happy path (mock `make_request` returning fixture data)
- [ ] Test `Cases.get()` with HTTP error (mock `raise_for_status` raising `HTTPError`)
- [ ] Test `Cases.create()` happy path for v6 endpoint
- [ ] Test `Cases.create()` happy path for v8 endpoint (verify correct endpoint used)
- [ ] Test `Cases.create()` with HTTP error

---

### 7. RBAC domain class (`xsoar_client/rbac.py`, 40% coverage)

**Methods to cover:**

- `Rbac.get_users()` -- `GET /users` (v6) or `/rbac/get_users` (v8)
- `Rbac.get_roles()` -- `GET /roles` (v6) or `/rbac/get_roles` (v8)
- `Rbac.get_user_groups()` -- `GET /user_groups` (v6) or `/rbac/get_user_groups` (v8)

**JSON fixtures needed:** `test_data/rbac/users.json`, `test_data/rbac/roles.json`, `test_data/rbac/user_groups.json` (see [Appendix A.3](#a3-rbacusersjson))

All three RBAC commands are opaque pass-throughs: `response.json()` is piped directly to `json.dumps()` for display. The code never accesses individual fields. The fixtures exist purely to provide realistic data that round-trips through the domain class. Include 2-3 items per list with representative fields from the real API (e.g. `id`, `username`, `email`, `roles` for users).

**Test file:** `tests/unit/test_rbac.py`

**Tasks:**

- [ ] Create `test_data/rbac/users.json`
- [ ] Create `test_data/rbac/roles.json`
- [ ] Create `test_data/rbac/user_groups.json`
- [ ] Create `test_rbac.py`
- [ ] Test each method: happy path with v6 endpoint
- [ ] Test each method: happy path with v8 endpoint (verify correct endpoint used via `resolve_endpoint`)
- [ ] Test each method: HTTP error propagation

---

### 8. Integrations domain class (`xsoar_client/integrations.py`, 58% coverage)

**Methods to cover:**

- `Integrations.get_instances()` -- `GET /integration/instances`
- `Integrations.load_config()` -- currently raises `NotImplementedError`

**JSON fixture needed:** `test_data/integrations/instances.json` (see [Appendix A.4](#a4-integrationsinstancesjson))

The only field explicitly accessed is `name` (bare dict lookup `i["name"]` in the `dump` command's single-instance path). All other fields are passed through to `json.dumps()`. The fixture should include `name` plus representative fields (`id`, `brand`, `enabled`) for realism. Include 2-3 instances, with at least two sharing the same `brand` to support deduplication testing if needed later.

**Test file:** `tests/unit/test_integrations.py`

**Tasks:**

- [ ] Create `test_data/integrations/instances.json`
- [ ] Create `test_integrations.py`
- [ ] Test `get_instances()` happy path
- [ ] Test `get_instances()` HTTP error
- [ ] Test `load_config()` raises `NotImplementedError`

---

### 9. Content domain class, remaining methods (`xsoar_client/content.py`, 42% coverage)

`download_playbook`, `_resolve_playbook_id`, and `download_layout` are already covered in `test_content_domain.py`. The remaining methods need tests.

**Methods to cover:**

- `Content.get_bundle()` -- downloads and extracts a tarball
- `Content.get_detached(content_type)` -- searches for detached content (`"scripts"` or `"playbooks"`)
- `Content.download_item(item_type, item_id)` -- downloads by type and ID
- `Content.attach_item(item_type, item_id)` -- attaches content to server-managed version
- `Content.detach_item(item_type, item_id)` -- detaches content
- `Content._list_playbooks()` -- searches all non-hidden, non-deprecated playbooks
- `Content._list_scripts()` -- searches all scripts
- `Content._list_commands()` -- fetches user commands
- `Content.list(item_type)` -- dispatcher for list methods

**JSON fixtures needed:** `test_data/content/playbook_search.json`, `test_data/content/automation_search.json`, `test_data/content/user_commands.json` (see [Appendix A.5](#a5-contentplaybook_searchjson), [A.6](#a6-contentautomation_searchjson), [A.7](#a7-contentuser_commandsjson))

These fixtures are also reused by the content filter tests (section 3). The search responses are wrapped in an envelope (`{"playbooks": [...]}` and `{"scripts": [...]}`), while `/user/commands` returns a bare list.

**Test file:** `tests/unit/test_content_domain.py` (extend existing file)

**Tasks:**

- [ ] Create `test_data/content/playbook_search.json` (include 2-3 playbooks with `id`, `name`, `inputs`, `outputs`, `tasks`)
- [ ] Create `test_data/content/automation_search.json` (include 2-3 scripts with `id`, `name`, `comment`, `arguments`)
- [ ] Create `test_data/content/user_commands.json` (include 2-3 integration instances with `brand`, `commands`)
- [ ] Add tests for `get_detached("scripts")` and `get_detached("playbooks")`
- [ ] Add test for `get_detached` with invalid content_type (should raise `ValueError`)
- [ ] Add tests for `download_item("playbook", id)` happy path and error propagation
- [ ] Add test for `download_item` with unsupported item_type (should raise `ValueError`)
- [ ] Add tests for `attach_item` with `"playbook"` and `"layout"` types
- [ ] Add test for `attach_item` with unsupported item_type (should raise `ValueError`)
- [ ] Add tests for `detach_item` with `"playbook"` and `"layout"` types
- [ ] Add test for `detach_item` with unsupported item_type (should raise `ValueError`)
- [ ] Add tests for `_list_playbooks()`, `_list_scripts()`, `_list_commands()` using JSON fixtures
- [ ] Add tests for `list("playbooks")`, `list("scripts")`, `list("commands")`, `list("all")`
- [ ] Add test for `list` with invalid item_type (should raise `ValueError`)
- [ ] Add test for `get_bundle()` using a small in-memory tarball fixture

---

### 10. Packs domain class (`xsoar_client/packs.py`, 21% coverage)

Largest single gap in the domain layer. Several methods interact with the artifact provider, marketplace HTTP calls, and `demisto_client`.

**Methods to cover:**

- `Packs.get_installed()` -- fetches and caches installed packs
- `Packs.get_installed_expired()` -- fetches and caches expired packs
- `Packs.is_installed(pack_id, pack_version)` -- checks if a pack (optionally at a version) is installed
- `Packs.is_available(pack_id, version, custom)` -- checks marketplace or artifact provider
- `Packs.download(pack_id, pack_version, custom)` -- downloads from marketplace or artifact provider
- `Packs.deploy_zip(filepath)` -- uploads a zip via `demisto_client`
- `Packs.deploy(pack_id, pack_version, custom)` -- download + upload orchestration
- `Packs.get_outdated()` -- compares installed-expired against artifact provider/changelog
- `Packs.get_latest_custom_version(pack_id)` -- delegates to artifact provider
- `Packs.delete()` -- raises `NotImplementedError`

**JSON fixtures needed:** `test_data/packs/installed.json`, `test_data/packs/installed_expired.json` (see [Appendix A.8](#a8-packsinstalledjson) and [A.9](#a9-packsinstalled_expiredjson))

`installed.json` -- list of installed packs. Fields accessed by the code:

| Field | Access style | Used by |
|---|---|---|
| `id` | `item["id"]` (bare lookup) | `is_installed()`, `manifest generate/validate/deploy/diff`, `manifest.py` helpers |
| `currentVersion` | `item["currentVersion"]` (bare lookup) | `is_installed()`, `manifest generate/validate/deploy/diff`, `manifest.py` helpers |

Include 3-4 packs. At least one should have `author` matching a custom pack author string (e.g. `"MyOrg"`) for downstream manifest tests.

`installed_expired.json` -- list of expired packs. Fields accessed by `get_outdated()`:

| Field | Access style | Required for |
|---|---|---|
| `author` | `pack["author"]` (bare lookup) | Classifying custom vs. marketplace |
| `id` | `pack["id"]` (bare lookup) | Artifact provider lookup, log messages, output dict |
| `currentVersion` | `pack["currentVersion"]` (bare lookup) | Version comparison, output dict |
| `updateAvailable` | `pack["updateAvailable"]` (bare lookup) | Gate for marketplace packs (bool) |
| `changelog` | `pack["changelog"]` (bare lookup) | Keys are semver strings, parsed with `version.parse` to find latest |

Include at least 3 packs: one custom pack with a newer version available in the artifact repo, one marketplace pack with `updateAvailable: true` and a `changelog` dict, and one marketplace pack with `updateAvailable: false`.

**Test file:** `tests/unit/test_packs.py`

**Tasks:**

- [ ] Create `test_data/packs/installed.json`
- [ ] Create `test_data/packs/installed_expired.json`
- [ ] Create `test_packs.py`
- [ ] Test `get_installed()` happy path, verify caching (second call should not make a request)
- [ ] Test `get_installed_expired()` happy path, verify caching
- [ ] Test `is_installed(pack_id)` with existing and non-existing pack
- [ ] Test `is_installed(pack_id, pack_version)` with matching and non-matching version
- [ ] Test `is_available` for marketplace pack (mock `requests.head`)
- [ ] Test `is_available` for custom pack (mock artifact provider)
- [ ] Test `is_available` for custom pack with no artifact provider configured (should raise `RuntimeError`)
- [ ] Test `download` for marketplace pack (mock `requests.get`)
- [ ] Test `download` for custom pack (mock artifact provider)
- [ ] Test `download` for custom pack with no artifact provider (should raise `RuntimeError`)
- [ ] Test `deploy_zip` happy path (mock `demisto_py_instance.upload_content_packs`)
- [ ] Test `deploy` happy path for marketplace pack
- [ ] Test `deploy` happy path for custom pack
- [ ] Test `deploy` with upload failure (`ApiException`)
- [ ] Test `get_outdated` with upstream packs that have updates
- [ ] Test `get_outdated` with custom packs that have updates (mock artifact provider `get_latest_version`)
- [ ] Test `get_outdated` with custom pack not found in artifact repo (should appear in `skipped`)
- [ ] Test `get_outdated` with no artifact provider for custom packs (should raise `RuntimeError`)
- [ ] Test `get_latest_custom_version` happy path
- [ ] Test `get_latest_custom_version` with no artifact provider (should raise `RuntimeError`)
- [ ] Test `delete` raises `NotImplementedError`

---

### 11. Client core (`xsoar_client/client.py`, 62% coverage)

**Methods to cover:**

- `Client.make_request()` -- builds headers, dispatches `requests.request()`
- `Client.test_connectivity()` -- calls `make_request` on workers/status endpoint
- `Client.resolve_endpoint(v6, v8)` -- returns endpoint based on `server_version`

**Test file:** `tests/unit/test_client.py`

Note: `Client.__init__` calls `demisto_client.configure()`, which must be mocked.

**Tasks:**

- [ ] Create `test_client.py`
- [ ] Test `resolve_endpoint` returns v6 endpoint when `server_version <= 6`
- [ ] Test `resolve_endpoint` returns v8 endpoint when `server_version > 6`
- [ ] Test `make_request` builds correct headers (including `x-xdr-auth-id` for v8)
- [ ] Test `make_request` without `xsiam_auth_id` (header should be absent)
- [ ] Test `test_connectivity` success (mock `make_request` returning 200)
- [ ] Test `test_connectivity` failure (mock `make_request` raising, should wrap in `ConnectionError`)

---

## Phase 4: Artifact Providers

### 12. S3 artifact provider (`artifact_providers/s3.py`, 40% coverage)

All methods interact with `boto3`. Mock `boto3.session.Session` and the S3 resource/client objects.

**Test file:** `tests/unit/test_artifact_s3.py`

**Tasks:**

- [ ] Create `test_artifact_s3.py`
- [ ] Test `test_connection()` happy path (mock `bucket.load()`)
- [ ] Test `test_connection()` failure (mock `bucket.load()` raising)
- [ ] Test `is_available()` when object exists (mock `Object.load()` succeeds)
- [ ] Test `is_available()` when object does not exist (mock `Object.load()` raises)
- [ ] Test `download()` returns bytes from S3 object body
- [ ] Test `get_latest_version()` parses version prefixes from `list_objects_v2` response
- [ ] Test lazy initialization of `session` and `s3` properties

---

### 13. Azure artifact provider (`artifact_providers/azure.py`, 0% coverage)

All methods interact with `azure.storage.blob`. Mock `BlobServiceClient` and container/blob clients.

**Test file:** `tests/unit/test_artifact_azure.py`

**Tasks:**

- [ ] Create `test_artifact_azure.py`
- [ ] Test `service` property with explicit `access_token`
- [ ] Test `service` property with `AZURE_STORAGE_SAS_TOKEN` env var (mock `os.environ`)
- [ ] Test `service` property with no token available (should raise `RuntimeError`)
- [ ] Test `test_connection()` happy path
- [ ] Test `is_available()` when blob exists
- [ ] Test `is_available()` when blob does not exist (`ResourceNotFoundError`)
- [ ] Test `download()` returns bytes from blob stream
- [ ] Test `get_latest_version()` parses version from blob name listing

---

### 14. Base artifact provider (`artifact_providers/base.py`, 71% coverage)

Only the concrete `get_pack_path` method needs testing. The abstract methods are covered when subclass tests exercise them.

**Test file:** `tests/unit/test_artifact_base.py` (or inline in one of the provider test files)

**Tasks:**

- [ ] Test `get_pack_path()` returns expected path format

---

## Phase 5: Lower Priority

### 15. Validators (`utilities/validators.py`, 50% coverage)

The two decorators (`validate_xsoar_connectivity`, `validate_artifacts_provider`) are partially exercised by CLI tests. Dedicated unit tests would cover the remaining branches.

**Test file:** `tests/unit/test_validators.py`

**Tasks:**

- [ ] Create `test_validators.py`
- [ ] Test `validate_xsoar_connectivity` passes through on successful connectivity
- [ ] Test `validate_xsoar_connectivity` prints error and exits on `ConnectionError`
- [ ] Test `validate_xsoar_connectivity` resolves environment from `ctx.params` and falls back to default
- [ ] Test `validate_artifacts_provider` skips validation when no provider is configured
- [ ] Test `validate_artifacts_provider` passes through on successful connection
- [ ] Test `validate_artifacts_provider` prints error and exits on connection failure

---

### 16. Config file utilities (`utilities/config_file.py`, 68% coverage)

Partially covered through CLI tests. The `load_config` decorator has some branches not yet tested.

**Test file:** `tests/unit/test_config_file.py`

**Tasks:**

- [ ] Create `test_config_file.py`
- [ ] Test `load_config` with missing config file (should prompt user)
- [ ] Test `load_config` with invalid environment parameter (should print error and exit)
- [ ] Test `load_config` reuses pre-parsed `XSOARConfig` from `ctx.obj`
- [ ] Test `read_config_file` when file does not exist (returns `None`)
- [ ] Test `get_config_file_path` returns expected path

---

## Notes

- All domain class tests follow the same pattern: instantiate with a `MagicMock` client, configure `make_request` to return a mock response loaded from a JSON fixture, call the method, assert the result.
- Tests must not touch the real filesystem (config files, log files). Use `tmp_path` where file I/O is needed.
- Patch deferred imports at their source module, not the importing module (per project conventions).
- After completing each phase, run `uv run pytest --cov=src/xsoar_cli --cov-report=term-missing` to measure progress.

---

## Appendix: Fixture Specifications

Realistic JSON structures for every fixture file. Based on tracing which fields the production code actually accesses (bare `dict["key"]` vs. `.get("key", default)`). Fields marked "passthrough" are not accessed by code but should be present for realism since the CLI dumps them as JSON.

### A.1 `cases/get.json`

Response from `GET /incident/load/{id}`. A flat dict (not wrapped in `total`/`data`).

```json
{
    "id": "12345",
    "version": 3,
    "name": "Phishing Investigation",
    "type": "Phishing",
    "status": 1,
    "severity": 2,
    "owner": "admin",
    "created": "2024-06-15T08:30:00Z",
    "modified": "2024-06-15T09:45:00Z",
    "details": "Suspicious email reported by user",
    "labels": [
        {"type": "Email", "value": "phish@example.com"},
        {"type": "Reporter", "value": "jdoe"}
    ],
    "attachment": null,
    "cacheVersn": 2,
    "sizeInBytes": 4096,
    "dbotMirrorId": "",
    "dbotMirrorInstance": "",
    "dbotMirrorDirection": "",
    "dbotDirtyFields": [],
    "dbotCurrentDirtyFields": [],
    "dbotMirrorTags": [],
    "dbotMirrorLastSync": ""
}
```

All fields above are popped with bare `.pop(key)` in the `clone` command. Missing any of them causes `KeyError`.

### A.2 `cases/create.json`

Response from `POST /incident` (v6) or `POST /xsoar/public/v1/incident` (v8). Same shape as a GET response, but only `id` is accessed by the code.

```json
{
    "id": "12346",
    "name": "Phishing Investigation",
    "created": "2024-06-15T10:00:00Z",
    "modified": "2024-06-15T10:00:00Z",
    "details": "Suspicious email reported by user",
    "status": 1,
    "severity": 2,
    "owner": "admin",
    "version": 1,
    "labels": [],
    "attachment": null,
    "cacheVersn": 0,
    "sizeInBytes": 0,
    "dbotMirrorId": "",
    "dbotMirrorInstance": "",
    "dbotMirrorDirection": "",
    "dbotDirtyFields": [],
    "dbotCurrentDirtyFields": [],
    "dbotMirrorTags": [],
    "dbotMirrorLastSync": ""
}
```

### A.3 `rbac/users.json`

Response from `GET /users`. The CLI dumps this verbatim, so no fields are explicitly accessed. Include realistic fields for round-trip testing.

```json
[
    {
        "id": "admin",
        "username": "admin",
        "name": "Admin User",
        "email": "admin@example.com",
        "roles": {"demisto": ["Administrator"]},
        "phone": "",
        "accUser": false
    },
    {
        "id": "analyst1",
        "username": "analyst1",
        "name": "Jane Doe",
        "email": "jane.doe@example.com",
        "roles": {"demisto": ["Analyst"]},
        "phone": "+1234567890",
        "accUser": false
    }
]
```

`rbac/roles.json`:

```json
[
    {
        "id": "Administrator",
        "name": "Administrator",
        "permissions": {"demisto": ["adminPage", "scripts", "playbooks"]}
    },
    {
        "id": "Analyst",
        "name": "Analyst",
        "permissions": {"demisto": ["scripts", "playbooks"]}
    }
]
```

`rbac/user_groups.json`:

```json
[
    {
        "id": "group-uuid-001",
        "name": "SOC Team",
        "data": ["analyst1", "analyst2"]
    },
    {
        "id": "group-uuid-002",
        "name": "Admins",
        "data": ["admin"]
    }
]
```

### A.4 `integrations/instances.json`

Response from `GET /integration/instances`. The only explicitly accessed field is `name` (bare `i["name"]` in the `dump` command's single-instance lookup).

```json
[
    {
        "id": "instance-uuid-001",
        "name": "EWS_Main",
        "brand": "EWS v2",
        "enabled": "true",
        "defaultIgnored": "false",
        "configvalues": {}
    },
    {
        "id": "instance-uuid-002",
        "name": "EWS_Secondary",
        "brand": "EWS v2",
        "enabled": "false",
        "defaultIgnored": "false",
        "configvalues": {}
    },
    {
        "id": "instance-uuid-003",
        "name": "VirusTotal_Prod",
        "brand": "VirusTotal",
        "enabled": "true",
        "defaultIgnored": "false",
        "configvalues": {}
    }
]
```

Two instances share brand `"EWS v2"` to support deduplication testing.

### A.5 `content/playbook_search.json`

Response from `POST /playbook/search`. Wrapped in `{"playbooks": [...]}`. Fields accessed:

- `id` -- bare `playbook["id"]` in `_resolve_playbook_id`, `.get("id", "")` in filters
- `name` -- `.get("name", "")` in `_resolve_playbook_id` and filters
- `inputs` -- `.get("inputs") or []` in `filter_playbooks` (detail mode). Each input: `key`, `description`
- `outputs` -- `.get("outputs") or []` in `filter_playbooks` (detail mode). Each output: `contextPath`, `description`, `type`

```json
{
    "playbooks": [
        {
            "id": "22a1b2c3-d4e5-6f78-9a0b-c1d2e3f4a5b6",
            "name": "Phishing Investigation - Generic v2",
            "inputs": [
                {"key": "EmailFrom", "value": {}, "description": "The sender email address"},
                {"key": "EmailSubject", "value": {}, "description": "The email subject line"}
            ],
            "outputs": [
                {"contextPath": "Email.From", "description": "Sender address", "type": "string"},
                {"contextPath": "Email.IsPhishing", "description": "Whether the email is phishing", "type": "boolean"}
            ],
            "tasks": {"0": {"id": "0", "type": "start"}, "1": {"id": "1", "type": "regular"}},
            "deprecated": false,
            "hidden": false
        },
        {
            "id": "Malware_Investigation",
            "name": "Malware Investigation",
            "inputs": [],
            "outputs": null,
            "tasks": {"0": {"id": "0", "type": "start"}},
            "deprecated": false,
            "hidden": false
        },
        {
            "id": "aabbccdd-1122-3344-5566-778899aabbcc",
            "name": "Access Investigation - Generic",
            "inputs": null,
            "outputs": [],
            "tasks": {},
            "deprecated": false,
            "hidden": false
        }
    ]
}
```

Includes one playbook with `null` outputs and one with `null` inputs to cover the `or []` normalization.

### A.6 `content/automation_search.json`

Response from `POST /automation/search`. Wrapped in `{"scripts": [...]}`. Fields accessed:

- `id` -- `.get("id", "")` in filters
- `comment` -- `.get("comment", "")` in filters
- `arguments` -- `.get("arguments") or []` in `filter_scripts` (detail mode). Each argument: `name`, `required`, `deprecated`, `description`

```json
{
    "scripts": [
        {
            "id": "SetAndHandleEmpty",
            "name": "SetAndHandleEmpty",
            "comment": "Set a value in context under the key you entered, even if the value is empty.",
            "arguments": [
                {"name": "key", "required": true, "deprecated": false, "description": "The key to set"},
                {"name": "value", "required": false, "deprecated": false, "description": "The value to set"}
            ],
            "type": "python3",
            "tags": ["Utility"]
        },
        {
            "id": "Print",
            "name": "Print",
            "comment": "Prints text to war room (Markdown supported).",
            "arguments": [
                {"name": "value", "required": true, "deprecated": false, "description": "The value to print"}
            ],
            "type": "python3",
            "tags": ["Utility"]
        },
        {
            "id": "LegacyScript",
            "name": "LegacyScript",
            "comment": "A deprecated utility script.",
            "arguments": null,
            "type": "javascript",
            "tags": []
        }
    ]
}
```

Includes one script with `null` arguments to cover the `or []` normalization.

### A.7 `content/user_commands.json`

Response from `GET /user/commands`. A bare list (no envelope). Each entry is an integration instance. Fields accessed:

- `brand` -- `.get("brand", "")`, used as deduplication key
- `commands` -- `.get("commands") or []`, list of command dicts
  - `name` -- `.get("name", "")`
  - `description` -- `.get("description", "")` (detail mode)
  - `arguments` -- `.get("arguments") or []` (detail mode). Same shape as script arguments.
  - `outputs` -- `.get("outputs") or []` (detail mode). Each output: `contextPath`, `description`, `type`

```json
[
    {
        "brand": "EWS v2",
        "category": "Email",
        "name": "EWS_Main",
        "commands": [
            {
                "name": "ews-search-mailbox",
                "description": "Search for items in a mailbox.",
                "arguments": [
                    {"name": "query", "required": true, "deprecated": false, "description": "Search query"},
                    {"name": "limit", "required": false, "deprecated": false, "description": "Max results"}
                ],
                "outputs": [
                    {"contextPath": "EWS.Items.id", "description": "Item ID", "type": "string"},
                    {"contextPath": "EWS.Items.subject", "description": "Item subject", "type": "string"}
                ]
            },
            {
                "name": "ews-get-attachment",
                "description": "Get an attachment from an item.",
                "arguments": [
                    {"name": "item-id", "required": true, "deprecated": false, "description": "The item ID"}
                ],
                "outputs": []
            }
        ]
    },
    {
        "brand": "EWS v2",
        "category": "Email",
        "name": "EWS_Secondary",
        "commands": [
            {
                "name": "ews-search-mailbox",
                "description": "Search for items in a mailbox.",
                "arguments": [
                    {"name": "query", "required": true, "deprecated": false, "description": "Search query"},
                    {"name": "limit", "required": false, "deprecated": false, "description": "Max results"}
                ],
                "outputs": [
                    {"contextPath": "EWS.Items.id", "description": "Item ID", "type": "string"},
                    {"contextPath": "EWS.Items.subject", "description": "Item subject", "type": "string"}
                ]
            },
            {
                "name": "ews-get-attachment",
                "description": "Get an attachment from an item.",
                "arguments": [
                    {"name": "item-id", "required": true, "deprecated": false, "description": "The item ID"}
                ],
                "outputs": []
            }
        ]
    },
    {
        "brand": "VirusTotal",
        "category": "Threat Intelligence",
        "name": "VirusTotal_Prod",
        "commands": [
            {
                "name": "vt-file-scan",
                "description": "Scan a file with VirusTotal.",
                "arguments": [
                    {"name": "file", "required": true, "deprecated": false, "description": "File entry ID to scan"}
                ],
                "outputs": [
                    {"contextPath": "VirusTotal.Scan.id", "description": "Scan ID", "type": "string"}
                ]
            }
        ]
    }
]
```

Two entries with brand `"EWS v2"` to test `_group_commands_by_brand` deduplication.

### A.8 `packs/installed.json`

Response from `GET /contentpacks/metadata/installed`. A bare list. Fields accessed via bare dict lookup (will raise `KeyError` if missing):

- `id` (str) -- used in `is_installed()`, all manifest commands, `manifest.py` helpers
- `currentVersion` (str, semver) -- used in `is_installed()`, all manifest commands, `manifest.py` helpers

```json
[
    {
        "id": "CommonScripts",
        "currentVersion": "1.14.20",
        "name": "Common Scripts",
        "author": "Cortex XSOAR"
    },
    {
        "id": "Phishing",
        "currentVersion": "3.6.1",
        "name": "Phishing",
        "author": "Cortex XSOAR"
    },
    {
        "id": "MyOrg_EDR",
        "currentVersion": "2.0.0",
        "name": "MyOrg EDR Pack",
        "author": "MyOrg"
    },
    {
        "id": "EWS",
        "currentVersion": "2.4.8",
        "name": "EWS",
        "author": "Cortex XSOAR"
    }
]
```

Includes one pack with `author: "MyOrg"` (custom) and three marketplace packs. Aligns with test data in the manifest fixtures.

### A.9 `packs/installed_expired.json`

Response from `GET /contentpacks/installed-expired`. A bare list. Fields accessed in `get_outdated()`:

- `author` (str) -- bare `pack["author"]`, classifies custom vs. marketplace
- `id` (str) -- bare `pack["id"]`, used for artifact provider lookup and output
- `currentVersion` (str, semver) -- bare `pack["currentVersion"]`, compared against latest
- `updateAvailable` (bool) -- bare `pack["updateAvailable"]`, gate for marketplace packs
- `changelog` (dict) -- bare `pack["changelog"]`, keys are semver strings parsed with `version.parse`

```json
[
    {
        "id": "MyOrg_EDR",
        "currentVersion": "2.0.0",
        "name": "MyOrg EDR Pack",
        "author": "MyOrg",
        "updateAvailable": false,
        "changelog": {}
    },
    {
        "id": "Phishing",
        "currentVersion": "3.6.1",
        "name": "Phishing",
        "author": "Cortex XSOAR",
        "updateAvailable": true,
        "changelog": {
            "3.6.1": {"releaseNotes": "Bug fixes.", "released": "2024-03-01T00:00:00Z"},
            "3.7.0": {"releaseNotes": "New detection rules.", "released": "2024-06-01T00:00:00Z"},
            "3.7.1": {"releaseNotes": "Hotfix.", "released": "2024-06-15T00:00:00Z"}
        }
    },
    {
        "id": "EWS",
        "currentVersion": "2.4.8",
        "name": "EWS",
        "author": "Cortex XSOAR",
        "updateAvailable": false,
        "changelog": {
            "2.4.8": {"releaseNotes": "Maintenance release.", "released": "2024-02-01T00:00:00Z"}
        }
    }
]
```

- `MyOrg_EDR`: custom pack (`author` matches `custom_pack_authors`). `get_outdated()` calls `artifact_provider.get_latest_version("MyOrg_EDR")` for this one. Tests should mock the artifact provider to return e.g. `"2.1.0"`.
- `Phishing`: marketplace pack with `updateAvailable: true`. `get_outdated()` parses `changelog` keys (`"3.6.1"`, `"3.7.0"`, `"3.7.1"`) and picks `"3.7.1"` as latest.
- `EWS`: marketplace pack with `updateAvailable: false`. Skipped by `get_outdated()`.