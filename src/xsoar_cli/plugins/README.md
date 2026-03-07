# Plugin Development

Plugins are Python files placed in `~/.local/xsoar-cli/plugins/` that are automatically discovered and loaded at CLI startup.

## Quick Start

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

## Plugin Structure

A plugin must be a Python class that inherits from `XSOARPlugin`. The `XSOARPlugin` base class is automatically available in plugin files without any imports.

**Required methods:**
- `name` - Unique identifier for your plugin
- `version` - Version string
- `get_command()` - Returns a Click command or group to register

**Optional methods:**
- `description` - Plugin description
- `initialize()` - Called when plugin loads

## Command Conflicts

Plugin commands cannot use the same names as core CLI commands (`case`, `config`, `graph`, `integration`, `manifest`, `pack`, `playbook`, `plugins`, `rbac`). If a conflict is detected, the plugin command is skipped. Use a different command name or wrap your commands in a Click group.