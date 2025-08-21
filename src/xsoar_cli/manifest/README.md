# Manifest Commands

The manifest commands help you manage XSOAR content pack deployments using a declarative configuration file (`xsoar_config.json`). This file defines which content packs should be installed on your XSOAR server and their specific versions.

## Prerequisites

- Valid XSOAR CLI configuration file (`~/.config/xsoar-cli/config.json`)
- Access to XSOAR server API
- For custom packs: AWS S3 credentials configured (AWS S3 is currently the only supported artifacts repository provider)
- Content repository with proper directory structure

## Manifest File Structure

The `xsoar_config.json` file contains two main sections:

```json
{
    "custom_packs": [
        {
            "id": "MyCustomPack",
            "version": "1.0.0",
            "_comment": "Optional comment for documentation"
        }
    ],
    "marketplace_packs": [
        {
            "id": "CommonScripts", 
            "version": "1.20.0"
        }
    ]
}
```

- **custom_packs**: Content packs developed by your organization, stored in AWS S3 (currently the only supported artifacts repository provider; pull requests for new providers are welcome!)
- **marketplace_packs**: Official Palo Alto Networks content packs from the marketplace
- **_comment**: Optional field for documentation/notes about specific pack versions

## Commands

### validate
Validates the manifest file and verifies all specified content packs are available.

**Usage:**
```bash
xsoar-cli manifest validate [OPTIONS] MANIFEST_PATH
```

**Options:**
- `--environment TEXT`: Environment name from config file (default: dev)

**Examples:**
```bash
# Validate manifest in current directory
xsoar-cli manifest validate ./xsoar_config.json

# Validate with specific environment
xsoar-cli manifest validate --environment prod ./xsoar_config.json
```

**What it checks:**
- JSON syntax validity
- Custom pack availability in S3 artifact repository
- Marketplace pack availability via HTTP connectivity
- Local pack metadata consistency for new packs in development

**Sample output:**
```
Manifest is valid JSON
Checking custom_packs availability ........................done.
Checking marketplace_packs availability ........................done.
Manifest is valid JSON and all packs are reachable.
```

### update
Compares installed packs against available versions and updates the manifest with latest versions.

**Usage:**
```bash
xsoar-cli manifest update [OPTIONS] MANIFEST_PATH
```

**Options:**
- `--environment TEXT`: Environment name from config file (default: dev)

**Examples:**
```bash
# Update manifest with latest versions
xsoar-cli manifest update ./xsoar_config.json

# Interactive prompts for each pack upgrade
xsoar-cli manifest update --environment staging ./xsoar_config.json
```

**Behavior:**
- Queries XSOAR server for outdated packs
- Displays upgrade candidates in tabular format
- Prompts for confirmation on each upgrade
- Preserves `_comment` fields but shows warnings
- Updates manifest file on disk

**Sample output:**
```
Fetching outdated packs from XSOAR server. This may take a minute...done.
Pack ID                                           Installed version   Latest available version
CommonScripts                                     1.19.0              1.20.0              
Base                                              1.40.14             1.41.14             
Total number of outdated content packs: 2
Upgrade CommonScripts from 1.19.0 to 1.20.0? [Y/n]: y
Upgrade Base from 1.40.14 to 1.41.14? [Y/n]: y
Written updated manifest to './xsoar_config.json'
```

### diff
Compares the manifest definition against what's actually installed on the XSOAR server.

**Usage:**
```bash
xsoar-cli manifest diff [OPTIONS] MANIFEST_PATH
```

**Options:**
- `--environment TEXT`: Environment name from config file (default: dev)

**Examples:**
```bash
# Show differences between manifest and server
xsoar-cli manifest diff ./xsoar_config.json

# Check production environment
xsoar-cli manifest diff --environment prod ./xsoar_config.json
```

**Output shows:**
- Packs defined in manifest but not installed
- Version mismatches between manifest and installed packs
- Summary message when everything is up to date

**Sample output:**
```
Pack MyCustomPack is not installed
Manifest states CommonScripts version 1.20.0 but version 1.19.0 is installed
```

### deploy
Installs or updates content packs on the XSOAR server according to the manifest.

**Usage:**
```bash
xsoar-cli manifest deploy [OPTIONS] MANIFEST_PATH
```

**Options:**
- `--environment TEXT`: Environment name from config file (default: dev)
- `--verbose`: Show detailed information about skipped packs
- `--yes`: Skip confirmation prompt

