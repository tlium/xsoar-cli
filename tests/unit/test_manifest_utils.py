"""Unit tests for manifest comparison helpers (``xsoar_cli.utilities.manifest``).

Every function under test is a pure data transformation, so no mocking is
needed. Tests use inline dicts that mirror the shapes used by the manifest
CLI commands.
"""

from __future__ import annotations

from xsoar_cli.utilities.manifest import (
    _all_manifest_packs,
    find_installed_packs_not_in_manifest,
    find_packs_in_manifest_not_installed,
    find_version_mismatch,
)

# ---------------------------------------------------------------------------
# Helpers -- reusable input data
# ---------------------------------------------------------------------------

_MANIFEST = {
    "custom_packs": [
        {"id": "MyOrg_EDR", "version": "2.0.0"},
        {"id": "MyOrg_CommonScripts", "version": "1.0.0"},
    ],
    "marketplace_packs": [
        {"id": "CommonScripts", "version": "1.14.20"},
        {"id": "Phishing", "version": "3.6.1"},
        {"id": "EWS", "version": "2.4.8"},
    ],
}

_INSTALLED = [
    {"id": "CommonScripts", "currentVersion": "1.14.20"},
    {"id": "Phishing", "currentVersion": "3.6.1"},
    {"id": "MyOrg_EDR", "currentVersion": "2.0.0"},
    {"id": "EWS", "currentVersion": "2.4.8"},
    {"id": "MyOrg_CommonScripts", "currentVersion": "1.0.0"},
]


# ===========================================================================
# _all_manifest_packs
# ===========================================================================


class TestAllManifestPacks:
    def test_both_sections_populated(self) -> None:
        result = _all_manifest_packs(_MANIFEST)
        ids = [p["id"] for p in result]
        assert ids == ["MyOrg_EDR", "MyOrg_CommonScripts", "CommonScripts", "Phishing", "EWS"]

    def test_custom_packs_only(self) -> None:
        manifest = {"custom_packs": [{"id": "A", "version": "1.0.0"}], "marketplace_packs": []}
        result = _all_manifest_packs(manifest)
        assert result == [{"id": "A", "version": "1.0.0"}]

    def test_marketplace_packs_only(self) -> None:
        manifest = {"custom_packs": [], "marketplace_packs": [{"id": "B", "version": "2.0.0"}]}
        result = _all_manifest_packs(manifest)
        assert result == [{"id": "B", "version": "2.0.0"}]

    def test_both_sections_empty(self) -> None:
        assert _all_manifest_packs({"custom_packs": [], "marketplace_packs": []}) == []

    def test_missing_keys_treated_as_empty(self) -> None:
        assert _all_manifest_packs({}) == []


# ===========================================================================
# find_installed_packs_not_in_manifest
# ===========================================================================


class TestFindInstalledPacksNotInManifest:
    def test_extra_pack_on_server(self) -> None:
        installed = [*_INSTALLED, {"id": "ExtraPack", "currentVersion": "1.0.0"}]
        result = find_installed_packs_not_in_manifest(installed, _MANIFEST)
        assert len(result) == 1
        assert result[0]["id"] == "ExtraPack"

    def test_multiple_extra_packs(self) -> None:
        installed = [
            *_INSTALLED,
            {"id": "ExtraA", "currentVersion": "1.0.0"},
            {"id": "ExtraB", "currentVersion": "2.0.0"},
        ]
        result = find_installed_packs_not_in_manifest(installed, _MANIFEST)
        ids = [p["id"] for p in result]
        assert ids == ["ExtraA", "ExtraB"]

    def test_no_extras(self) -> None:
        result = find_installed_packs_not_in_manifest(_INSTALLED, _MANIFEST)
        assert result == []

    def test_empty_installed(self) -> None:
        result = find_installed_packs_not_in_manifest([], _MANIFEST)
        assert result == []

    def test_empty_manifest(self) -> None:
        installed = [{"id": "SomePack", "currentVersion": "1.0.0"}]
        result = find_installed_packs_not_in_manifest(installed, {})
        assert len(result) == 1
        assert result[0]["id"] == "SomePack"


# ===========================================================================
# find_packs_in_manifest_not_installed
# ===========================================================================


class TestFindPacksInManifestNotInstalled:
    def test_missing_pack(self) -> None:
        installed = [p for p in _INSTALLED if p["id"] != "EWS"]
        result = find_packs_in_manifest_not_installed(installed, _MANIFEST)
        assert len(result) == 1
        assert result[0]["id"] == "EWS"

    def test_multiple_missing_packs(self) -> None:
        installed = [p for p in _INSTALLED if p["id"] not in ("EWS", "Phishing")]
        result = find_packs_in_manifest_not_installed(installed, _MANIFEST)
        ids = [p["id"] for p in result]
        assert "EWS" in ids
        assert "Phishing" in ids
        assert len(ids) == 2

    def test_none_missing(self) -> None:
        result = find_packs_in_manifest_not_installed(_INSTALLED, _MANIFEST)
        assert result == []

    def test_empty_installed(self) -> None:
        result = find_packs_in_manifest_not_installed([], _MANIFEST)
        assert len(result) == 5

    def test_empty_manifest(self) -> None:
        result = find_packs_in_manifest_not_installed(_INSTALLED, {})
        assert result == []


# ===========================================================================
# find_version_mismatch
# ===========================================================================


class TestFindVersionMismatch:
    def test_version_difference(self) -> None:
        installed = [
            {"id": "CommonScripts", "currentVersion": "1.14.20"},
            {"id": "Phishing", "currentVersion": "3.5.0"},
            {"id": "MyOrg_EDR", "currentVersion": "2.0.0"},
            {"id": "EWS", "currentVersion": "2.4.8"},
            {"id": "MyOrg_CommonScripts", "currentVersion": "1.0.0"},
        ]
        result = find_version_mismatch(installed, _MANIFEST)
        assert len(result) == 1
        assert result[0] == {
            "id": "Phishing",
            "manifest_version": "3.6.1",
            "installed_version": "3.5.0",
        }

    def test_multiple_mismatches(self) -> None:
        installed = [
            {"id": "CommonScripts", "currentVersion": "1.13.0"},
            {"id": "Phishing", "currentVersion": "3.5.0"},
            {"id": "MyOrg_EDR", "currentVersion": "2.0.0"},
            {"id": "EWS", "currentVersion": "2.4.8"},
            {"id": "MyOrg_CommonScripts", "currentVersion": "1.0.0"},
        ]
        result = find_version_mismatch(installed, _MANIFEST)
        ids = [p["id"] for p in result]
        assert "CommonScripts" in ids
        assert "Phishing" in ids
        assert len(ids) == 2

    def test_all_matching(self) -> None:
        result = find_version_mismatch(_INSTALLED, _MANIFEST)
        assert result == []

    def test_pack_not_installed_is_skipped(self) -> None:
        installed = [p for p in _INSTALLED if p["id"] != "EWS"]
        result = find_version_mismatch(installed, _MANIFEST)
        assert result == []

    def test_empty_installed(self) -> None:
        result = find_version_mismatch([], _MANIFEST)
        assert result == []

    def test_empty_manifest(self) -> None:
        result = find_version_mismatch(_INSTALLED, {})
        assert result == []
