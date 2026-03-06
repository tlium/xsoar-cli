# Integration

BETA command. Save and load integration instance configuration.

## Dump Config

Dump the configuration of a named integration instance. Output is JSON formatted with 4-space indentation.

**Syntax:** `xsoar-cli integration dumpconfig [OPTIONS] NAME`

**Options:**
- `--environment TEXT` - Target environment (default: uses default environment from config)

**Arguments:**
- `NAME` - The name of the integration instance

**Examples:**
```
xsoar-cli integration dumpconfig "My Integration Instance"
xsoar-cli integration dumpconfig --environment prod "My Integration Instance"
```

## Load Config

Load integration instance configuration from a JSON file. Not yet implemented.

**Syntax:** `xsoar-cli integration loadconfig [OPTIONS] NAME`

**Options:**
- `--environment TEXT` - Target environment (default: uses default environment from config)

**Arguments:**
- `NAME` - The name of the integration instance