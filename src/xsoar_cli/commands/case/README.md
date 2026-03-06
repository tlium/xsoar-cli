# Case

Create, retrieve, and clone cases between environments.

## Get

Retrieve basic information about a single case. Output is JSON formatted with 4-space indentation.

**Syntax:** `xsoar-cli case get [OPTIONS] CASENUMBER`

**Options:**
- `--environment TEXT` - Target environment (default: uses default environment from config)

**Examples:**
```
xsoar-cli case get 312412
xsoar-cli case get --environment prod 312412
```

## Clone

Clone a case from one environment to another. Useful for copying production cases to development environment for testing.

**Syntax:** `xsoar-cli case clone [OPTIONS] CASENUMBER`

**Options:**
- `--source TEXT` - Source environment (required)
- `--dest TEXT` - Destination environment (required)

**Examples:**
```
xsoar-cli case clone --source prod --dest dev 312412
xsoar-cli case clone --source dev --dest prod 312412
```

## Create

Create a new case in XSOAR with optional custom fields and case type.

**Syntax:** `xsoar-cli case create [OPTIONS] [NAME] [DETAILS]`

**Options:**
- `--environment TEXT` - Target environment (default: uses default environment from config)
- `--casetype TEXT` - Case type (default: uses default case type from config)
- `--custom-fields TEXT` - Additional fields in format "field1=value1,field2=value2" (useful when XSOAR has mandatory custom case fields configured)
- `--custom-fields-delimiter TEXT` - Delimiter for custom fields (default: ",")

**Arguments:**
- `NAME` - Case title (default: "Test case created from xsoar-cli")
- `DETAILS` - Case description (default: "Placeholder case details")

**Examples:**
```
xsoar-cli case create
xsoar-cli case create "Security Incident" "Suspicious network activity detected"
xsoar-cli case create --casetype "Phishing" --custom-fields "severity=High,source=Email" "Phishing Email" "Suspicious email received"
```
