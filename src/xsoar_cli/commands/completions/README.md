# Completions

Install and manage shell completion for xsoar-cli. Supports Bash, Zsh (including Oh My Zsh), and Fish.

## Install

Generate and install the shell completion script. The target shell is auto-detected from `$SHELL` if not specified.

For Zsh, the install location is determined automatically:
- **Oh My Zsh**: `$ZSH_CUSTOM/completions/_xsoar-cli`
- **Plain Zsh**: `~/.zfunc/_xsoar-cli`

**Syntax:** `xsoar-cli completions install [OPTIONS]`

**Options:**
- `--shell [bash|zsh|fish]` - Target shell. Auto-detected from `$SHELL` if not specified.

**Examples:**
```
# Auto-detect shell
xsoar-cli completions install

# Specify shell explicitly
xsoar-cli completions install --shell zsh
xsoar-cli completions install --shell bash
xsoar-cli completions install --shell fish
```

Regenerate completions after upgrading xsoar-cli by running the same command again.

## Uninstall

Remove a previously installed completion script. Uses the same detection logic as `install` to locate the file.

**Syntax:** `xsoar-cli completions uninstall [OPTIONS]`

**Options:**
- `--shell [bash|zsh|fish]` - Target shell. Auto-detected from `$SHELL` if not specified.

**Examples:**
```
# Auto-detect shell
xsoar-cli completions uninstall

# Specify shell explicitly
xsoar-cli completions uninstall --shell zsh
```
