"""Unit tests for content filter utilities (``xsoar_cli.utilities.content``).

Every function under test is a pure data transformation, so no mocking is
needed. Tests use inline dicts that mirror the shapes returned by the XSOAR
API (see Appendix A.5-A.7 in TODO_TEST_COVERAGE.md).
"""

from __future__ import annotations

from xsoar_cli.utilities.content import (
    _group_commands_by_brand,
    filter_commands,
    filter_content,
    filter_playbooks,
    filter_scripts,
    summarize_commands,
    summarize_playbooks,
    summarize_scripts,
)

# ---------------------------------------------------------------------------
# Helpers -- reusable input data
# ---------------------------------------------------------------------------

_SCRIPTS = [
    {
        "id": "SetAndHandleEmpty",
        "comment": "Set a value in context under the key you entered.",
        "arguments": [
            {"name": "key", "required": True, "deprecated": False, "description": "The key to set"},
            {"name": "value", "required": False, "deprecated": False, "description": "The value to set"},
        ],
        "type": "python3",
        "tags": ["Utility"],
    },
    {
        "id": "Print",
        "comment": "Prints text to war room.",
        "arguments": [
            {"name": "value", "required": True, "deprecated": False, "description": "The value to print"},
        ],
        "type": "python3",
        "tags": ["Utility"],
    },
    {
        "id": "LegacyScript",
        "comment": "A deprecated utility script.",
        "arguments": None,
        "type": "javascript",
        "tags": [],
    },
]

_PLAYBOOKS = [
    {
        "id": "22a1b2c3-d4e5-6f78-9a0b-c1d2e3f4a5b6",
        "name": "Phishing Investigation - Generic v2",
        "inputs": [
            {"key": "EmailFrom", "value": {}, "description": "The sender email address"},
            {"key": "EmailSubject", "value": {}, "description": "The email subject line"},
        ],
        "outputs": [
            {"contextPath": "Email.From", "description": "Sender address", "type": "string"},
            {"contextPath": "Email.IsPhishing", "description": "Whether phishing", "type": "boolean"},
        ],
        "tasks": {"0": {"id": "0", "type": "start"}},
        "deprecated": False,
        "hidden": False,
    },
    {
        "id": "Malware_Investigation",
        "name": "Malware Investigation",
        "inputs": [],
        "outputs": None,
        "tasks": {},
        "deprecated": False,
        "hidden": False,
    },
    {
        "id": "aabbccdd-1122-3344-5566-778899aabbcc",
        "name": "Access Investigation - Generic",
        "inputs": None,
        "outputs": [],
        "tasks": {},
        "deprecated": False,
        "hidden": False,
    },
]

_COMMAND_INSTANCES = [
    {
        "brand": "EWS v2",
        "category": "Email",
        "name": "EWS_Main",
        "commands": [
            {
                "name": "ews-search-mailbox",
                "description": "Search for items in a mailbox.",
                "arguments": [
                    {"name": "query", "required": True, "deprecated": False, "description": "Search query"},
                    {"name": "limit", "required": False, "deprecated": False, "description": "Max results"},
                ],
                "outputs": [
                    {"contextPath": "EWS.Items.id", "description": "Item ID", "type": "string"},
                ],
            },
        ],
    },
    {
        "brand": "EWS v2",
        "category": "Email",
        "name": "EWS_Secondary",
        "commands": [
            {
                "name": "ews-search-mailbox",
                "description": "Search for items in a mailbox.",
                "arguments": [
                    {"name": "query", "required": True, "deprecated": False, "description": "Search query"},
                ],
                "outputs": [],
            },
        ],
    },
    {
        "brand": "VirusTotal",
        "category": "Threat Intelligence",
        "name": "VirusTotal_Prod",
        "commands": [
            {
                "name": "vt-file-scan",
                "description": "Scan a file with VirusTotal.",
                "arguments": None,
                "outputs": None,
            },
        ],
    },
]


# ===========================================================================
# Scripts
# ===========================================================================


