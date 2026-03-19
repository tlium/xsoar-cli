# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- `config validate --connectivity-only` flag to test only XSOAR server connectivity, skipping artifacts repository checks.
- `config validate --all` flag to test all configured environments.

### Changed

- `config validate` now tests only the default environment by default. Previously it tested all configured environments. Use `--all` to restore the previous behavior.
- Renamed `config validate --stacktrace` to `--verbose` / `-v`. The option shows error details on failure rather than a stack trace, so the new name better reflects its behavior.