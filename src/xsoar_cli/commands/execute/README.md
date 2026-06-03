# Execute

Execute scripts, integration commands, and playbooks against an XSOAR investigation.

By default, execution happens in the user's playground. Pass `--case-id` to run against a specific case instead.

> Note: `execute playbook` is not yet implemented. The command and options are in
> place, but the underlying API call currently raises `NotImplementedError`.

## Command

Execute an automation script or integration command. There is no difference in how scripts and integration commands are invoked.

Use the bare command or script name, the same way you would reference it in a playbook. A leading `!` is accepted but optional.

Arguments are supplied as space-separated `key=value` pairs. Values containing whitespace are quoted automatically. A malformed argument (one without a `=`) causes the command to exit with an error.

**Shell note:** interactive shells (zsh, bash) treat characters like `!` and `|` specially. Prefer omitting the `!`, and wrap argument values in single quotes when they contain shell metacharacters, for example `query='index=zscaler | head 1'`.

**Syntax:** `xsoar-cli execute command [OPTIONS] NAME [ARGS]...`

**Options:**
- `--environment TEXT` - Target environment (default: uses default environment from config)
- `--case-id INTEGER` - Case ID to execute against (default: the user's playground)
- `--mode [sync|async]` - Wait for results (`sync`) or submit and return the created entry (`async`) (default: "sync")
- `--output-level [summary|raw]` - Amount of detail to include in the output (default: "summary")

**Arguments:**
- `NAME` - The script or integration command to run
- `ARGS` - Zero or more `key=value` argument pairs

**Output:**
- `summary` (default) prints the readable contents of each returned War Room entry, with a direct link to each entry.
- `raw` prints the full result as JSON, suitable for scripting and piping.

**Examples:**
```
xsoar-cli execute command MyScript arg1=val1 arg2=val2
xsoar-cli execute command whois query=example.com --case-id 12345
xsoar-cli execute command splunk-search query='index=zscaler | head 1'
xsoar-cli execute command MyScript arg1=val1 --mode async
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
