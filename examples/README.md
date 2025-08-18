# XSOAR CLI Plugin Examples

This directory contains example plugins that demonstrate various features and capabilities of the XSOAR CLI plugin system.

## Examples

### advanced_plugin.py

A comprehensive example plugin that demonstrates:

- **Multiple command groups** - Organized commands into logical groups (`cases`, `utils`)
- **XSOAR integration patterns** - Shows how to structure commands that would interact with XSOAR
- **Rich CLI features** - Options, arguments, validation, prompts, confirmations
- **File operations** - Reading/writing files, log analysis
- **Error handling** - Proper exception handling and user feedback
- **Code generation** - Dynamic template generation for new plugins

#### Usage

1. Copy the file to your plugins directory:
   ```bash
   cp examples/advanced_plugin.py ~/.local/xsoar-cli/plugins/
   ```

2. Verify the plugin is loaded:
   ```bash
   xsoar-cli plugins list
   ```

3. Use the plugin commands:
   ```bash
   # List cases
   xsoar-cli advanced cases list --limit 5
   
   # Create a test case
   xsoar-cli advanced cases create --name "Test Case" --severity High
   
   # Analyze a log file
   xsoar-cli advanced utils analyze-log /path/to/logfile.log --pattern "error"
   
   # Generate a new plugin template
   xsoar-cli advanced utils generate-template MyCustomPlugin
   
   # Show plugin statistics
   xsoar-cli advanced stats --verbose
   ```

## Creating Your Own Plugins

### Quick Start

1. **Use the built-in example generator**:
   ```bash
   xsoar-cli plugins create-example
   ```

2. **Or generate a custom template**:
   ```bash
   xsoar-cli advanced utils generate-template YourPluginName
   ```

3. **Copy to plugins directory**:
   ```bash
   cp YourPluginName_plugin.py ~/.local/xsoar-cli/plugins/
   ```

### Plugin Structure

Every plugin must inherit from `XSOARPlugin` and implement these required methods:

```python
import click

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
        @click.command(help="My command")
        def mycommand():
            click.echo("Hello from my plugin!")
        return mycommand
```

### Best Practices

1. **Use descriptive names** - Choose clear, unique command names
2. **Organize with groups** - Use `@click.group()` for multiple related commands
3. **Handle errors gracefully** - Use try/catch and proper error messages
4. **Validate inputs** - Use Click's built-in validation options
5. **Provide helpful output** - Use colors, formatting, and clear messages
6. **Document your commands** - Add help text and descriptions

### XSOAR Integration

To integrate with XSOAR in your plugins, use the configuration system:

```python
from xsoar_cli.utilities import load_config

@click.command()
@click.pass_context
@load_config
def my_xsoar_command(ctx: click.Context):
    # Access XSOAR client
    xsoar_client = ctx.obj["server_envs"]["dev"]
    
    # Use the client for XSOAR operations
    cases = xsoar_client.get_cases()
    # ... your logic here
```

## Testing Your Plugins

1. **Validate syntax**:
   ```bash
   xsoar-cli plugins validate
   ```

2. **Check plugin info**:
   ```bash
   xsoar-cli plugins info your_plugin_name
   ```

3. **Test commands**:
   ```bash
   xsoar-cli your-command --help
   xsoar-cli your-command test-args
   ```

4. **Reload during development**:
   ```bash
   xsoar-cli plugins reload your_plugin_name
   ```

## Sharing Plugins

To share your plugins with others:

1. **Simple sharing** - Share the `.py` file directly
2. **Documentation** - Include usage examples and requirements
3. **Dependencies** - List any external packages needed
4. **Testing** - Provide test cases or examples

## Getting Help

- **Plugin documentation**: `src/xsoar_cli/plugins/README.md`
- **List available plugins**: `xsoar-cli plugins list`
- **Plugin commands help**: `xsoar-cli plugins --help`
- **Command-specific help**: `xsoar-cli <plugin-command> --help`

Happy plugin development! 🚀