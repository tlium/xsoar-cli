# Playbook

Playbook management commands for XSOAR development workflows.

## Download

Download a playbook from XSOAR, format it with demisto-sdk, and re-attach it to the server. Designed for content repository development workflows.

**Syntax:** `xsoar-cli playbook download [OPTIONS] NAME`

**Options:**
- `--environment TEXT` - Target environment (default: uses default environment from config)

**Arguments:**
- `NAME` - The name of the playbook to download

**Examples:**
```
xsoar-cli playbook download "My Awesome Playbook"
xsoar-cli playbook download --environment dev "Security Investigation"
```

## Requirements

- Must be run from the root of a content repository with proper directory structure
- Target directory `Packs/<PackID>/Playbooks/` must exist
- `demisto-sdk` must be installed and available in PATH

## Behavior

1. Downloads the specified playbook from XSOAR
2. Detects the content pack ID from playbook metadata
3. Saves to `$(cwd)/Packs/<PackID>/Playbooks/<playbook_name>.yml`
4. Runs `demisto-sdk format --assume-yes --no-validate --no-graph` on the file
5. Re-attaches the formatted playbook to XSOAR
6. Replaces whitespace characters in filenames with underscores

## Limitations

- Only supports playbooks that are already part of a content pack
- Requires existing content repository directory structure
- Attempting to download non-existing playbooks results in server errors
- Does not support completely new playbooks (not yet implemented)