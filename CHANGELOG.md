# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [2.4.0] - 2026-06-17

### Added

- `content get-detached --type all` queries both scripts and playbooks and displays results for each type.
- `content list --output-format` option (choices: `table`, `json`, `plain`, default: `table`). `table` is human-readable aligned columns, `json` is machine-readable, and `plain` is tab-separated values suitable for piping to tools like `grep`.
- `content list --search TERM` option. Filters the listed items with a case-insensitive substring match against each item's id, name, and description. Content types and integration brands with no matching items are omitted, and a `No content matching '<term>' found.` message is shown when nothing matches.
- `content describe --type [script|playbook|command] NAME` command. Shows a single content item in detail: description, arguments, and inputs/outputs. Commands also show the integration brand and its configured instances (name and state). Supports `--output-format [table|json]` (default: `table`). See the [content README](src/xsoar_cli/commands/content/README.md) for details.
- `case get-context CASENUMBER` command. Retrieves the investigation context tree for a case as JSON, matching `demisto.context()` at runtime. The incident record is not merged in. See the [case README](src/xsoar_cli/commands/case/README.md) for details.
- `case get-entry ENTRY_ID` command. Retrieves a single War Room entry by its full ID (e.g. `112@153483`) as JSON. The case ID is derived from the entry ID. Exits non-zero with a clear message when the entry ID is malformed or the entry is not found. See the [case README](src/xsoar_cli/commands/case/README.md) for details.
- `case get-entries CASENUMBER` command. Retrieves all War Room entries for a case as a JSON array, or an empty array when the case has no entries. See the [case README](src/xsoar_cli/commands/case/README.md) for details.

### Changed

- `content get-detached` now prints a human-readable summary instead of raw JSON. Output is a count followed by one line per item in the form `<name> (ID: <id>)`, or `No detached <type> found` when there are none.
- **Breaking:** `content list` now defaults to a human-readable table instead of JSON. Use `--output-format json` for machine-readable output.
- `content list` playbook output now shows the playbook ID and description (read from the `comment` field) instead of the name and ID.
- `content list` command output now shows the command name and description and no longer includes the integration brand. The summary-level JSON structure for commands is now a list of `{name, description}` objects instead of plain command-name strings.

### Removed

- **Breaking:** `content list --detail-level` option, along with its `short`, `extended`, and `full` levels. `content list` now always produces a curated summary. Per-item detail (arguments, inputs, outputs) is available through the `content describe` command.

### Fixed

- `content get-detached` now returns only the content items that are actually detached. The previous query returned all system items, so the command reported every system script (or playbook) as detached instead of just the detached ones. Results are now filtered on each item's `detached` field.

## [2.3.0] - 2026-06-04

### Added

- `execute command NAME [ARGS]...` runs an automation script or integration command against XSOAR, in the user's playground by default or a specific case with `--case-id`. See the [execute README](src/xsoar_cli/commands/execute/README.md) for details.
- `execute playbook NAME` starts a playbook in the user's playground, or a specific case with `--case-id`. See the [execute README](src/xsoar_cli/commands/execute/README.md) for details.

### Fixed

- `content download` now correctly resolves playbooks whose ID differs from their name when the name contains spaces. Previously, the name search query was not quoted, causing it to return no results. In practice this affected custom playbooks created in the XSOAR UI, which use a UUID as their ID.

### Changed

- **Breaking:** `manifest validate` now validates all packs by default (previously defaulted to `--mode diff`). Use the new `--only-changed` flag to validate only packs that differ from what is installed on the server.
- **Breaking:** `content list` now uses a single `--detail-level` option (choices: `short`, `extended`, `full`, default: `short`) instead of the separate `--details` and `--verbose` flags.
- Plugin commands are now listed under a separate `Plugins:` section in `--help` output instead of being mixed with core commands.

### Removed

- `manifest validate --mode` option. Use `--only-changed` instead of `--mode diff`. Full validation is now the default.
- `content list --details` flag. Use `--detail-level extended` instead.
- `content list --verbose` flag. Use `--detail-level full` instead.

## [2.2.0] - 2026-04-10

### Added

- `config set-version-check` command to enable or disable the version update check on CLI startup. Accepts `--enable` or `--disable`.
- `plugins init` command to create the plugins directory and generate an example plugin.

### Changed

- **Breaking:** Plugins must explicitly import `XSOARPlugin` (`from xsoar_cli.plugins import XSOARPlugin`). The base class is no longer injected automatically and so old plugins require modification. See the [plugin README](src/xsoar_cli/plugins/README.md) for details.
- Plugin commands (`list`, `info`, `validate`) now report a clear error when the plugins directory has not been initialized.
- Plugin registration failures no longer prevent remaining plugins from loading.
- `content get-detached --type` is now required. The `all` choice has been removed; specify `scripts` or `playbooks` explicitly.
- `integration dump`, `rbac getroles`, `rbac getusers`, and `rbac getusergroups` no longer emit a trailing blank line after JSON output.
- `config show` now uses `click.echo()` instead of `print()`, improving behavior when piping output to other tools.

### Removed

- The plugins directory is no longer automatically created on CLI startup. Run `xsoar-cli plugins init` to create it explicitly.

### Fixed

- `content get-detached` no longer fails when invoked without `--type` due to a stale default value that referenced the removed `all` choice.
- Content bundle download (`get_content_bundle`) now raises on HTTP errors instead of silently proceeding and failing with a confusing `tarfile` error.

## [2.1.1] - 2026-04-08

### Changed

- `manifest generate` now uses an `--output-dir` option (default: current directory) instead of a positional path argument. The output file is always named `xsoar_config.json`. Prompts for confirmation if the file already exists.
- `manifest update`, `manifest validate`, `manifest diff`, and `manifest deploy` now support file path tab completion for the manifest argument.

