"""Helpers for filtering verbose XSOAR content responses.

The raw JSON returned by xsoar_client.content.list() contains far more detail
than downstream consumers (especially LLM-based tooling) need. The functions
in this module strip each content type down to the fields that matter while
keeping the output structure extensible.

``content list`` uses the ``summarize_*`` functions to produce a compact
id/comment summary per item, designed for discovery where a consumer scans
the list to identify relevant items.

The ``filter_*`` functions reduce each item to its actionable detail
(arguments, inputs, outputs). They are reserved for the ``content describe``
command, which presents a single item in depth.
"""

from __future__ import annotations

# -- Scripts -----------------------------------------------------------------


def summarize_scripts(scripts: list[dict]) -> list[dict]:
    """Return an id + comment summary for each script.

    This is the most compact representation, suitable for discovery queries
    where the consumer only needs to identify scripts by name and purpose.
    """
    return [
        {
            "id": script.get("id", ""),
            "comment": script.get("comment", ""),
        }
        for script in scripts
    ]


def filter_scripts(scripts: list[dict]) -> list[dict]:
    """Return a detailed (but still filtered) representation of each script.

    Keeps ``id``, ``comment``, and ``arguments`` (with each argument reduced
    to ``name``, ``required``, ``deprecated``, ``description``).
    Scripts whose ``arguments`` value is ``None`` get an empty list.
    """
    argument_keys = ("name", "required", "deprecated", "description")
    filtered: list[dict] = []

    for script in scripts:
        arguments = script.get("arguments") or []
        filtered.append(
            {
                "id": script.get("id", ""),
                "comment": script.get("comment", ""),
                "arguments": [{key: arg.get(key) for key in argument_keys} for arg in arguments],
            }
        )

    return filtered


def summarize_playbooks(playbooks: list[dict]) -> list[dict]:
    """Return an id + comment summary for each playbook.

    The ``comment`` field holds the playbook description and matches the
    field name used by scripts, keeping the structure consistent across
    content types.
    """
    return [
        {
            "id": playbook.get("id", ""),
            "comment": playbook.get("comment", ""),
        }
        for playbook in playbooks
    ]


def filter_playbooks(playbooks: list[dict]) -> list[dict]:
    """Return a detailed (but still filtered) representation of each playbook.

    Keeps ``id``, ``comment``, ``inputs`` (reduced to ``key`` and
    ``description``), and ``outputs`` (reduced to ``contextPath``,
    ``description``, ``type``). The ``tasks`` blob is excluded because it
    dominates the response size and is not useful for deciding whether to
    use a playbook.
    """
    input_keys = ("key", "description")
    output_keys = ("contextPath", "description", "type")
    filtered: list[dict] = []

    for playbook in playbooks:
        inputs = playbook.get("inputs") or []
        outputs = playbook.get("outputs") or []
        filtered.append(
            {
                "id": playbook.get("id", ""),
                "comment": playbook.get("comment", ""),
                "inputs": [{key: inp.get(key) for key in input_keys} for inp in inputs],
                "outputs": [{key: out.get(key) for key in output_keys} for out in outputs],
            }
        )

    return filtered


def _group_commands_by_brand(instances: list[dict]) -> list[dict]:
    """Deduplicate integration instances by brand.

    The raw ``/user/commands`` response contains one entry per integration
    instance. When the same brand is configured with multiple instances the
    command definitions are identical. Grouping by brand removes this
    duplication and keeps the output focused on what commands are available
    rather than how many instances exist.
    """
    seen: dict[str, dict] = {}
    for instance in instances:
        brand = instance.get("brand", "")
        if brand not in seen:
            seen[brand] = instance
    return list(seen.values())


def summarize_commands(instances: list[dict]) -> list[dict]:
    """Return a brand + command summary for each integration.

    Deduplicates by brand and reduces each command to ``name`` and
    ``description``. Returning objects (rather than plain name strings)
    keeps the structure consistent with ``filter_commands`` so formatters
    do not need to handle both shapes.
    """
    grouped = _group_commands_by_brand(instances)
    return [
        {
            "brand": instance.get("brand", ""),
            "commands": [
                {
                    "name": cmd.get("name", ""),
                    "description": cmd.get("description", ""),
                }
                for cmd in instance.get("commands") or []
            ],
        }
        for instance in grouped
    ]


