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

## Get Context

Retrieve the investigation context tree for a single case. Output is the raw context tree as JSON, matching `demisto.context()` at runtime. The incident record is not merged in.

**Syntax:** `xsoar-cli case get-context [OPTIONS] CASENUMBER`

**Options:**
- `--environment TEXT` - Target environment (default: uses default environment from config)

**Examples:**
```
xsoar-cli case get-context 153483
xsoar-cli case get-context --environment prod 153483
```

## Get Entry

Retrieve a single War Room entry by its full ID. Output is the raw entry as JSON. The command exits non-zero with a clear message when no entry with that ID exists in the case.

`ENTRY_ID` is the full entry ID as shown in the GUI, in the form `<n>@<case-id>` (e.g. `112@153483`). The case ID is taken from the entry ID, so it does not need to be supplied separately.

**Syntax:** `xsoar-cli case get-entry [OPTIONS] ENTRY_ID`

**Options:**
- `--environment TEXT` - Target environment (default: uses default environment from config)

**Examples:**
```
xsoar-cli case get-entry 112@153483
xsoar-cli case get-entry --environment prod 112@153483
```

## Get Entries

Retrieve all War Room entries for a single case. Output is the full list of entries as a JSON array, or an empty array when the case has no entries.

**Syntax:** `xsoar-cli case get-entries [OPTIONS] CASENUMBER`

**Options:**
- `--environment TEXT` - Target environment (default: uses default environment from config)

**Examples:**
```
xsoar-cli case get-entries 153483
xsoar-cli case get-entries --environment prod 153483
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
