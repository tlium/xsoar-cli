"""Output formatters for content list and describe commands.

Supports three output formats:

- **table** (default): human-readable aligned columns with section headers.
- **json**: machine-readable JSON with 4-space indentation.
- **plain**: tab-separated values, one item per line. No headers or
  decoration, suitable for piping to grep/cut/awk.
"""

from __future__ import annotations

import json

OUTPUT_FORMATS = ("json", "table", "plain")


def format_content_output(
    data: dict,
    *,
    output_format: str,
) -> str:
    """Format the content summary for display.

    *data* is the dict produced by ``filter_content()``, keyed by content
    type (``scripts``, ``playbooks``, ``commands``). *output_format*
    selects the presentation style.
    """
    if output_format == "json":
        return json.dumps(data, indent=4)

    formatter = _format_table if output_format == "table" else _format_plain

    sections: list[str] = []
    if "scripts" in data:
        sections.append(formatter(data["scripts"], "scripts"))
    if "playbooks" in data:
        sections.append(formatter(data["playbooks"], "playbooks"))
    if "commands" in data:
        sections.append(formatter(data["commands"], "commands"))

    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Table format
# ---------------------------------------------------------------------------


def _format_table(items: list[dict], content_type: str) -> str:
    if content_type == "scripts":
        return _table_scripts(items)
    if content_type == "playbooks":
        return _table_playbooks(items)
    return _table_commands(items)


def _table_scripts(scripts: list[dict]) -> str:
    header = f"Scripts ({len(scripts)})"
    headers = ["ID", "Description"]
    rows = [[s.get("id", ""), _oneline(s.get("comment", ""))] for s in scripts]
    return f"{header}\n\n{_render_table(headers, rows, max_widths={1: 80})}"


def _table_playbooks(playbooks: list[dict]) -> str:
    header = f"Playbooks ({len(playbooks)})"
    headers = ["ID", "Description"]
    rows = [[p.get("id", ""), _oneline(p.get("comment", ""))] for p in playbooks]
    return f"{header}\n\n{_render_table(headers, rows, max_widths={0: 50, 1: 80})}"


def _table_commands(command_groups: list[dict]) -> str:
    total = sum(len(g.get("commands", [])) for g in command_groups)
    header = f"Commands ({total} commands from {len(command_groups)} integrations)"
    headers = ["Command", "Description"]
    rows = []
    for group in command_groups:
        for cmd in group.get("commands", []):
            rows.append([cmd.get("name", ""), _oneline(cmd.get("description", ""))])
    return f"{header}\n\n{_render_table(headers, rows, max_widths={1: 80})}"


# ---------------------------------------------------------------------------
# Plain format (tab-separated, no decoration)
# ---------------------------------------------------------------------------


def _format_plain(items: list[dict], content_type: str) -> str:
    if content_type == "scripts":
        return _plain_scripts(items)
    if content_type == "playbooks":
        return _plain_playbooks(items)
    return _plain_commands(items)


def _plain_scripts(scripts: list[dict]) -> str:
    return "\n".join(f"{s.get('id', '')}\t{_oneline(s.get('comment', ''))}" for s in scripts)


def _plain_playbooks(playbooks: list[dict]) -> str:
    return "\n".join(f"{p.get('id', '')}\t{_oneline(p.get('comment', ''))}" for p in playbooks)


def _plain_commands(command_groups: list[dict]) -> str:
    lines: list[str] = []
    for group in command_groups:
        for cmd in group.get("commands", []):
            lines.append(f"{cmd.get('name', '')}\t{_oneline(cmd.get('description', ''))}")
    return "\n".join(lines)


def _oneline(text: str) -> str:
    """Collapse a multi-line string into a single line."""
    return " ".join(text.split())


# ---------------------------------------------------------------------------
# Describe (single-item vertical detail)
# ---------------------------------------------------------------------------

DESCRIBE_OUTPUT_FORMATS = ("table", "json")


