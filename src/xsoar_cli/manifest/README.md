# Manifest

Content pack deployment management commands using a declarative configuration file (`xsoar_config.json`).

## Generate

Generate a new manifest file from currently installed content packs. Assumes all packs are marketplace packs (no custom packs).

**Syntax:** `xsoar-cli manifest generate [OPTIONS] MANIFEST_PATH`

**Options:**
- `--environment TEXT` - Target environment (default: uses default environment from config)

**Arguments:**
- `MANIFEST_PATH` - Path where the new manifest file will be created

**Examples:**
```
xsoar-cli manifest generate ./xsoar_config.json
xsoar-cli manifest generate --environment prod ./xsoar_config.json
```

## Validate

Validate manifest JSON syntax and verify all specified content packs are available. Tests connectivity to pack sources and checks local pack metadata for development packs.

**Syntax:** `xsoar-cli manifest validate [OPTIONS] MANIFEST_PATH`

**Options:**
- `--environment TEXT` - Target environment (default: uses default environment from config)

**Arguments:**
- `MANIFEST_PATH` - Path to the manifest file to validate

**Examples:**
```
xsoar-cli manifest validate ./xsoar_config.json
xsoar-cli manifest validate --environment staging ./xsoar_config.json
```

## Update

Compare installed packs against available versions and update the manifest file with latest versions. Prompts for confirmation on each upgrade.

**Syntax:** `xsoar-cli manifest update [OPTIONS] MANIFEST_PATH`

**Options:**
- `--environment TEXT` - Target environment (default: uses default environment from config)

**Arguments:**
- `MANIFEST_PATH` - Path to the manifest file to update

**Examples:**
```
xsoar-cli manifest update ./xsoar_config.json
xsoar-cli manifest update --environment dev ./xsoar_config.json
```

## Diff

Compare the manifest definition against what is actually installed on the XSOAR server. Shows packs that are missing or have version mismatches.

**Syntax:** `xsoar-cli manifest diff [OPTIONS] MANIFEST_PATH`

**Options:**
- `--environment TEXT` - Target environment (default: uses default environment from config)

**Arguments:**
- `MANIFEST_PATH` - Path to the manifest file to compare

**Examples:**
```
xsoar-cli manifest diff ./xsoar_config.json
xsoar-cli manifest diff --environment prod ./xsoar_config.json
```

## Deploy

Install or update content packs on the XSOAR server according to the manifest. Only deploys packs that differ from current installation.

**Syntax:** `xsoar-cli manifest deploy [OPTIONS] MANIFEST_PATH`

**Options:**
- `--environment TEXT` - Target environment (default: uses default environment from config)
- `--verbose` - Show detailed information about skipped packs
- `--yes` - Skip confirmation prompt

**Arguments:**
- `MANIFEST_PATH` - Path to the manifest file to deploy

**Examples:**
```
xsoar-cli manifest deploy ./xsoar_config.json
xsoar-cli manifest deploy --environment prod --yes ./xsoar_config.json
xsoar-cli manifest deploy --verbose ./xsoar_config.json
```

## Manifest File Structure

The `xsoar_config.json` file defines content packs to be installed:

```json
{
    "custom_packs": [
        {
            "id": "MyCustomPack",
            "version": "1.0.0",
            "_comment": "Optional documentation comment"
        }
    ],
    "marketplace_packs": [
        {
            "id": "CommonScripts",
            "version": "1.20.0"
        }
    ]
}
```

- **custom_packs**: Organization-developed packs stored in artifact repositories
- **marketplace_packs**: Official Palo Alto Networks content packs
- **_comment**: Optional field for documentation (preserved during updates)