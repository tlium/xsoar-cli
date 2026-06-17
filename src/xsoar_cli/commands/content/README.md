# Content

Inspect and manage content items on your XSOAR server.

## Get Detached

List detached content items. Detached items are content items that have been modified on the server and are no longer in sync with the installed content pack.

The output is a human-readable summary: a count followed by one line per item in the form `<name> (ID: <id>)`. When no detached items are found, the output is `No detached <type> found` (for example `No detached scripts found`). This applies to both `--type scripts` and `--type playbooks`.

**Syntax:** `xsoar-cli content get-detached [OPTIONS]`

**Options:**
- `--environment TEXT` - Target environment (default: uses default environment from config)
- `--type [scripts|playbooks|all]` - Type of content items to retrieve (required)

**Examples:**
```
xsoar-cli content get-detached --type scripts
xsoar-cli content get-detached --type playbooks
xsoar-cli content get-detached --type all
xsoar-cli content get-detached --type scripts --environment prod
```

## List

List available content items. Enumerates commands, playbooks and scripts available on the server. Designed for discovery: a quick, scannable overview of what content exists, primarily to help humans and AI agents identify relevant items before working with them.

By default the output is a human-readable table. Use `--output-format json` for machine-readable output, or `--output-format plain` for tab-separated values that are easy to pipe to tools like `grep`.

**Syntax:** `xsoar-cli content list [OPTIONS]`

**Options:**
- `--environment TEXT` - Target environment (default: uses default environment from config)
- `--type [scripts|playbooks|commands|all]` - Type of content items to list (default: all)
- `--search TEXT` - Case-insensitive substring filter on item id, name, and description
- `--output-format [table|json|plain]` - Output format (default: table)

**Examples:**
```
xsoar-cli content list
xsoar-cli content list --environment prod
xsoar-cli content list --type commands
xsoar-cli content list --type commands --search slack
xsoar-cli content list --type commands --output-format json
xsoar-cli content list --type scripts --output-format plain
xsoar-cli content list --type playbooks --environment dev
```

## Describe

Describe a single content item in detail. Looks up one script, playbook, or command by name and shows its description, arguments, and inputs/outputs. Commands also show the integration brand and its configured instances (name and state). Use this after `content list` to get the detail needed to actually use an item.

The lookup is case-insensitive. Scripts match on id, playbooks match on id or name (so a custom playbook with a UUID id resolves by its human-readable name), and commands match on the command name.

**Syntax:** `xsoar-cli content describe --type TYPE NAME`

**Options:**
- `--environment TEXT` - Target environment (default: uses default environment from config)
- `--type [script|playbook|command]` - Type of content item to describe (required)
- `--output-format [table|json]` - Output format (default: table)

**Examples:**
```
xsoar-cli content describe --type command servicenow-get-record
xsoar-cli content describe --type script AddDNBHostIndicatorToCase
xsoar-cli content describe --type playbook "Phishing Investigation - Generic v2"
xsoar-cli content describe --type command servicenow-get-record --output-format json
```

## Download

Download a content item by name from the XSOAR server.

Some content types (layouts, playbooks) are easier to create and modify directly in the XSOAR UI rather than by hand. The intended workflow is to make changes in the UI, then download the updated item to overwrite the local file in the content repository. Since the repository is tracked in Git, no information is lost on overwrite.

The command resolves the content item's pack ID and writes the file to the appropriate location under `Packs/<pack_id>/`. If the target directory does not exist, you are offered the option to save to the current working directory instead. If the target file does not already exist, you are prompted for confirmation before writing. Existing files are overwritten silently.

**Syntax:** `xsoar-cli content download --type TYPE NAME`

**Options:**
- `--environment TEXT` - Target environment (default: uses default environment from config)
- `--type [playbook|layout]` - Type of content item to download (required)
- `--output PATH` - Path to the content repository root. Defaults to current working directory. Useful when running xsoar-cli from outside the content repository.

**Arguments:**
- `NAME` - Display name of the content item to download

**Output files:**
- Playbooks: `Packs/<pack_id>/Playbooks/<name>.yml`
- Layouts: `Packs/<pack_id>/Layouts/layoutscontainer-<name>.json`

Spaces in names are replaced with underscores in filenames.

**Examples:**
```
xsoar-cli content download --type playbook "AWS GuardDuty"
xsoar-cli content download --type layout "Incident Layout" --environment prod
xsoar-cli content download --type playbook "My Playbook" --output /path/to/content-repo
```