def format_describe(item_type: str, item: dict, *, output_format: str) -> str:
    """Format a single content item for the ``content describe`` command.

    *item* is the reduced dict produced by ``describe_item()``. *item_type*
    is ``script``, ``playbook``, or ``command`` (singular). The ``table``
    format is a vertical detail layout; ``json`` dumps the reduced dict.
    """
    if output_format == "json":
        return json.dumps(item, indent=4)
    if item_type == "script":
        return _describe_script(item)
    if item_type == "playbook":
        return _describe_playbook(item)
    if item_type == "command":
        return _describe_command(item)
    raise ValueError(f"Invalid value {item_type=}")


def _describe_script(item: dict) -> str:
    parts = [f"Script: {item.get('id', '')}"]
    comment = item.get("comment", "").strip()
    if comment:
        parts.append(comment)
    parts.append(_describe_section("Arguments", _argument_rows(item.get("arguments", []))))
    return "\n\n".join(parts)


def _describe_playbook(item: dict) -> str:
    parts = [f"Playbook: {item.get('id', '')}"]
    comment = item.get("comment", "").strip()
    if comment:
        parts.append(comment)
    input_rows = [[inp.get("key", ""), _oneline(inp.get("description", ""))] for inp in item.get("inputs", [])]
    parts.append(_describe_section("Inputs", input_rows))
    parts.append(_describe_section("Outputs", _output_rows(item.get("outputs", []))))
    return "\n\n".join(parts)


def _describe_command(item: dict) -> str:
    parts = [f"Command: {item.get('name', '')}", f"Brand: {item.get('brand', '')}"]
    instance_rows = [[inst.get("name", ""), inst.get("state", "")] for inst in item.get("instances", [])]
    parts.append(_describe_section("Instances", instance_rows))
    description = item.get("description", "").strip()
    if description:
        parts.append(description)
    parts.append(_describe_section("Arguments", _argument_rows(item.get("arguments", []))))
    parts.append(_describe_section("Outputs", _output_rows(item.get("outputs", []))))
    return "\n\n".join(parts)


def _argument_rows(arguments: list[dict]) -> list[list[str]]:
    return [
        [
            arg.get("name", ""),
            "(required)" if arg.get("required") else "",
            _oneline(arg.get("description", "")),
        ]
        for arg in arguments
    ]


def _output_rows(outputs: list[dict]) -> list[list[str]]:
    return [
        [
            out.get("contextPath", ""),
            out.get("type", "") or "",
            _oneline(out.get("description", "")),
        ]
        for out in outputs
    ]


def _describe_section(label: str, rows: list[list[str]]) -> str:
    """Render a labelled section with aligned, indented columns.

    When *rows* is empty the section body is ``(none)``.
    """
    return f"{label}:\n{_aligned_columns(rows)}"


def _aligned_columns(rows: list[list[str]], *, indent: str = "  ") -> str:
    """Align rows into columns, indented, with no header. Empty -> ``(none)``."""
    if not rows:
        return f"{indent}(none)"

    col_count = max(len(row) for row in rows)
    widths = [0] * col_count
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    lines = []
    for row in rows:
        cells = []
        for i in range(col_count):
            cell = row[i] if i < len(row) else ""
            # Pad every column except the last so trailing text is not padded.
            cells.append(cell.ljust(widths[i]) if i < col_count - 1 else cell)
        lines.append((indent + "  ".join(cells)).rstrip())
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _render_table(
    headers: list[str],
    rows: list[list[str]],
    *,
    max_widths: dict[int, int] | None = None,
) -> str:
    """Render headers and rows as an aligned table with a dashed separator.

    *max_widths* maps column indices to maximum character widths. Cells
    exceeding the limit are truncated with an ellipsis.
    """
    col_count = len(headers)
    widths = [len(h) for h in headers]
    for row in rows:
        for i in range(min(col_count, len(row))):
            widths[i] = max(widths[i], len(row[i]))

    if max_widths:
        for col, limit in max_widths.items():
            if col < col_count:
                widths[col] = min(widths[col], limit)

    def _fit(text: str, width: int) -> str:
        if len(text) <= width:
            return text.ljust(width)
        return text[: width - 3] + "..."

    header_line = "  ".join(h.ljust(w) for h, w in zip(headers, widths))
    separator = "  ".join("-" * w for w in widths)
    data_lines = ["  ".join(_fit(row[i] if i < len(row) else "", widths[i]) for i in range(col_count)).rstrip() for row in rows]

    return "\n".join([header_line.rstrip(), separator, *data_lines])