def filter_commands(instances: list[dict]) -> list[dict]:
    """Return a detailed (but still filtered) representation of each integration's commands.

    Deduplicates by brand. Keeps each command's ``name``, ``description``,
    ``arguments`` (reduced to ``name``, ``required``, ``deprecated``,
    ``description``), and ``outputs`` (reduced to ``contextPath``,
    ``description``, ``type``).
    """
    argument_keys = ("name", "required", "deprecated", "description")
    output_keys = ("contextPath", "description", "type")
    grouped = _group_commands_by_brand(instances)
    filtered: list[dict] = []

    for instance in grouped:
        commands: list[dict] = []
        for cmd in instance.get("commands") or []:
            arguments = cmd.get("arguments") or []
            outputs = cmd.get("outputs") or []
            commands.append(
                {
                    "name": cmd.get("name", ""),
                    "description": cmd.get("description", ""),
                    "arguments": [{key: arg.get(key) for key in argument_keys} for arg in arguments],
                    "outputs": [{key: out.get(key) for key in output_keys} for out in outputs],
                }
            )
        filtered.append(
            {
                "brand": instance.get("brand", ""),
                "commands": commands,
            }
        )

    return filtered


# -- Detached content --------------------------------------------------------


def format_detached_summary(items: list[dict], content_type: str) -> str:
    """Format a human-readable summary of detached content items.

    *items* is the list of content records returned for a single content type
    (for example the ``scripts`` list from the detached automation search).
    *content_type* is the plural label used in the output (for example
    ``"scripts"``).

    When *items* is empty, returns ``"No detached <content_type> found"``.
    Otherwise returns a header line with the count followed by one indented
    line per item in the form ``<name> (ID: <id>)``.
    """
    if not items:
        return f"No detached {content_type} found"

    lines = [f"Found {len(items)} detached {content_type}:"]
    lines.extend(f"  {item.get('name', '')} (ID: {item.get('id', '')})" for item in items)
    return "\n".join(lines)


def filter_content(raw: dict) -> dict:
    """Produce a compact id/comment summary for each content type in *raw*.

    ``raw`` is the dict returned by ``xsoar_client.content.list()`` and may
    contain any combination of ``scripts``, ``playbooks``, and ``commands``
    keys depending on the requested type.
    """
    result: dict = {}

    if "scripts" in raw:
        result["scripts"] = summarize_scripts(raw["scripts"])

    if "playbooks" in raw:
        result["playbooks"] = summarize_playbooks(raw["playbooks"])

    if "commands" in raw:
        result["commands"] = summarize_commands(raw["commands"])

    return result


_SEARCH_FIELDS = ("id", "name", "comment", "description")


def _item_matches(item: dict, term: str) -> bool:
    """Return True if *term* is a substring of any searchable field on *item*.

    The match is case-insensitive and checks ``id``, ``name``, ``comment``,
    and ``description`` (whichever are present). *term* is expected to be
    already lowercased.
    """
    return any(term in str(item.get(field, "")).lower() for field in _SEARCH_FIELDS)


def search_content(summary: dict, term: str) -> dict:
    """Filter a content summary down to items matching *term*.

    *summary* is the dict produced by ``filter_content()``. The match is a
    case-insensitive substring test against each item's ``id``, ``name``,
    ``comment``, and ``description`` fields (whichever are present).

    For scripts and playbooks, non-matching items are dropped. For commands,
    only matching commands are kept within each brand group, and brand groups
    left with no matching commands are dropped. Content types left with no
    matches are omitted from the result entirely.

    When *term* is empty, the summary is returned unchanged.
    """
    if not term:
        return summary

    needle = term.lower()
    result: dict = {}

    for content_type in ("scripts", "playbooks"):
        items = summary.get(content_type)
        if items is None:
            continue
        matches = [item for item in items if _item_matches(item, needle)]
        if matches:
            result[content_type] = matches

    if "commands" in summary:
        groups: list[dict] = []
        for group in summary["commands"]:
            matching = [cmd for cmd in group.get("commands", []) if _item_matches(cmd, needle)]
            if matching:
                groups.append({"brand": group.get("brand", ""), "commands": matching})
        if groups:
            result["commands"] = groups

    return result


def describe_item(item_type: str, raw: dict) -> dict:
    """Reduce a single raw content item to its actionable detail.

    *item_type* is ``script``, ``playbook``, or ``command`` (singular).
    *raw* is the record returned by ``Content.describe()``. For commands the
    raw record wraps the command in ``{brand, instances, command}``; the
    reduced result flattens that into the command fields plus ``brand`` and
    ``instances``.
    """
    if item_type == "script":
        return filter_scripts([raw])[0]
    if item_type == "playbook":
        return filter_playbooks([raw])[0]
    if item_type == "command":
        brand = raw.get("brand", "")
        instances = raw.get("instances", [])
        reduced = filter_commands([{"brand": brand, "commands": [raw.get("command", {})]}])[0]["commands"][0]
        return {
            "name": reduced["name"],
            "brand": brand,
            "instances": instances,
            "description": reduced["description"],
            "arguments": reduced["arguments"],
            "outputs": reduced["outputs"],
        }
    raise ValueError(f"Invalid value {item_type=}")
