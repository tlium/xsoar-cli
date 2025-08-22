# Pack

Content pack management commands for XSOAR.

## Delete

Delete a content pack from the XSOAR server. Verifies the pack is installed before attempting deletion.

**Syntax:** `xsoar-cli pack delete [OPTIONS] PACK_ID`

**Options:**
- `--environment TEXT` - Target environment (default: uses default environment from config)

**Arguments:**
- `PACK_ID` - The ID of the content pack to delete

**Examples:**
```
xsoar-cli pack delete MyCustomPack
xsoar-cli pack delete --environment prod CommonScripts
```

## Get Outdated

Display a list of outdated content packs showing current and latest available versions in table format.

**Syntax:** `xsoar-cli pack get-outdated [OPTIONS]`

**Options:**
- `--environment TEXT` - Target environment (default: uses default environment from config)

**Examples:**
```
xsoar-cli pack get-outdated
xsoar-cli pack get-outdated --environment staging
```
