# xsoar-cli

![PyPI - Version](https://img.shields.io/pypi/v/xsoar-cli) [![Python](https://img.shields.io/pypi/pyversions/xsoar-cli.svg)](https://pypi.org/project/xsoar-cli/) [![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A command-line interface for managing Palo Alto Networks XSOAR (Cortex XSOAR) that streamlines content development and deployment workflows.

**Key Features:**
- **Content Management**: Validate and deploy content packs with declarative manifests
- **Case Operations**: Retrieve case details and clone cases between environments
- **Playbook Development**: Download playbooks for local editing and testing
- **Dependency Analysis**: Generate visual graphs of content pack dependencies
- **Plugin System**: Extend functionality with custom commands

Perfect for DevOps teams using CI/CD pipelines to manage XSOAR content stored in [content repositories](https://github.com/demisto/content-ci-cd-template).

Pull Requests are very welcome and appreciated! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Quick Start

```bash
# Install
pip install xsoar-cli

# Create configuration file
xsoar-cli config create

# Validate and deploy your content
xsoar-cli manifest validate ./xsoar_config.json
xsoar-cli manifest deploy ./xsoar_config.json

# Get help on available commands
xsoar-cli --help
```

## Important Notes

This CLI tool is made to be run from the root of a content repository. Some commands depend on files located in your content repository or expects a certain directory structure to be available from your currently working directory.

## Requirements

### Core Requirements
- XSOAR servers version 6 or 8
- Python 3.9+ (only tested with Python 3.12, earlier versions may work but are not guaranteed)

### Additional Requirements (depending on usage)
- **AWS SDK for Python (Boto3)** - Only required when working with custom content packs stored in S3. You can use marketplace packs and other functionality without AWS setup.

**Note:** AWS S3 is currently the only available artifacts repository provider for custom packs. Pull requests for new providers are welcome!

## Installation

```bash
pip install xsoar-cli
```

## Upgrading

```bash
pip install --upgrade xsoar-cli
```

## Uninstalling

```bash
pip uninstall xsoar-cli
```

## Configuration

The xsoar-cli config file is located in `~/.config/xsoar-cli/config.json`. To create a configuration file from template, please run:

```bash
xsoar-cli config create
```

### Configuration File Structure

After creating the config file, edit it with your XSOAR server details:

```json
{
    "default_environment": "xsoar6",
    "default_new_case_type": "",
    "custom_pack_authors": ["SOMEONE"],
    "server_config": {
        "xsoar6": {
            "base_url": "https://xsoar-v6.example.com",
            "api_token": "YOUR API TOKEN HERE",
            "artifacts_location": "S3",
            "s3_bucket_name": "xsoar-cicd",
            "verify_ssl": "/path/to/your/CA_bundle.pem",
            "server_version": 6
        },
        "xsoar8": {
            "base_url": "https://xsoar-v8.example.com",
            "api_token": "YOUR API TOKEN HERE",
            "artifacts_location": "S3",
            "s3_bucket_name": "xsoar-cicd-prod",
            "verify_ssl": false,
            "server_version": 8,
            "xsiam_auth_id": 123
        }
    }
}
```

### Configuration Options

- **default_environment**: Which environment to use by default (e.g., "xsoar6")
- **default_new_case_type**: Default case type when creating new cases
- **custom_pack_authors**: List of author names used in your custom content packs. This helps xsoar-cli distinguish between your custom packs and marketplace packs. Use the same values you have in `pack_metadata.json` files.

- **server_config**: Define multiple XSOAR environments (xsoar6, xsoar8, etc.)
  - **base_url**: Your XSOAR server URL
  - **api_token**: API token for authentication (see XSOAR documentation for creating API keys)
  - **artifacts_location**: Where artifacts are stored (currently only "S3" is supported)
  - **s3_bucket_name**: S3 bucket where your custom content packs are stored
  - **verify_ssl**: SSL certificate verification - use `false` for self-signed certificates, or path to CA bundle
  - **server_version**: XSOAR server version (6 or 8)
  - **xsiam_auth_id**: Required for XSOAR 8 (XSIAM) - the authentication ID for API access

### Validation

Test your configuration with:

```bash
xsoar-cli config validate
```

This will verify connectivity to all configured XSOAR environments.

## Usage

```bash
xsoar-cli <command> <sub-command> <args>
```

For information about available commands, run `xsoar-cli` without arguments.

For more information on a specific command execute `xsoar-cli <command> --help`.

### Commands

- **[case](src/xsoar_cli/case/README.md)** - Retrieve case details and clone cases between environments
- **[config](src/xsoar_cli/config/README.md)** - Create, validate, and manage CLI configuration files
- **[graph](src/xsoar_cli/graph/README.md)** - Generate visual dependency graphs for content packs
- **[manifest](src/xsoar_cli/manifest/README.md)** - Validate and deploy content using declarative manifests
- **[pack](src/xsoar_cli/pack/README.md)** - Manage content pack operations and information
- **[playbook](src/xsoar_cli/playbook/README.md)** - Download playbooks for local editing and development
- **[plugins](src/xsoar_cli/plugins/README.md)** - Extend CLI functionality with custom commands

## Plugin System

xsoar-cli supports a plugin system that allows you to extend the CLI with custom commands. For complete documentation, examples, and usage instructions, see [Plugin System Documentation](src/xsoar_cli/plugins/README.md).

## Troubleshooting

### Common Issues

**"Config file not found"**
- Run `xsoar-cli config create` to generate a template configuration file
- Ensure the file exists at `~/.config/xsoar-cli/config.json`

**"Failed to reach pack" or connection errors**
- Verify your XSOAR server URL and API token in the config file
- Check network connectivity to your XSOAR server
- For custom packs: Ensure AWS credentials are configured and S3 bucket is accessible

**"Invalid environment"**
- Check that the environment name matches exactly what's defined in your config file
- Use `xsoar-cli config validate` to verify your configuration

**Python compatibility issues**
- Ensure you're using Python 3.9 or later
- Consider using Python 3.12 for best compatibility

## Contributing

We welcome all contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines on how to contribute to this project.

## License

`xsoar-cli` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
