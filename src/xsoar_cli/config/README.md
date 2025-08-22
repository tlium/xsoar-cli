# Config

Configuration management commands for XSOAR CLI.

## Create

Create a new configuration file based on a template. If the configuration file already exists, prompts for confirmation to overwrite.

**Syntax:** `xsoar-cli config create`

**Examples:**
```
xsoar-cli config create
```

## Show

Display the current configuration file contents as formatted JSON. API keys are masked by default for security.

**Syntax:** `xsoar-cli config show [OPTIONS]`

**Options:**
- `--unmask` - Show unmasked API keys in output

**Examples:**
```
xsoar-cli config show
xsoar-cli config show --unmask
```

## Validate

Validate that the configuration file is properly formatted JSON and test connectivity to each XSOAR environment defined in the configuration.

**Syntax:** `xsoar-cli config validate [OPTIONS]`

**Options:**
- `--only-test-environment TEXT` - Test connectivity for only the specified environment

**Examples:**
```
xsoar-cli config validate
xsoar-cli config validate --only-test-environment prod
```

## Set Credentials

Update API credentials for a specific environment in the configuration file. Automatically sets server version based on whether a key ID is provided.

**Syntax:** `xsoar-cli config set-credentials [OPTIONS] APITOKEN`

**Options:**
- `--environment TEXT` - Target environment (default: dev)
- `--key_id INTEGER` - API key ID for XSOAR 8 (sets server_version to 8, omit for XSOAR 6)

**Arguments:**
- `APITOKEN` - The API token to set for the environment

**Examples:**
```
xsoar-cli config set-credentials your-api-token-here
xsoar-cli config set-credentials --environment prod your-api-token-here
xsoar-cli config set-credentials --environment prod --key_id 123 your-api-token-here
```