**Examples:**
```bash
# Deploy with confirmation prompt
xsoar-cli manifest deploy ./xsoar_config.json

# Deploy to production without prompts
xsoar-cli manifest deploy --environment prod --yes ./xsoar_config.json

# Deploy with verbose output
xsoar-cli manifest deploy --verbose ./xsoar_config.json
```

**Behavior:**
- Prompts for confirmation before deployment (unless --yes used)
- Only installs/updates packs that differ from current installation
- Shows progress for each pack installation
- Skips packs already at correct version

**Sample output:**
```
WARNING: this operation will attempt to deploy all packs defined in the manifest to XSOAR dev environment. Continue? [y/N]: y
Fetching installed packs...done.
Installing MyCustomPack version 1.0.0...OK.
Installing CommonScripts version 1.20.0...OK.
Not installing Base version 1.41.14. Already installed.
```

## Common Workflows

### Initial Setup
1. Create manifest: `xsoar-cli manifest validate ./xsoar_config.json` (validates structure)
2. Deploy: `xsoar-cli manifest deploy ./xsoar_config.json`

### Regular Updates
1. Check for updates: `xsoar-cli manifest update ./xsoar_config.json`
2. Review changes in manifest file
3. Deploy updates: `xsoar-cli manifest deploy ./xsoar_config.json`

### Environment Consistency
1. Check differences: `xsoar-cli manifest diff --environment prod ./xsoar_config.json`
2. Deploy if needed: `xsoar-cli manifest deploy --environment prod ./xsoar_config.json`

### CI/CD Pipeline Integration
```bash
# Typical CI/CD workflow
xsoar-cli manifest validate ./xsoar_config.json    # Fail fast on invalid manifest
xsoar-cli manifest diff --environment dev ./xsoar_config.json  # Show what will change
xsoar-cli manifest deploy --yes --environment dev ./xsoar_config.json  # Deploy changes
```

## Troubleshooting

### Common Issues

**"Failed to decode JSON in {filepath}"**
- Check JSON syntax in manifest file
- Ensure no trailing commas or missing quotes
- Use a JSON validator to identify syntax errors

**"Failed to reach pack {pack_id} version {version}"**
- **For custom packs**: Check AWS S3 credentials and bucket access
- **For marketplace packs**: Verify internet connectivity to Palo Alto Networks CDN
- Ensure pack version exists in the artifact repository
- Check if pack is in development locally (may not be uploaded yet)

**"Pack {pack_id} not found in manifest"**
- Verify pack ID matches exactly (case-sensitive)
- Check that pack is in correct section (`custom_packs` vs `marketplace_packs`)
- Ensure pack ID in manifest matches the ID in pack metadata

**"Environment not found"**
- Check config file exists: `~/.config/xsoar-cli/config.json`
- Verify environment name matches configuration exactly
- Run `xsoar-cli config create` if configuration is missing
- Check server connectivity and API credentials

**"WARNING: comment found in manifest for {pack_id}: {comment}"**
- This is informational only - comments are preserved during updates
- Review the comment to understand why the version was pinned
- Decide whether to accept or decline the upgrade based on the comment

### Performance Considerations

- **Large manifests**: Commands may take several minutes with 100+ packs
- **Network timeouts**: Custom pack validation requires S3 connectivity
- **Rate limiting**: XSOAR API calls are rate-limited; large deployments may be slower

### Best Practices

1. **Version Control**: Keep `xsoar_config.json` in version control
2. **Comments**: Use `_comment` field to document version pin reasons
3. **Testing**: Always validate before deploying to production
4. **Environment Separation**: Consider different manifests for dev/staging/prod
5. **Backup**: Run `diff` before `deploy` to understand changes
6. **Incremental Updates**: Update and deploy frequently rather than large batch updates
7. **Monitoring**: Check deployment results and verify pack functionality after updates

### Development Workflow

When developing new custom packs:

1. Add pack to manifest with new version
2. Run `xsoar-cli manifest validate` - may show pack not available (expected)
3. The validation will pass if local pack metadata matches manifest version
4. Deploy pack artifacts to S3 repository
5. Run `xsoar-cli manifest deploy` to install on XSOAR server

### Security Notes

- AWS credentials should be configured securely (IAM roles, not hardcoded keys)
- XSOAR API keys should be stored in the configuration file with appropriate permissions
- Consider using different credentials for different environments
- Review pack sources and content before deploying to production systems