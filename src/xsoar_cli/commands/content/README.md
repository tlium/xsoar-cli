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
