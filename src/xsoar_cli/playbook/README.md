# Playbook

## Download
**This command requires a content repository-like directory structure in the current working directory**
It attempts to provide a smoother development experience when modifying playbooks by doing the following steps:
1. download the playbook. Attempts to detect the proper content pack and outputs the file to $(cwd)/Packs/PackID/Playbooks/<playbook name>.yml
2. run demisto-sdk format --assume-yes --no-validate --no-graph <playbook_name.yml>
3. re-attach the downloaded playbook in XSOAR
Whitespace characters in Pack ID and Playbook name will be converted to underscores "_".

### Current limitations
- This command only supports downloading playbooks which are already part of a content pack. Proper implementation on completely new
playbooks is yet to be implemented.
- Attempting to download a non-existing playbook will result in a 500 Internal Server Error

#### Example invocation:
```
xsoar-cli playbook download "my awesome playbook.yml"
```
