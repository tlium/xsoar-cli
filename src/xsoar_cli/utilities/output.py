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


def _oneline(text: str) -> str:
    """Collapse a multi-line string into a single line."""
    return " ".join(text.split())
