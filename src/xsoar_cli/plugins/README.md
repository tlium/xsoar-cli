# XSOAR CLI Plugin System

The XSOAR CLI plugin system allows you to extend the CLI with custom commands. Plugins are Python files placed in `~/.local/xsoar-cli/plugins/` that are automatically discovered and loaded.

## Quick Start

1. **Create the plugins directory**:
   ```bash
   mkdir -p ~/.local/xsoar-cli/plugins
   ```

2. **Create a plugin file** (`~/.local/xsoar-cli/plugins/hello_plugin.py`):
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

3. **Use your plugin**:
   ```bash
   xsoar-cli hello --name "Alice"
   ```

## Plugin Structure

A plugin must:
- Be a Python class that inherits from `XSOARPlugin`
- Implement the `name`, `version`, and `get_command()` methods
- The `get_command()` method must return a Click command

### Required Methods

- `name` - Unique identifier for your plugin
- `version` - Version string
- `get_command()` - Returns the Click command to register

### Optional Methods

- `description` - Plugin description
- `initialize()` - Called when plugin loads
- `cleanup()` - Called when plugin unloads

## Plugin Management

```bash
# List all plugins
xsoar-cli plugins list

# Show plugin details
xsoar-cli plugins info hello

# Validate plugins
xsoar-cli plugins validate

# Reload a plugin after changes
xsoar-cli plugins reload hello
```

## Command Conflicts

Plugin commands cannot use the same names as core CLI commands:
- `case`, `config`, `graph`, `manifest`, `pack`, `playbook`, `plugins`

If conflicts occur, use a different command name or create a command group.

## Notes

- The `XSOARPlugin` class is automatically available in plugin files
- Plugin files are discovered automatically from `~/.local/xsoar-cli/plugins/`
- Plugins are loaded when the CLI starts
- No special imports are needed for `XSOARPlugin`