class TestSummarizeScripts:
    def test_typical_input(self) -> None:
        result = summarize_scripts(_SCRIPTS)
        assert result == [
            {"id": "SetAndHandleEmpty", "comment": "Set a value in context under the key you entered."},
            {"id": "Print", "comment": "Prints text to war room."},
            {"id": "LegacyScript", "comment": "A deprecated utility script."},
        ]

    def test_empty_list(self) -> None:
        assert summarize_scripts([]) == []

    def test_missing_fields_use_defaults(self) -> None:
        result = summarize_scripts([{}])
        assert result == [{"id": "", "comment": ""}]


class TestFilterScripts:
    def test_typical_input(self) -> None:
        result = filter_scripts(_SCRIPTS)
        assert len(result) == 3

        first = result[0]
        assert first["id"] == "SetAndHandleEmpty"
        assert len(first["arguments"]) == 2
        assert first["arguments"][0] == {
            "name": "key",
            "required": True,
            "deprecated": False,
            "description": "The key to set",
        }

    def test_none_arguments_becomes_empty_list(self) -> None:
        result = filter_scripts(_SCRIPTS)
        legacy = result[2]
        assert legacy["id"] == "LegacyScript"
        assert legacy["arguments"] == []

    def test_empty_list(self) -> None:
        assert filter_scripts([]) == []


# ===========================================================================
# Playbooks
# ===========================================================================


class TestSummarizePlaybooks:
    def test_typical_input(self) -> None:
        result = summarize_playbooks(_PLAYBOOKS)
        assert result == [
            {"id": "22a1b2c3-d4e5-6f78-9a0b-c1d2e3f4a5b6", "name": "Phishing Investigation - Generic v2"},
            {"id": "Malware_Investigation", "name": "Malware Investigation"},
            {"id": "aabbccdd-1122-3344-5566-778899aabbcc", "name": "Access Investigation - Generic"},
        ]

    def test_empty_list(self) -> None:
        assert summarize_playbooks([]) == []

    def test_missing_fields_use_defaults(self) -> None:
        result = summarize_playbooks([{}])
        assert result == [{"id": "", "name": ""}]


class TestFilterPlaybooks:
    def test_typical_input(self) -> None:
        result = filter_playbooks(_PLAYBOOKS)
        assert len(result) == 3

        first = result[0]
        assert first["id"] == "22a1b2c3-d4e5-6f78-9a0b-c1d2e3f4a5b6"
        assert first["name"] == "Phishing Investigation - Generic v2"
        assert len(first["inputs"]) == 2
        assert first["inputs"][0] == {"key": "EmailFrom", "description": "The sender email address"}
        assert len(first["outputs"]) == 2
        assert first["outputs"][0] == {
            "contextPath": "Email.From",
            "description": "Sender address",
            "type": "string",
        }

    def test_none_outputs_becomes_empty_list(self) -> None:
        result = filter_playbooks(_PLAYBOOKS)
        malware = result[1]
        assert malware["id"] == "Malware_Investigation"
        assert malware["outputs"] == []

    def test_none_inputs_becomes_empty_list(self) -> None:
        result = filter_playbooks(_PLAYBOOKS)
        access = result[2]
        assert access["id"] == "aabbccdd-1122-3344-5566-778899aabbcc"
        assert access["inputs"] == []

    def test_empty_list(self) -> None:
        assert filter_playbooks([]) == []


# ===========================================================================
# Commands
# ===========================================================================


class TestGroupCommandsByBrand:
    def test_deduplicates_same_brand(self) -> None:
        result = _group_commands_by_brand(_COMMAND_INSTANCES)
        brands = [inst.get("brand") for inst in result]
        assert brands == ["EWS v2", "VirusTotal"]

    def test_keeps_first_instance_per_brand(self) -> None:
        result = _group_commands_by_brand(_COMMAND_INSTANCES)
        ews = result[0]
        assert ews["name"] == "EWS_Main"

    def test_empty_list(self) -> None:
        assert _group_commands_by_brand([]) == []

    def test_single_instance(self) -> None:
        result = _group_commands_by_brand([_COMMAND_INSTANCES[2]])
        assert len(result) == 1
        assert result[0]["brand"] == "VirusTotal"


