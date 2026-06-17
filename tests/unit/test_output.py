"""Unit tests for output formatters (``xsoar_cli.utilities.output``).

These cover the ``format_describe`` vertical detail layout used by the
``content describe`` command. The pure list/summary formatters are exercised
through the CLI integration tests.
"""

from __future__ import annotations

import json

import pytest

from xsoar_cli.utilities.output import format_describe

_SCRIPT = {
    "id": "MyScript",
    "comment": "Does a thing.",
    "arguments": [
        {"name": "value", "required": True, "deprecated": False, "description": "The value to use"},
        {"name": "mode", "required": False, "deprecated": False, "description": "Optional mode"},
    ],
}

_PLAYBOOK = {
    "id": "uuid-1",
    "comment": "Investigates things.",
    "inputs": [{"key": "Target", "description": "The target"}],
    "outputs": [{"contextPath": "Result.Verdict", "description": "The verdict", "type": "string"}],
}

_COMMAND = {
    "name": "servicenow-get-record",
    "brand": "ServiceNow v2",
    "instances": [
        {"name": "ServiceNow_v2_DNB", "state": "active"},
        {"name": "ServiceNow_Pentest_RITM", "state": "disabled"},
    ],
    "description": "Get a record from a table.",
    "arguments": [
        {"name": "table", "required": True, "deprecated": False, "description": "The table name"},
    ],
    "outputs": [
        {"contextPath": "ServiceNow.Record.ID", "description": "The record system ID", "type": "string"},
    ],
}


class TestFormatDescribeJSON:
    def test_script_json_roundtrips(self) -> None:
        out = format_describe("script", _SCRIPT, output_format="json")
        assert json.loads(out) == _SCRIPT

    def test_command_json_roundtrips(self) -> None:
        out = format_describe("command", _COMMAND, output_format="json")
        assert json.loads(out) == _COMMAND


class TestFormatDescribeScript:
    def test_header_and_description(self) -> None:
        out = format_describe("script", _SCRIPT, output_format="table")
        assert "Script: MyScript" in out
        assert "Does a thing." in out

    def test_arguments_listed(self) -> None:
        out = format_describe("script", _SCRIPT, output_format="table")
        assert "Arguments:" in out
        assert "value" in out
        assert "(required)" in out
        assert "The value to use" in out
        assert "mode" in out

    def test_no_arguments_shows_none(self) -> None:
        script = {"id": "Bare", "comment": "No args.", "arguments": []}
        out = format_describe("script", script, output_format="table")
        assert "Arguments:" in out
        assert "(none)" in out

    def test_empty_comment_omitted(self) -> None:
        script = {"id": "Bare", "comment": "", "arguments": []}
        out = format_describe("script", script, output_format="table")
        assert out.startswith("Script: Bare")


class TestFormatDescribePlaybook:
    def test_header_and_sections(self) -> None:
        out = format_describe("playbook", _PLAYBOOK, output_format="table")
        assert "Playbook: uuid-1" in out
        assert "Investigates things." in out
        assert "Inputs:" in out
        assert "Target" in out
        assert "Outputs:" in out
        assert "Result.Verdict" in out
        assert "string" in out

    def test_empty_inputs_and_outputs_show_none(self) -> None:
        playbook = {"id": "pb", "comment": "c", "inputs": [], "outputs": []}
        out = format_describe("playbook", playbook, output_format="table")
        assert out.count("(none)") == 2


class TestFormatDescribeCommand:
    def test_header_brand_and_sections(self) -> None:
        out = format_describe("command", _COMMAND, output_format="table")
        assert "Command: servicenow-get-record" in out
        assert "Brand: ServiceNow v2" in out
        assert "Get a record from a table." in out
        assert "Arguments:" in out
        assert "table" in out
        assert "Outputs:" in out
        assert "ServiceNow.Record.ID" in out

    def test_instances_section_lists_all_with_state(self) -> None:
        out = format_describe("command", _COMMAND, output_format="table")
        assert "Instances:" in out
        assert "ServiceNow_v2_DNB" in out
        assert "active" in out
        assert "ServiceNow_Pentest_RITM" in out
        assert "disabled" in out

    def test_brand_on_its_own_line(self) -> None:
        out = format_describe("command", _COMMAND, output_format="table")
        brand_lines = [line for line in out.splitlines() if line.startswith("Brand:")]
        assert brand_lines == ["Brand: ServiceNow v2"]


class TestFormatDescribeErrors:
    def test_invalid_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid"):
            format_describe("widget", {}, output_format="table")
