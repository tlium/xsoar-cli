"""
Advanced XSOAR CLI Plugin Example

This plugin demonstrates advanced features including:
- Multiple command groups
- XSOAR client integration
- Configuration access
- Error handling
- File operations
- Custom options and arguments

To use this plugin:
1. Copy this file to ~/.local/xsoar-cli/plugins/advanced_plugin.py
2. Run: xsoar-cli plugins list
3. Use commands like: xsoar-cli advanced cases list
"""

import json
from pathlib import Path
from typing import Optional

import click


class AdvancedPlugin(XSOARPlugin):
    """Advanced plugin demonstrating various features."""

    @property
    def name(self) -> str:
        return "advanced"

    @property
    def version(self) -> str:
        return "2.0.0"

    @property
    def description(self) -> str:
        return "Advanced plugin demonstrating XSOAR integration and complex commands"

    def get_command(self) -> click.Command:
        """Return the main command group for this plugin."""

        @click.group(help="Advanced XSOAR operations")
        @click.pass_context
        def advanced(ctx: click.Context):
            """Main command group for advanced plugin."""
            # Store plugin instance in context for subcommands
            ctx.ensure_object(dict)
            ctx.obj["plugin"] = self

        # Case management commands
        @click.group(help="Case management operations")
        def cases():
            """Case management commands."""

        @click.command(help="List recent cases")
        @click.option("--limit", default=10, help="Number of cases to show")
        @click.option("--environment", default="dev", help="Environment to query")
        @click.option("--output", "-o", type=click.Path(), help="Save output to file")
        @click.pass_context
        def list_cases(ctx: click.Context, limit: int, environment: str, output: Optional[str]):
            """List recent cases from XSOAR."""
            try:
                # This would require the @load_config decorator in a real implementation
                click.echo(f"Fetching {limit} recent cases from {environment} environment...")

                # Simulated case data (in real plugin, this would use XSOAR client)
                cases_data = [{"id": f"case_{i}", "name": f"Case {i}", "severity": "Medium"} for i in range(1, limit + 1)]

                if output:
                    output_path = Path(output)
                    output_path.write_text(json.dumps(cases_data, indent=2))
                    click.echo(f"✅ Saved {len(cases_data)} cases to {output_path}")
                else:
                    click.echo(f"Found {len(cases_data)} cases:")
                    for case in cases_data:
                        click.echo(f"  • {case['id']}: {case['name']} ({case['severity']})")

            except Exception as e:
                click.echo(f"❌ Error fetching cases: {e}", err=True)
                raise click.Abort()

        @click.command(help="Create a test case")
        @click.option("--name", prompt="Case name", help="Name for the new case")
        @click.option("--description", default="Test case created by advanced plugin")
        @click.option("--severity", type=click.Choice(["Low", "Medium", "High", "Critical"]), default="Medium")
        @click.option("--environment", default="dev", help="Environment to create case in")
        @click.confirmation_option(prompt="Are you sure you want to create this case?")
        def create_case(name: str, description: str, severity: str, environment: str):
            """Create a new test case in XSOAR."""
            try:
                click.echo(f"Creating case '{name}' in {environment}...")

                # Simulated case creation (in real plugin, this would use XSOAR client)
                case_id = f"TEST_{hash(name) % 10000}"

                click.echo(f"✅ Created case {case_id}")
                click.echo(f"   Name: {name}")
                click.echo(f"   Description: {description}")
                click.echo(f"   Severity: {severity}")
                click.echo(f"   Environment: {environment}")

            except Exception as e:
                click.echo(f"❌ Error creating case: {e}", err=True)
                raise click.Abort()

        # Utility commands
        @click.group(help="Utility operations")
        def utils():
            """Utility commands."""

        @click.command(help="Analyze a log file")
        @click.argument("log_file", type=click.Path(exists=True))
        @click.option("--pattern", help="Search pattern")
        @click.option("--lines", default=100, help="Number of lines to analyze")
        def analyze_log(log_file: str, pattern: Optional[str], lines: int):
            """Analyze a log file for patterns."""
            try:
                log_path = Path(log_file)
                click.echo(f"Analyzing log file: {log_path}")

                with log_path.open("r") as f:
                    log_lines = f.readlines()[:lines]

                total_lines = len(log_lines)
                click.echo(f"Analyzing {total_lines} lines...")

                if pattern:
                    matching_lines = [line for line in log_lines if pattern in line]
                    click.echo(f"Found {len(matching_lines)} lines matching '{pattern}':")
                    for i, line in enumerate(matching_lines[:10], 1):
                        click.echo(f"  {i:2d}: {line.strip()}")
                    if len(matching_lines) > 10:
                        click.echo(f"  ... and {len(matching_lines) - 10} more")
                else:
                    error_keywords = ["error", "exception", "failed", "critical"]
                    error_lines = [line for line in log_lines if any(keyword in line.lower() for keyword in error_keywords)]
                    click.echo(f"Found {len(error_lines)} potential error lines:")
                    for i, line in enumerate(error_lines[:5], 1):
                        click.echo(f"  {i:2d}: {line.strip()}")

            except Exception as e:
                click.echo(f"❌ Error analyzing log: {e}", err=True)
                raise click.Abort()

        @click.command(help="Generate a plugin template")
        @click.argument("plugin_name")
        @click.option("--output-dir", default=".", help="Output directory")
        def generate_template(plugin_name: str, output_dir: str):
            """Generate a new plugin template."""
            try:
                output_path = Path(output_dir) / f"{plugin_name}_plugin.py"

                if output_path.exists():
                    click.confirm(f"File {output_path} exists. Overwrite?", abort=True)

                template = f'''"""
{plugin_name.title()} XSOAR CLI Plugin

Auto-generated plugin template.
"""

import click


class {plugin_name.title()}Plugin(XSOARPlugin):
    """Custom plugin for {plugin_name} operations."""

    @property
    def name(self) -> str:
        return "{plugin_name.lower()}"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Custom plugin for {plugin_name} operations"

    def get_command(self) -> click.Command:
        @click.group(help="{plugin_name.title()} operations")
        def {plugin_name.lower()}():
            pass

        @click.command(help="Example command")
        @click.option("--param", help="Example parameter")
        def example(param: str):
            click.echo(f"Hello from {plugin_name} plugin!")
            if param:
                click.echo(f"Parameter: {{param}}")

        {plugin_name.lower()}.add_command(example)
        return {plugin_name.lower()}

    def initialize(self):
        click.echo("{plugin_name.title()} plugin initialized!")
'''

                output_path.write_text(template)
                click.echo(f"✅ Generated plugin template: {output_path}")
                click.echo("To use: Copy to ~/.local/xsoar-cli/plugins/ and run 'xsoar-cli plugins list'")

            except Exception as e:
                click.echo(f"❌ Error generating template: {e}", err=True)
                raise click.Abort()

        # Statistics and reporting
        @click.command(help="Show plugin statistics")
        @click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
        def stats(verbose: bool):
            """Show statistics about this plugin."""
            click.echo("Advanced Plugin Statistics")
            click.echo("=" * 30)
            click.echo(f"Plugin: {self.name}")
            click.echo(f"Version: {self.version}")
            click.echo(f"Description: {self.description}")

            if verbose:
                click.echo("\nAvailable Commands:")
                click.echo("  • cases list - List recent cases")
                click.echo("  • cases create - Create a test case")
                click.echo("  • utils analyze-log - Analyze log files")
                click.echo("  • utils generate-template - Generate plugin templates")
                click.echo("  • stats - Show this information")

                click.echo("\nFeatures Demonstrated:")
                click.echo("  ✓ Command groups and subcommands")
                click.echo("  ✓ Options with validation")
                click.echo("  ✓ File operations")
                click.echo("  ✓ Error handling")
                click.echo("  ✓ Interactive prompts")
                click.echo("  ✓ Confirmation dialogs")

        # Add commands to groups
        cases.add_command(list_cases, name="list")
        cases.add_command(create_case, name="create")

        utils.add_command(analyze_log, name="analyze-log")
        utils.add_command(generate_template, name="generate-template")

        # Add groups and commands to main group
        advanced.add_command(cases)
        advanced.add_command(utils)
        advanced.add_command(stats)

        return advanced

    def initialize(self):
        """Initialize the plugin."""
        click.echo("Advanced plugin initialized! 🚀")

    def cleanup(self):
        """Cleanup plugin resources."""
        click.echo("Advanced plugin cleaned up! 👋")
