# Content

Inspect and manage content items on your XSOAR server.

## Get Detached

List detached content items. Detached items are content items that are not associated with any installed content pack. Output is JSON formatted with 4-space indentation.

**Syntax:** `xsoar-cli content get-detached [OPTIONS]`

**Options:**
- `--environment TEXT` - Target environment (default: uses default environment from config)
- `--type [scripts|playbooks|all]` - Type of content items to retrieve (default: all)

**Examples:**
```
xsoar-cli content get-detached
xsoar-cli content get-detached --environment prod
xsoar-cli content get-detached --type scripts
xsoar-cli content get-detached --type playbooks --environment dev
```

## List

List available content items. Enumerates commands, playbooks and scripts available on the server. Output is JSON formatted with 4-space indentation.

**Syntax:** `xsoar-cli content list [OPTIONS]`

**Options:**
- `--environment TEXT` - Target environment (default: uses default environment from config)
- `--type [scripts|playbooks|commands|all]` - Type of content items to list (default: all)

**Examples:**
```
xsoar-cli content list
xsoar-cli content list --environment prod
xsoar-cli content list --type commands
xsoar-cli content list --type playbooks --environment dev
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
