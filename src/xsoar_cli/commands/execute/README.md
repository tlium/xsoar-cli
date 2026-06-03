# Execute

Execute scripts, integration commands, and playbooks against an XSOAR investigation.

By default, execution happens in the user's playground. Pass `--case-id` to run against a specific case instead.

> Note: the execution layer is not yet implemented. The commands and options are
> in place, but the underlying API calls currently raise `NotImplementedError`.

## Command

Execute an automation script or integration command. There is no difference in how scripts and integration commands are invoked.

Arguments are supplied as space-separated `key=value` pairs. A malformed argument (one without a `=`) causes the command to exit with an error.

**Syntax:** `xsoar-cli execute command [OPTIONS] NAME [ARGS]...`

**Options:**
- `--environment TEXT` - Target environment (default: uses default environment from config)
- `--case-id INTEGER` - Case ID to execute against (default: the user's playground)
- `--output-level [summary|raw]` - Amount of detail to include in the output (default: "summary")

**Arguments:**
- `NAME` - The script or integration command to run
- `ARGS` - Zero or more `key=value` argument pairs

**Examples:**
```
xsoar-cli execute command MyScript arg1=val1 arg2=val2
xsoar-cli execute command !whois query=example.com --case-id 12345
xsoar-cli execute command MyScript arg1=val1 --output-level raw
```

## Playbook

Execute a playbook.

**Syntax:** `xsoar-cli execute playbook [OPTIONS] NAME`

**Options:**
- `--environment TEXT` - Target environment (default: uses default environment from config)
- `--case-id INTEGER` - Case ID to execute against (default: the user's playground)
- `--output-level [summary|raw]` - Amount of detail to include in the output (default: "summary")

**Arguments:**
- `NAME` - The playbook to run

**Examples:**
```
xsoar-cli execute playbook "My Playbook"
xsoar-cli execute playbook "My Playbook" --case-id 12345
```
