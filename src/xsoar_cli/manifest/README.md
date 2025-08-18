# Manifest

## Validate
Verifies that the xsoar_config.json manifest is valid JSON. Does a HTTP HEAD calls to every upstream content pack defined. Checks
custom content pack availability in AWS S3 artefact repository.
```
xsoar-cli manifest validate /my/full/path/to/xsoar_config.json
xsoar-cli manifest validate relative/path/to/xsoar_config.json
```

## Update
Updates and prompts the user to write the xsoar_config.json manifest with the latest available content packs. Both upstream and custom content packs are checked.
```
xsoar-cli manifest update /my/full/path/to/xsoar_config.json
xsoar-cli manifest update relative/path/to/xsoar_config.json
```

## Diff
Queries the XSOAR server for installed packages and compares them to what is defined in the manifest. Prints out the diff.
```
xsoar-cli manifest diff /my/full/path/to/xsoar_config.json
xsoar-cli manifest diff relative/path/to/xsoar_config.json
```
