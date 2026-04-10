# Plugin Development

Plugins are Python files placed in `~/.local/xsoar-cli/plugins/` that are automatically discovered and loaded at CLI startup.

## Quick Start

1. Initialize the plugins directory:
   ```
   xsoar-cli plugins init
   ```
   This creates `~/.local/xsoar-cli/plugins/` and writes an example `hello.py` plugin.

2. Use your plugin:
   ```
   xsoar-cli hello --name "Alice"
   ```

## Plugin Structure

A plugin must be a Python class that inherits from `XSOARPlugin` and imports it explicitly:

```python
from xsoar_cli.plugins import XSOARPlugin
```

**Required methods:**
- `name` - Unique identifier for your plugin
- `version` - Version string
- `get_command()` - Returns a Click command or group to register

**Optional methods:**
- `description` - Plugin description
- `initialize()` - Called when plugin loads

## Command Conflicts

Plugin commands cannot use the same names as core CLI commands (`case`, `completions`, `config`, `content`, `graph`, `integration`, `manifest`, `pack`, `plugins`, `rbac`). If a conflict is detected, the plugin command is skipped. Use a different command name or wrap your commands in a Click group.

## Limitations

- Each plugin must be a single self-contained `.py` file.
- Imports between plugin files in the plugins directory are not supported.
- Plugin file names must not collide with Python standard library module names or installed packages (e.g., do not name a plugin `json.py` or `logging.py`).
