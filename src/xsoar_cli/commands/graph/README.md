# Graph

BETA command. Generate visual dependency graphs for content packs. All examples below assume the commands are run from the root of the content repository.

## Generate

Create a dependency graph for the content repository and plot connected components. If no packs are specified, a graph is created for all packs in the repository.

**Syntax:** `xsoar-cli graph generate [OPTIONS] [PACKS]...`

**Options:**
- `--environment TEXT` - Target environment (default: uses default environment from config)
- `-rp, --repo-path PATH` - Path to content repository (required)
- `-urp, --upstream-repo-path PATH` - Path to local clone of Palo Alto content repository

**Arguments:**
- `PACKS` - One or more paths to content packs to include in the graph (optional)

**Examples:**
```
xsoar-cli graph generate -rp .
xsoar-cli graph generate -rp . Packs/MyFirstPack
xsoar-cli graph generate -rp . Packs/MyFirstPack Packs/MySecondPack
```

## Export

Export a dependency graph to a file. Supports GML and GraphML formats. If no packs are specified, a graph is created for all packs in the repository.

**Syntax:** `xsoar-cli graph export [OPTIONS] [PACKS]...`

**Options:**
- `--environment TEXT` - Target environment (default: uses default environment from config)
- `-rp, --repo-path PATH` - Path to content repository (required)
- `-urp, --upstream-repo-path PATH` - Path to local clone of Palo Alto content repository
- `-o, --output-path PATH` - Path to output directory (required)
- `-of, --output-format [GML|GraphML]` - File format for the exported graph (default: GML)

**Arguments:**
- `PACKS` - One or more paths to content packs to include in the graph (optional)

**Examples:**
```
xsoar-cli graph export -rp . -o /tmp
xsoar-cli graph export -rp . -o /tmp -of GraphML
xsoar-cli graph export -rp . -o /tmp Packs/MyFirstPack Packs/MySecondPack
```