class TestSummarizeCommands:
    def test_typical_input(self) -> None:
        result = summarize_commands(_COMMAND_INSTANCES)
        assert len(result) == 2
        assert result[0] == {"brand": "EWS v2", "commands": ["ews-search-mailbox"]}
        assert result[1] == {"brand": "VirusTotal", "commands": ["vt-file-scan"]}

    def test_empty_list(self) -> None:
        assert summarize_commands([]) == []

    def test_none_commands_becomes_empty_list(self) -> None:
        result = summarize_commands([{"brand": "NoBrand", "commands": None}])
        assert result == [{"brand": "NoBrand", "commands": []}]


class TestFilterCommands:
    def test_typical_input(self) -> None:
        result = filter_commands(_COMMAND_INSTANCES)
        assert len(result) == 2

        ews = result[0]
        assert ews["brand"] == "EWS v2"
        assert len(ews["commands"]) == 1

        cmd = ews["commands"][0]
        assert cmd["name"] == "ews-search-mailbox"
        assert cmd["description"] == "Search for items in a mailbox."
        assert len(cmd["arguments"]) == 2
        assert cmd["outputs"] == [
            {"contextPath": "EWS.Items.id", "description": "Item ID", "type": "string"},
        ]

    def test_none_arguments_and_outputs(self) -> None:
        result = filter_commands(_COMMAND_INSTANCES)
        vt = result[1]
        vt_cmd = vt["commands"][0]
        assert vt_cmd["arguments"] == []
        assert vt_cmd["outputs"] == []

    def test_empty_list(self) -> None:
        assert filter_commands([]) == []


# ===========================================================================
# Dispatch (filter_content)
# ===========================================================================


class TestFilterContent:
    def test_scripts_summary(self) -> None:
        raw = {"scripts": _SCRIPTS}
        result = filter_content(raw, detail=False)
        assert "scripts" in result
        assert len(result["scripts"]) == 3
        assert result["scripts"][0] == {
            "id": "SetAndHandleEmpty",
            "comment": "Set a value in context under the key you entered.",
        }

    def test_scripts_detail(self) -> None:
        raw = {"scripts": _SCRIPTS}
        result = filter_content(raw, detail=True)
        assert "scripts" in result
        assert "arguments" in result["scripts"][0]

    def test_playbooks_summary(self) -> None:
        raw = {"playbooks": _PLAYBOOKS}
        result = filter_content(raw, detail=False)
        assert "playbooks" in result
        assert result["playbooks"][0] == {
            "id": "22a1b2c3-d4e5-6f78-9a0b-c1d2e3f4a5b6",
            "name": "Phishing Investigation - Generic v2",
        }

    def test_playbooks_detail(self) -> None:
        raw = {"playbooks": _PLAYBOOKS}
        result = filter_content(raw, detail=True)
        assert "playbooks" in result
        assert "inputs" in result["playbooks"][0]
        assert "outputs" in result["playbooks"][0]

    def test_commands_summary(self) -> None:
        raw = {"commands": _COMMAND_INSTANCES}
        result = filter_content(raw, detail=False)
        assert "commands" in result
        assert len(result["commands"]) == 2

    def test_commands_detail(self) -> None:
        raw = {"commands": _COMMAND_INSTANCES}
        result = filter_content(raw, detail=True)
        assert "commands" in result
        assert "arguments" in result["commands"][0]["commands"][0]

    def test_all_types_combined(self) -> None:
        raw = {
            "scripts": _SCRIPTS,
            "playbooks": _PLAYBOOKS,
            "commands": _COMMAND_INSTANCES,
        }
        result = filter_content(raw, detail=False)
        assert set(result.keys()) == {"scripts", "playbooks", "commands"}

    def test_empty_dict(self) -> None:
        assert filter_content({}) == {}

    def test_unknown_keys_ignored(self) -> None:
        raw = {"unknown": [{"id": "1"}]}
        assert filter_content(raw) == {}
