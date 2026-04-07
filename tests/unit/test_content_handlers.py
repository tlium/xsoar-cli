from unittest.mock import patch

import pytest

from xsoar_cli.utilities.download_content_handlers import (
    HANDLERS,
    LayoutHandler,
    PlaybookHandler,
    resolve_output_path,
)

# Sample playbook YAML that includes a packID in the expected location.
PLAYBOOK_YAML = "id: test-playbook\nname: Test Playbook\ncontentitemexportablefields:\n  contentitemfields:\n    packID: MyPack\n"

PLAYBOOK_YAML_NO_PACK = "id: test-playbook\nname: Test Playbook\n"


class TestResolveOutputPath:
    """Tests for the resolve_output_path helper."""

    def test_file_exists_returns_path(self, tmp_path) -> None:
        """Existing file: return path immediately (overwrite case)."""
        target_dir = tmp_path / "Packs" / "MyPack" / "Playbooks"
        target_dir.mkdir(parents=True)
        existing = target_dir / "playbook.yml"
        existing.write_text("old")
        result = resolve_output_path("MyPack", "Playbooks", "playbook.yml", cwd=tmp_path)
        assert result == existing

    def test_dir_exists_file_missing_confirm_yes(self, tmp_path) -> None:
        target_dir = tmp_path / "Packs" / "MyPack" / "Playbooks"
        target_dir.mkdir(parents=True)
        with patch("xsoar_cli.utilities.download_content_handlers.click.confirm", return_value=True):
            result = resolve_output_path("MyPack", "Playbooks", "playbook.yml", cwd=tmp_path)
        assert result == target_dir / "playbook.yml"

    def test_dir_exists_file_missing_confirm_no(self, tmp_path) -> None:
        target_dir = tmp_path / "Packs" / "MyPack" / "Playbooks"
        target_dir.mkdir(parents=True)
        with patch("xsoar_cli.utilities.download_content_handlers.click.confirm", return_value=False):
            result = resolve_output_path("MyPack", "Playbooks", "playbook.yml", cwd=tmp_path)
        assert result is None

    def test_dir_missing_fallback_to_cwd_and_confirm(self, tmp_path) -> None:
        """Dir missing, user accepts cwd, then confirms new file."""
        with patch("xsoar_cli.utilities.download_content_handlers.click.confirm", side_effect=[True, True]):
            result = resolve_output_path("MissingPack", "Playbooks", "playbook.yml", cwd=tmp_path)
        assert result == tmp_path / "playbook.yml"

    def test_dir_missing_decline_cwd(self, tmp_path) -> None:
        with patch("xsoar_cli.utilities.download_content_handlers.click.confirm", return_value=False):
            result = resolve_output_path("MissingPack", "Playbooks", "playbook.yml", cwd=tmp_path)
        assert result is None

    def test_no_pack_id_uses_cwd(self, tmp_path) -> None:
        """No pack ID: target dir is cwd. File is new, user confirms."""
        with patch("xsoar_cli.utilities.download_content_handlers.click.confirm", return_value=True):
            result = resolve_output_path(None, "Playbooks", "playbook.yml", cwd=tmp_path)
        assert result == tmp_path / "playbook.yml"

    def test_no_pack_id_existing_file_in_cwd(self, tmp_path) -> None:
        """No pack ID, but file already exists in cwd: overwrite silently."""
        existing = tmp_path / "playbook.yml"
        existing.write_text("old")
        result = resolve_output_path(None, "Playbooks", "playbook.yml", cwd=tmp_path)
        assert result == existing


class TestPlaybookHandler:
    """Tests for the PlaybookHandler class."""

    def test_extract_pack_id(self) -> None:
        handler = PlaybookHandler()
        data = PLAYBOOK_YAML.encode()
        assert handler.extract_pack_id(data) == "MyPack"

    def test_extract_pack_id_missing(self) -> None:
        handler = PlaybookHandler()
        data = PLAYBOOK_YAML_NO_PACK.encode()
        assert handler.extract_pack_id(data) is None

    def test_build_filename(self) -> None:
        handler = PlaybookHandler()
        assert handler.build_filename("My Cool Playbook") == "My_Cool_Playbook.yml"

    def test_write(self, tmp_path) -> None:
        handler = PlaybookHandler()
        filepath = tmp_path / "test.yml"
        handler.write(filepath, b"id: test\nname: Test\n")
        assert filepath.read_bytes() == b"id: test\nname: Test\n"

    def test_subdir(self) -> None:
        assert PlaybookHandler.subdir == "Playbooks"

    def test_format_after_download(self) -> None:
        assert PlaybookHandler.format_after_download is True

    def test_item_type(self) -> None:
        assert PlaybookHandler.item_type == "playbook"

    def test_reattach_after_download(self) -> None:
        assert PlaybookHandler.reattach_after_download is True


class TestLayoutHandler:
    """Tests for the LayoutHandler class."""

    def test_extract_pack_id(self) -> None:
        handler = LayoutHandler()
        assert handler.extract_pack_id({"packID": "SomePack", "name": "Test"}) == "SomePack"

    def test_extract_pack_id_missing(self) -> None:
        handler = LayoutHandler()
        assert handler.extract_pack_id({"name": "Test"}) is None

    def test_build_filename(self) -> None:
        handler = LayoutHandler()
        assert handler.build_filename("My Layout") == "layoutscontainer-My_Layout.json"

    def test_write(self, tmp_path) -> None:
        handler = LayoutHandler()
        filepath = tmp_path / "test.json"
        handler.write(filepath, {"name": "Test", "id": "123"})
        import json

        assert json.loads(filepath.read_text()) == {"name": "Test", "id": "123"}

    def test_subdir(self) -> None:
        assert LayoutHandler.subdir == "Layouts"

    def test_format_after_download(self) -> None:
        assert LayoutHandler.format_after_download is True

    def test_item_type(self) -> None:
        assert LayoutHandler.item_type == "layout"

    def test_reattach_after_download(self) -> None:
        assert LayoutHandler.reattach_after_download is True


class TestHandlersRegistry:
    """Tests for the HANDLERS registry."""

    def test_playbook_registered(self) -> None:
        assert "playbook" in HANDLERS
        assert isinstance(HANDLERS["playbook"], PlaybookHandler)

    def test_layout_registered(self) -> None:
        assert "layout" in HANDLERS
        assert isinstance(HANDLERS["layout"], LayoutHandler)
