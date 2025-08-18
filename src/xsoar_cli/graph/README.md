# Graph
BETA command. Under active development.

## Generate
Creates a graph representation of the entire content repository and plots connected components. The syntax is `xsoar-cli graph generate [OPTIONS] [PACKS]...`
where the only required option is the path to the content repository. An optional PACKS argument can be specified with the paths of one or more content packs
you want to be plotted.

### Example invocations
```
# Plot the connected components from the graph of the entire content repository
xsoar-cli graph generate -rp ./content_repo
# Plot only the components found in MyFirstPack
xsoar-cli graph generate -rp ./content_repo ./content_repo/Packs/MyFirstPack
# Plot only connected components from MyFirstPack and MySecondPack
xsoar-cli graph generate -rp ./content_repo ./content_repo/Packs/MyFirstPack ./content_repo/Packs/MySecondPack
```