## [2.1.0] - 2026-04-08

### Added

- `completions install` command to generate and install shell completion scripts for Bash, Zsh (including Oh My Zsh), and Fish. Auto-detects the current shell from `$SHELL`, overridable with `--shell`.
- `completions uninstall` command to remove previously installed completion scripts.
- Shell completion no longer triggers the version update check or logging setup, which previously leaked output into completion results.

## [2.0.2] - 2026-04-08

### Changed

- Redesigned test suite into a two-layer structure: `tests/cli/` for CLI integration tests (CliRunner-based) and `tests/unit/` for direct unit tests. Replaced repetitive `@patch` decorator stacking and manual `CliRunner` instantiation with shared fixtures (`invoke`, `mock_xsoar_env`, `mock_content_env`, `mock_case_env`) and factory fixtures (`make_mock_client`, `make_http_error`, `make_case_response`).

### Removed

- `playbook download` command. Use `content download --type playbook` instead, which supports name-to-ID resolution fallback, preserves original YAML formatting, and adds the `--output` option.

## [2.0.1] - 2026-04-07

### Added

- `content download` subcommand for downloading individual content items by name. Supports playbooks and layouts (`xsoar-cli content download --type playbook|layout <name>`).
- `content download --output` option to specify the content repository root directory. Useful when running xsoar-cli from outside the content repository.
- `content download` automatically runs `demisto-sdk format` on downloaded files to ensure they conform to the content repository standard.
- `content download` re-attaches downloaded content items to their pack after writing, so they no longer appear as detached in XSOAR.
- `content download` resolves the content item's pack ID and writes to the correct `Packs/<pack_id>/` directory. Prompts for fallback to the current working directory if the pack directory does not exist.

## [2.0.0] - 2026-04-07

### Fixed

- Fixed typo "Uknown" in error messages for `Content.download_item`, `Content.attach_item`, and `Content.detach_item`.
- Fixed `content list` command function shadowing the Python builtin `list()`. The function is renamed internally to `list_content` while the CLI-facing command name remains `list`.
- Fixed `Packs.deploy` temp file handling: the file is now written and closed via a context manager, and cleaned up in a `finally` block. Previously the temp file was never deleted and the pattern would fail on Windows.

### Changed

- `Packs.get_outdated` now logs a warning instead of printing to stderr when a custom pack is installed but not found in the artifacts repository. The domain layer no longer produces user-facing output directly.
- `Packs.get_outdated` now returns an `OutdatedResult` NamedTuple containing both the outdated packs list and a list of skipped custom pack IDs. The `pack get-outdated` and `manifest update` commands now warn the user when custom packs are installed but not found in the artifacts repository.
- `S3ArtifactProvider` now initializes the boto3 session and S3 resource lazily on first use, matching the pattern used by `AzureArtifactProvider`. Previously, construction failed immediately if AWS credentials were missing, even when the artifact provider was not needed by the current command.
- Added missing return type annotations to `Content._list_playbooks`, `Content._list_scripts`, `Content._list_commands`, and `Content.list`.
- Simplified redundant `skip_validation`/`skip_verify` branching in `Packs.deploy`. Both branches set `skip_validation` to the same value; the conditional is now only on `skip_verify`.
- Simplified `validate_xsoar_connectivity` decorator to only handle the single-environment case. The `case clone` command now validates connectivity for both environments inline instead of using a lambda passed to the decorator.

- Merged xsoar-client into xsoar-cli as the `xsoar_cli.xsoar_client` subpackage. The standalone `xsoar-client` package is no longer a dependency.
- Command modules now use domain class methods directly (e.g., `client.cases.get()` instead of `client.get_case()`).
- Missing required environment config keys (`base_url`, `api_token`, `server_version`) now produce a clear error message identifying the environment and missing key, instead of a raw `KeyError`.
- `verify_ssl` now defaults to `True` when omitted from an environment's config. Previously, a missing key would cause a crash.

### Removed

- Deprecated proxy methods on the `Client` class (`get_case`, `create_case`, `get_roles`, `get_users`, `get_user_groups`, `get_integrations`, `download_item`, `attach_item`, `detach_item`, `get_installed_packs`, `get_installed_expired_packs`, `is_installed`, `is_pack_available`, `download_pack`, `deploy_pack`, `deploy_zip`, `delete`, `get_outdated_packs`, `get_latest_custom_pack_version`). Use the corresponding domain class methods instead.
- `ClientConfig` dataclass (`xsoar_client/config.py`). The `Client` constructor now accepts connection parameters directly.
- Environment variable fallback for client credentials (`DEMISTO_API_KEY`, `DEMISTO_BASE_URL`, `XSIAM_AUTH_ID`). All configuration is managed through the config file.

## [1.5.1] - 2026-03-27

### Added

- `config validate --connectivity-only` flag to test only XSOAR server connectivity, skipping artifacts repository checks.
- `config validate --all` flag to test all configured environments.
- Version update check on CLI startup. When `skip_version_check` is set to `false` in the config file and the package is installed from PyPI, the CLI checks for newer versions and prints a notice to stderr. Disabled by default.
- `skip_version_check` key in the config file template.

### Changed

- `config validate` now tests only the default environment by default. Previously it tested all configured environments. Use `--all` to restore the previous behavior.
- Renamed `config validate --stacktrace` to `--verbose` / `-v`. The option shows error details on failure rather than a stack trace, so the new name better reflects its behavior.

### Removed

- `config validate --stacktrace` option. Use `--verbose` / `-v` instead.
