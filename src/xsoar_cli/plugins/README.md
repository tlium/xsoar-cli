# XSOAR CLI Plugin System

The XSOAR CLI plugin system allows you to extend the CLI with custom commands and functionality. Plugins are Python files that you place in a special directory, and they're automatically discovered and loaded by the CLI.

## Quick Start

1. **Create the plugins directory** (if it doesn't exist):
   ```bash
   mkdir -p ~/.local/xsoar-cli/plugins
   ```

2. **Create an example plugin**:
   ```bash
   xsoar-cli plugins create-example
   ```

3. **Test the example plugin**:
   ```bash
   xsoar-cli example hello --name "World"
   xsoar-cli example info
   ```

## Plugin Directory

Plugins are stored in: `~/.local/xsoar-cli/plugins/`

Each plugin is a Python file (`.py`) in this directory. The CLI automatically discovers and loads all Python files in this directory when it starts.

## Creating a Plugin

### Basic Plugin Structure

A plugin is a Python class that inherits from `XSOARPlugin`. Here's the minimal structure:

```python
import click
from xsoar_cli.plugins import XSOARPlugin

class MyPlugin(XSOARPlugin):
    @property
    def name(self) -> str:
        return "myplugin"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "My custom plugin"

    def get_command(self) -> click.Command:
        @click.command(help="My custom command")
        def mycommand():
            click.echo("Hello from my plugin!")

        return mycommand
```

### Complete Example

Here's a more comprehensive example (`~/.local/xsoar-cli/plugins/my_plugin.py`):

```python
"""
My Custom XSOAR Plugin

This plugin demonstrates various features of the plugin system.
"""

import click
from xsoar_cli.plugins import XSOARPlugin

class MyCustomPlugin(XSOARPlugin):
    @property
    def name(self) -> str:
        return "mycustom"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "A custom plugin with multiple commands"

    def get_command(self) -> click.Command:
        """Return the main command group for this plugin."""

        @click.group(help="My custom commands")
        def mycustom():
            """Main command group for my custom plugin."""
            pass

        @click.command(help="Greet someone")
        @click.option("--name", default="World", help="Name to greet")
        @click.option("--times", default=1, help="Number of times to greet")
        def greet(name: str, times: int):
            """Greet someone multiple times."""
            for i in range(times):
                click.echo(f"Hello, {name}!")

        @click.command(help="Show current status")
        @click.option("--verbose", "-v", is_flag=True, help="Verbose output")
        def status(verbose: bool):
            """Show plugin status."""
            click.echo(f"Plugin: {self.name} v{self.version}")
            if verbose:
                click.echo(f"Description: {self.description}")
                click.echo("Status: Active")

        @click.command(help="Process a file")
        @click.argument("filename", type=click.Path(exists=True))
        @click.option("--output", "-o", help="Output file")
        def process(filename: str, output: str):
            """Process a file."""
            click.echo(f"Processing file: {filename}")
            if output:
                click.echo(f"Output will be saved to: {output}")
            # Your processing logic here

        # Add commands to the group
        mycustom.add_command(greet)
        mycustom.add_command(status)
        mycustom.add_command(process)

        return mycustom

    def initialize(self):
        """Initialize the plugin."""
        click.echo("My custom plugin initialized!")

    def cleanup(self):
        """Cleanup when the plugin is unloaded."""
        pass
```

After saving this file, you can use it like:

```bash
xsoar-cli mycustom greet --name John --times 3
xsoar-cli mycustom status --verbose
xsoar-cli mycustom process myfile.txt --output result.txt
```

## Plugin API Reference

### XSOARPlugin Base Class

All plugins must inherit from `XSOARPlugin` and implement the required methods:

#### Required Properties

- **`name`** (str): The plugin name, used for identification
- **`version`** (str): The plugin version
- **`description`** (str, optional): A description of what the plugin does

#### Required Methods

- **`get_command()`**: Must return a `click.Command` or `click.Group` object

#### Optional Methods

- **`initialize()`**: Called once when the plugin is loaded
- **`cleanup()`**: Called when the plugin is unloaded

### Using XSOAR CLI Utilities

Your plugins can access the same utilities that the core CLI uses:

```python
from xsoar_cli.utilities import load_config

@click.command()
@click.pass_context
@load_config
def my_command(ctx: click.Context):
    # Access XSOAR client
    xsoar_client = ctx.obj["server_envs"]["dev"]["xsoar_client"]
    # Use the client...
```

## Plugin Management Commands

### List Plugins

```bash
# List all plugins
xsoar-cli plugins list

# Show detailed information
xsoar-cli plugins list --verbose
```

### Check for Command Conflicts

```bash
# Check for conflicts between plugin commands and core CLI commands
xsoar-cli plugins check-conflicts
```

### Plugin Information

```bash
# Show information about a specific plugin
xsoar-cli plugins info my_plugin
```

### Validate Plugins

```bash
# Validate all plugins
xsoar-cli plugins validate
```

### Reload Plugin

```bash
# Reload a plugin after making changes
xsoar-cli plugins reload my_plugin
```

### Open Plugins Directory

```bash
# Open the plugins directory in your file manager
xsoar-cli plugins open
```

## Command Conflicts

The plugin system automatically detects when a plugin tries to register a command that conflicts with existing core CLI commands.

### How Conflict Detection Works

1. **Automatic Detection**: When plugins are loaded, the system checks if any plugin command names conflict with core commands
2. **Conflict Prevention**: Conflicting plugin commands are **not registered** - the core command takes precedence
3. **User Notification**: Conflicts are reported through various commands

### Checking for Conflicts

```bash
# Check for any command conflicts
xsoar-cli plugins check-conflicts

# List plugins (shows conflicts in output)
xsoar-cli plugins list

# Validate all plugins (includes conflict checking)
xsoar-cli plugins validate
```

### Example Conflict Scenario

If you create a plugin with a command named `case`, it will conflict with the core `case` command:

```python
class MyPlugin(XSOARPlugin):
    def get_command(self):
        @click.command()
        def case():  # ❌ This conflicts with core 'case' command
            click.echo("My case command")
        return case
```

**Result**: The plugin loads successfully, but the `case` command remains the core command. The plugin's `case` command is ignored.

### Resolving Conflicts

**Option 1: Rename the command**
```python
class MyPlugin(XSOARPlugin):
    def get_command(self):
        @click.command()
        def mycase():  # ✅ Unique name
            click.echo("My case command")
        return mycase
```

**Option 2: Use a command group**
```python
class MyPlugin(XSOARPlugin):
    def get_command(self):
        @click.group()
        def myplugin():
            pass

        @click.command()
        def case():  # ✅ Namespaced as 'myplugin case'
            click.echo("My case command")

        myplugin.add_command(case)
        return myplugin
```

### Core Commands to Avoid

These command names are reserved by the core CLI:
- `case` - Case/incident management
- `config` - Configuration management
- `graph` - Dependency graphs
- `manifest` - Manifest operations
- `pack` - Content pack operations
- `playbook` - Playbook operations
- `plugins` - Plugin management

## Best Practices

### 1. Plugin Naming

- Use descriptive names for your plugin class and command
- Avoid conflicts with existing commands
- Use lowercase with underscores for file names: `my_plugin.py`

### 2. Command Structure

- Use command groups for plugins with multiple commands
- Provide helpful descriptions and help text
- Use appropriate Click decorators for options and arguments

### 3. Error Handling

```python
def get_command(self) -> click.Command:
    @click.command()
    def mycommand():
        try:
            # Your logic here
            pass
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            raise click.Abort()

    return mycommand
```

### 4. Configuration Access

```python
from xsoar_cli.utilities import load_config

@click.command()
@click.pass_context
@load_config
def my_command(ctx: click.Context):
    # Access configuration
    config = ctx.obj
    # Access XSOAR clients
    dev_client = ctx.obj["server_envs"]["dev"]["xsoar_client"]
```

### 5. Logging

```python
import logging

logger = logging.getLogger(__name__)

class MyPlugin(XSOARPlugin):
    def initialize(self):
        logger.info("Plugin initialized")
```

## Troubleshooting

### Plugin Not Loading

1. **Check file location**: Ensure your plugin is in `~/.local/xsoar-cli/plugins/`
2. **Check syntax**: Make sure your Python syntax is correct
3. **Check inheritance**: Ensure your class inherits from `XSOARPlugin`
4. **Check required methods**: Implement all required properties and methods

### Debugging Plugins

```bash
# Enable debug mode to see plugin loading details
xsoar-cli --debug plugins list

# Validate a specific plugin
xsoar-cli plugins validate

# Check for command conflicts
xsoar-cli plugins check-conflicts

# Check plugin info
xsoar-cli plugins info my_plugin
```

### Common Issues

1. **Import errors**: Make sure all required modules are installed
2. **Command conflicts**: Use `xsoar-cli plugins check-conflicts` to identify naming conflicts
3. **Missing methods**: Implement all required abstract methods
4. **Invalid return types**: Ensure `get_command()` returns a Click command
5. **Plugin not visible**: Check if your command conflicts with a core command

## Examples Repository

For more examples and inspiration, check out the community plugin examples at:
`~/.local/xsoar-cli/plugins/example_plugin.py` (created with `xsoar-cli plugins create-example`)

## Development Tips

### Testing Your Plugin

1. Create your plugin file
2. Test loading: `xsoar-cli plugins validate`
3. Test functionality: Use your commands
4. Reload after changes: `xsoar-cli plugins reload my_plugin`

### Using External Dependencies

If your plugin needs external packages, make sure they're installed in the same environment as xsoar-cli:

```bash
pip install my-required-package
```

Then import them in your plugin:

```python
try:
    import my_required_package
except ImportError:
    click.echo("Error: my-required-package is required for this plugin")
    raise click.Abort()
```

### Plugin Distribution

You can share plugins by simply sharing the Python file. Users can place it in their plugins directory and it will be automatically discovered.

For more complex plugins, consider packaging them as proper Python packages that install the plugin file automatically.
