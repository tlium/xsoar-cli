# Plugins

Manage and extend the CLI with custom commands.

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

## Reload

Reload a specific plugin after making changes to its source file.

**Syntax:** `xsoar-cli plugins reload PLUGIN_NAME`

**Arguments:**
- `PLUGIN_NAME` - The name of the plugin to reload

**Examples:**
```
xsoar-cli plugins reload hello
```

---

## Writing Plugins

Plugins are Python files placed in `~/.local/xsoar-cli/plugins/` that are automatically discovered and loaded at CLI startup.

### Quick Start

1. Create the plugins directory:
   ```
   mkdir -p ~/.local/xsoar-cli/plugins
   ```

2. Create a plugin file (`~/.local/xsoar-cli/plugins/hello_plugin.py`):
   ```python
   import click

   class HelloPlugin(XSOARPlugin):
       @property
       def name(self) -> str:
           return "hello"

       @property
       def version(self) -> str:
           return "1.0.0"

       def get_command(self) -> click.Command:
           @click.command(help="Say hello")
           @click.option("--name", default="World", help="Name to greet")
           def hello(name: str):
               click.echo(f"Hello, {name}!")
           return hello
   ```

3. Use your plugin:
   ```
   xsoar-cli hello --name "Alice"
   ```

### Plugin Structure

A plugin must be a Python class that inherits from `XSOARPlugin`. The `XSOARPlugin` base class is automatically available in plugin files without any imports.

**Required methods:**
- `name` - Unique identifier for your plugin
- `version` - Version string
- `get_command()` - Returns a Click command or group to register

**Optional methods:**
- `description` - Plugin description
- `initialize()` - Called when plugin loads
- `cleanup()` - Called when plugin unloads

### Command Conflicts

Plugin commands cannot use the same names as core CLI commands (`case`, `config`, `graph`, `integration`, `manifest`, `pack`, `playbook`, `plugins`, `rbac`). If a conflict is detected, the plugin command is skipped. Use a different command name or wrap your commands in a Click group.