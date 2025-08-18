# xsoar-cli
-----
This tool is made to help provide a smoother workflow for developers, but also for power users to get useful information out of XSOAR from
the terminal. It is mostly useful if you are using a CICD workflow to deploy your XSOAR content, and most of the functionality assumest that
you have your content stored in a [content repository](https://github.com/demisto/content-ci-cd-template).

Pull Requests are very welcome and appreciated!


*IMPORTANT NOTE*
This CLI tools is made to be run from the root of a content repository. Some commands depends on files located in your
content repository or expects a certain directory structure to be available from your currently working directory.

## Installation
```
pip install xsoar-cli
```
## Upgrading
```
pip install --upgrade xsoar-cli
```


## Configuration
The xsoar-cli config file is located in `~/.config/xsoar-cli/config.json`. To create a configuration file from template, please run
```
xsoar-cli config create
```
Open up the newly created configuration file and add values that correspond with your environment.

*IMPORTANT NOTES* 
- The configuration key `"custom_pack_authors": ["SOMEONE"]` is needed in order for `xsoar-cli` to be able to determine which content packs 
are your own custom content packs and which are supplied from Palo Alto upstream. Use whatever values you may have set in pack_metadata.json
 in the content packs in your content repository.

## Usage
```
xsoar-cli <command> <sub-command> <args>
```
For information about available commands, run `xsoar-cli` without arguments.

For more information on a specific command execute `xsoar-cli <command> --help.`

### Commands
1. [case](src/xsoar_cli/case/README.md)
2. [config](src/xsoar_cli/config/README.md)
3. [graph](src/xsoar_cli/graph/README.md)
4. [manifest](src/xsoar_cli/manifest/README.md)
5. [pack](src/xsoar_cli/pack/README.md)
6. [playbook](src/xsoar_cli/playbook/README.md)
7. [plugins](src/xsoar_cli/plugins/README.md)

## Plugin System

xsoar-cli supports a plugin system that allows you to extend the CLI with custom commands. Plugins are Python files that you place in `~/.local/xsoar-cli/plugins/` and they're automatically discovered and loaded.

### Quick Start with Plugins

1. **Create an example plugin**:
   ```bash
   xsoar-cli plugins create-example
   ```

2. **List available plugins**:
   ```bash
   xsoar-cli plugins list
   ```

3. **Test the example plugin**:
   ```bash
   xsoar-cli example hello --name "World"
   ```

### Plugin Management Commands

- `xsoar-cli plugins list` - List all plugins
- `xsoar-cli plugins info <plugin>` - Show plugin information
- `xsoar-cli plugins validate` - Validate all plugins
- `xsoar-cli plugins reload <plugin>` - Reload a specific plugin
- `xsoar-cli plugins create-example` - Create an example plugin
- `xsoar-cli plugins open` - Open the plugins directory

### Creating Your Own Plugins

Create a Python file in `~/.local/xsoar-cli/plugins/` that inherits from `XSOARPlugin`:

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

    def get_command(self) -> click.Command:
        @click.command(help="My custom command")
        def mycommand():
            click.echo("Hello from my plugin!")
        return mycommand
```

For detailed documentation, see [Plugin System Documentation](src/xsoar_cli/plugins/README.md).

## License

`xsoar-cli` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
