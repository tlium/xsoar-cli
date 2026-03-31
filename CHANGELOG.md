# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed

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