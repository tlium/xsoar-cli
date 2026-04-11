"""Helpers for filtering verbose XSOAR content responses.

The raw JSON returned by xsoar_client.content.list() contains far more detail
than downstream consumers (especially LLM-based tooling) need. The functions
in this module strip each content type down to the fields that matter while
keeping the output structure extensible.

Three detail levels are available:

- **short** (default): compact id/name representation per item. Designed for
  discovery, where an LLM scans the full list to identify relevant items.
- **extended**: includes inputs, outputs, and arguments reduced to the fields
  that matter. Intended for retrieving actionable detail on a smaller set of
  items.
- **full**: the raw, unfiltered API response. Handled by the CLI command
  before calling into this module.
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
    """Return an id + name summary for each playbook.

    Playbook IDs are UUIDs, so the human-readable ``name`` field is included
    to make the summary useful for discovery.
    """
    return [
        {
            "id": playbook.get("id", ""),
            "name": playbook.get("name", ""),
        }
        for playbook in playbooks
    ]


def filter_playbooks(playbooks: list[dict]) -> list[dict]:
    """Return a detailed (but still filtered) representation of each playbook.

    Keeps ``id``, ``name``, ``inputs`` (reduced to ``key`` and
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
                "name": playbook.get("name", ""),
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
    """Return a brand + command name summary for each integration.

    Deduplicates by brand and reduces each command to just its name.
    """
    grouped = _group_commands_by_brand(instances)
    return [
        {
            "brand": instance.get("brand", ""),
            "commands": [cmd.get("name", "") for cmd in instance.get("commands") or []],
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


DETAIL_LEVELS = ("short", "extended", "full")


def filter_content(raw: dict, *, detail_level: str = "short") -> dict:
    """Dispatch filtering for each content type present in *raw*.

    ``raw`` is the dict returned by ``xsoar_client.content.list()`` and may
    contain any combination of ``scripts``, ``playbooks``, and ``commands``
    keys depending on the requested type.

    *detail_level* controls how much information is kept:

    - ``"short"``: compact id/name summary only.
    - ``"extended"``: includes arguments, inputs, and outputs.
    - ``"full"``: not handled here (the caller should output the raw response
      directly).
    """
    result: dict = {}

    if "scripts" in raw:
        if detail_level == "extended":
            result["scripts"] = filter_scripts(raw["scripts"])
        else:
            result["scripts"] = summarize_scripts(raw["scripts"])

    if "playbooks" in raw:
        if detail_level == "extended":
            result["playbooks"] = filter_playbooks(raw["playbooks"])
        else:
            result["playbooks"] = summarize_playbooks(raw["playbooks"])

    if "commands" in raw:
        if detail_level == "extended":
            result["commands"] = filter_commands(raw["commands"])
        else:
            result["commands"] = summarize_commands(raw["commands"])

    return result
