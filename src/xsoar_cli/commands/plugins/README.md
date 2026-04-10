# Plugins

Manage plugins loaded into the CLI.

## Init

Initialize the plugins directory and generate an example plugin.

**Syntax:** `xsoar-cli plugins init`

Creates `~/.local/xsoar-cli/plugins/` (if it does not exist) and writes an example `hello.py` plugin. If the example file already exists, prompts for confirmation before overwriting.

**Examples:**
```
xsoar-cli plugins init
```

## List

List all available and loaded plugins.

**Syntax:** `xsoar-cli plugins list [OPTIONS]`

**Options:**
- `-v, --verbose` - Show detailed information (name, version, description)

**Examples:**
```
xsoar-cli plugins list
xsoar-cli plugins list --verbose
```

## Info

Show detailed information about a specific plugin.

**Syntax:** `xsoar-cli plugins info PLUGIN_NAME`

**Arguments:**
- `PLUGIN_NAME` - The name of the plugin file (without `.py` extension)

**Examples:**
```
xsoar-cli plugins info hello
```

## Validate

Validate all plugins in the plugins directory. Checks that each plugin can load and provide a valid Click command, and reports any command name conflicts with core commands.

**Syntax:** `xsoar-cli plugins validate`

**Examples:**
```
xsoar-cli plugins validate
```
