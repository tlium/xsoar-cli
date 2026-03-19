# Config

Create, validate, and manage CLI configuration.

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

Validate the configuration file and test connectivity. By default, tests only the default environment (both XSOAR server connectivity and artifacts repository if configured).

**Syntax:** `xsoar-cli config validate [OPTIONS]`

**Options:**
- `--connectivity-only` - Only test XSOAR server connectivity, skip artifacts repository check
- `--all` - Test all configured environments (mutually exclusive with `--only-test-environment`)
- `--only-test-environment TEXT` - Test connectivity for only the specified environment (mutually exclusive with `--all`)
- `-v`, `--verbose` - Show error details on validation failure

**Examples:**
```
# Test default environment (XSOAR connectivity and artifacts)
xsoar-cli config validate

# Test default environment, XSOAR connectivity only
xsoar-cli config validate --connectivity-only

# Test all configured environments
xsoar-cli config validate --all

# Test all configured environments, XSOAR connectivity only
xsoar-cli config validate --all --connectivity-only

# Test a specific environment
xsoar-cli config validate --only-test-environment prod

# Test a specific environment, XSOAR connectivity only
xsoar-cli config validate --only-test-environment prod --connectivity-only

# Show error details on failure
xsoar-cli config validate --verbose
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

## Set Azure Token

Set the Azure Blob Storage SAS token for an environment in the configuration file.

**Syntax:** `xsoar-cli config set-azure-token [OPTIONS] SASTOKEN`

**Options:**
- `--environment TEXT` - Target environment (default: dev)

**Arguments:**
- `SASTOKEN` - The SAS token to set for the environment

**Examples:**
```
xsoar-cli config set-azure-token my-sas-token
xsoar-cli config set-azure-token --environment prod my-sas-token
```
