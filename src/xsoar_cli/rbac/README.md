# RBAC

Dump roles, users and user groups.

## Get Roles

Dump all roles configured in your XSOAR environment. Output is JSON formatted with 4-space indentation.

**Syntax:** `xsoar-cli rbac getroles [OPTIONS]`

**Options:**
- `--environment TEXT` - Target environment (default: uses default environment from config)

**Examples:**
```
xsoar-cli rbac getroles
xsoar-cli rbac getroles --environment prod
```

## Get Users

Dump all users configured in your XSOAR environment. Output is JSON formatted with 4-space indentation.

**Syntax:** `xsoar-cli rbac getusers [OPTIONS]`

**Options:**
- `--environment TEXT` - Target environment (default: uses default environment from config)

**Examples:**
```
xsoar-cli rbac getusers
xsoar-cli rbac getusers --environment prod
```

## Get User Groups

Dump all user groups configured in your XSOAR environment. XSOAR 8+ only. Output is JSON formatted with 4-space indentation.

**Syntax:** `xsoar-cli rbac getusergroups [OPTIONS]`

**Options:**
- `--environment TEXT` - Target environment (default: uses default environment from config)

**Examples:**
```
xsoar-cli rbac getusergroups
xsoar-cli rbac getusergroups --environment prod
```
