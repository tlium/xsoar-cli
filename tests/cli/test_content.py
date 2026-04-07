"""CLI integration tests for the ``content download`` command."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tests.cli.conftest import InvokeHelper

PLAYBOOK_YAML = "id: test-playbook\nname: Test Playbook\ncontentitemexportablefields:\n  contentitemfields:\n    packID: MyPack\n"
PLAYBOOK_YAML_NO_PACK = "id: test-playbook\nname: Test Playbook\n"


class TestContentDownloadPlaybookCommand:
    """Tests for ``content download --type playbook``."""

    def test_overwrites_existing_file(self, invoke: InvokeHelper, mock_content_env, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        pack_dir = tmp_path / "Packs" / "MyPack" / "Playbooks"
        pack_dir.mkdir(parents=True)
        existing = pack_dir / "Test_Playbook.yml"
        existing.write_text("old content")
        mock_content_env.download_playbook.return_value = PLAYBOOK_YAML.encode()
        result = invoke(["content", "download", "--type", "playbook", "Test Playbook"])
        assert result.exit_code == 0
        assert "ok." in result.output
        assert existing.read_text() == PLAYBOOK_YAML

    def test_new_file_confirm_yes(self, invoke: InvokeHelper, mock_content_env, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        pack_dir = tmp_path / "Packs" / "MyPack" / "Playbooks"
        pack_dir.mkdir(parents=True)
        mock_content_env.download_playbook.return_value = PLAYBOOK_YAML.encode()
        result = invoke(["content", "download", "--type", "playbook", "Test Playbook"], input="y\n")
        assert result.exit_code == 0
        assert (pack_dir / "Test_Playbook.yml").exists()

    def test_new_file_confirm_no(self, invoke: InvokeHelper, mock_content_env, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        pack_dir = tmp_path / "Packs" / "MyPack" / "Playbooks"
        pack_dir.mkdir(parents=True)
        mock_content_env.download_playbook.return_value = PLAYBOOK_YAML.encode()
        result = invoke(["content", "download", "--type", "playbook", "Test Playbook"], input="n\n")
        assert result.exit_code == 0
        assert "discarded" in result.output.lower()
        assert not (pack_dir / "Test_Playbook.yml").exists()

    def test_missing_dir_fallback_to_cwd(self, invoke: InvokeHelper, mock_content_env, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        mock_content_env.download_playbook.return_value = PLAYBOOK_YAML.encode()
        result = invoke(["content", "download", "--type", "playbook", "Test Playbook"], input="y\ny\n")
        assert result.exit_code == 0
        assert (tmp_path / "Test_Playbook.yml").exists()

    def test_missing_dir_decline_fallback(self, invoke: InvokeHelper, mock_content_env, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        mock_content_env.download_playbook.return_value = PLAYBOOK_YAML.encode()
        result = invoke(["content", "download", "--type", "playbook", "Test Playbook"], input="n\n")
        assert result.exit_code == 0
        assert "discarded" in result.output.lower()

    def test_no_pack_id_falls_back_to_cwd(self, invoke: InvokeHelper, mock_content_env, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        mock_content_env.download_playbook.return_value = PLAYBOOK_YAML_NO_PACK.encode()
        result = invoke(["content", "download", "--type", "playbook", "Test Playbook"], input="y\n")
        assert result.exit_code == 0
        assert (tmp_path / "Test_Playbook.yml").exists()

    def test_spaces_in_name(self, invoke: InvokeHelper, mock_content_env, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        pack_dir = tmp_path / "Packs" / "MyPack" / "Playbooks"
        pack_dir.mkdir(parents=True)
        existing = pack_dir / "My_Cool_Playbook.yml"
        existing.write_text("old")
        yaml_data = "id: my-playbook\nname: My Cool Playbook\ncontentitemexportablefields:\n  contentitemfields:\n    packID: MyPack\n"
        mock_content_env.download_playbook.return_value = yaml_data.encode()
        result = invoke(["content", "download", "--type", "playbook", "My Cool Playbook"])
        assert result.exit_code == 0
        assert existing.exists()

    def test_download_failure(self, invoke: InvokeHelper, mock_content_env) -> None:
        mock_content_env.download_playbook.side_effect = ValueError("Playbook 'Nonexistent' not found")
        result = invoke(["content", "download", "--type", "playbook", "Nonexistent"])
        assert result.exit_code == 1
        assert "FAILED" in result.output
        assert "Playbook 'Nonexistent' not found" in result.output

    def test_output_option_writes_to_specified_path(self, invoke: InvokeHelper, mock_content_env, tmp_path) -> None:
        repo_root = tmp_path / "my-repo"
        pack_dir = repo_root / "Packs" / "MyPack" / "Playbooks"
        pack_dir.mkdir(parents=True)
        existing = pack_dir / "Test_Playbook.yml"
        existing.write_text("old")
        mock_content_env.download_playbook.return_value = PLAYBOOK_YAML.encode()
        result = invoke(["content", "download", "--type", "playbook", "--output", str(repo_root), "Test Playbook"])
        assert result.exit_code == 0
        assert existing.read_text() == PLAYBOOK_YAML

    def test_output_option_new_file_confirm_yes(self, invoke: InvokeHelper, mock_content_env, tmp_path) -> None:
        repo_root = tmp_path / "my-repo"
        pack_dir = repo_root / "Packs" / "MyPack" / "Playbooks"
        pack_dir.mkdir(parents=True)
        mock_content_env.download_playbook.return_value = PLAYBOOK_YAML.encode()
        result = invoke(["content", "download", "--type", "playbook", "--output", str(repo_root), "Test Playbook"], input="y\n")
        assert result.exit_code == 0
        assert (pack_dir / "Test_Playbook.yml").exists()

    def test_runs_demisto_sdk_format(self, invoke: InvokeHelper, mock_content_env, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        pack_dir = tmp_path / "Packs" / "MyPack" / "Playbooks"
        pack_dir.mkdir(parents=True)
        existing = pack_dir / "Test_Playbook.yml"
        existing.write_text("old")
        mock_content_env.download_playbook.return_value = PLAYBOOK_YAML.encode()
        result = invoke(["content", "download", "--type", "playbook", "Test Playbook"])
        assert result.exit_code == 0
        assert "demisto-sdk format" in result.output.lower()
        mock_content_env.subprocess_run.assert_called_once()
        call_args = mock_content_env.subprocess_run.call_args[0][0]
        assert call_args[0] == "demisto-sdk"
        assert call_args[1] == "format"
        assert str(existing) in call_args

    def test_reattaches_after_write(self, invoke: InvokeHelper, mock_content_env, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        pack_dir = tmp_path / "Packs" / "MyPack" / "Playbooks"
        pack_dir.mkdir(parents=True)
        existing = pack_dir / "Test_Playbook.yml"
        existing.write_text("old")
        mock_content_env.download_playbook.return_value = PLAYBOOK_YAML.encode()
        result = invoke(["content", "download", "--type", "playbook", "Test Playbook"])
        assert result.exit_code == 0
        mock_content_env.attach.assert_called_once_with("playbook", "Test Playbook")


class TestContentDownloadLayoutCommand:
    """Tests for ``content download --type layout``."""

    def test_overwrites_existing_file(self, invoke: InvokeHelper, mock_content_env, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        pack_dir = tmp_path / "Packs" / "SomePack" / "Layouts"
        pack_dir.mkdir(parents=True)
        existing = pack_dir / "layoutscontainer-Test_Layout.json"
        existing.write_text("{}")
        mock_content_env.download_layout.return_value = {"id": "test-layout", "name": "Test Layout", "packID": "SomePack"}
        result = invoke(["content", "download", "--type", "layout", "Test Layout"])
        assert result.exit_code == 0
        assert "ok." in result.output
        assert '"name": "Test Layout"' in existing.read_text()

    def test_new_file_confirm_yes(self, invoke: InvokeHelper, mock_content_env, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        pack_dir = tmp_path / "Packs" / "SomePack" / "Layouts"
        pack_dir.mkdir(parents=True)
        mock_content_env.download_layout.return_value = {"id": "test-layout", "name": "Test Layout", "packID": "SomePack"}
        result = invoke(["content", "download", "--type", "layout", "Test Layout"], input="y\n")
        assert result.exit_code == 0
        assert (pack_dir / "layoutscontainer-Test_Layout.json").exists()

    def test_new_file_confirm_no(self, invoke: InvokeHelper, mock_content_env, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        pack_dir = tmp_path / "Packs" / "SomePack" / "Layouts"
        pack_dir.mkdir(parents=True)
        mock_content_env.download_layout.return_value = {"id": "test-layout", "name": "Test Layout", "packID": "SomePack"}
        result = invoke(["content", "download", "--type", "layout", "Test Layout"], input="n\n")
        assert result.exit_code == 0
        assert "discarded" in result.output.lower()
        assert not (pack_dir / "layoutscontainer-Test_Layout.json").exists()

    def test_missing_dir_fallback_to_cwd(self, invoke: InvokeHelper, mock_content_env, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        mock_content_env.download_layout.return_value = {"id": "test-layout", "name": "Test Layout", "packID": "SomePack"}
        result = invoke(["content", "download", "--type", "layout", "Test Layout"], input="y\ny\n")
        assert result.exit_code == 0
        assert (tmp_path / "layoutscontainer-Test_Layout.json").exists()

    def test_missing_dir_decline_fallback(self, invoke: InvokeHelper, mock_content_env, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        mock_content_env.download_layout.return_value = {"id": "test-layout", "name": "Test Layout", "packID": "SomePack"}
        result = invoke(["content", "download", "--type", "layout", "Test Layout"], input="n\n")
        assert result.exit_code == 0
        assert "discarded" in result.output.lower()

    def test_download_failure(self, invoke: InvokeHelper, mock_content_env) -> None:
        mock_content_env.download_layout.side_effect = ValueError("Layout 'Nonexistent' not found")
        result = invoke(["content", "download", "--type", "layout", "Nonexistent"])
        assert result.exit_code == 1
        assert "FAILED" in result.output
        assert "Layout 'Nonexistent' not found" in result.output

    def test_output_option_writes_to_specified_path(self, invoke: InvokeHelper, mock_content_env, tmp_path) -> None:
        repo_root = tmp_path / "my-repo"
        pack_dir = repo_root / "Packs" / "SomePack" / "Layouts"
        pack_dir.mkdir(parents=True)
        existing = pack_dir / "layoutscontainer-Test_Layout.json"
        existing.write_text("{}")
        mock_content_env.download_layout.return_value = {"id": "test-layout", "name": "Test Layout", "packID": "SomePack"}
        result = invoke(["content", "download", "--type", "layout", "--output", str(repo_root), "Test Layout"])
        assert result.exit_code == 0
        assert '"name": "Test Layout"' in existing.read_text()

    def test_runs_demisto_sdk_format(self, invoke: InvokeHelper, mock_content_env, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        pack_dir = tmp_path / "Packs" / "SomePack" / "Layouts"
        pack_dir.mkdir(parents=True)
        existing = pack_dir / "layoutscontainer-Test_Layout.json"
        existing.write_text("{}")
        mock_content_env.download_layout.return_value = {"id": "test-layout", "name": "Test Layout", "packID": "SomePack"}
        result = invoke(["content", "download", "--type", "layout", "Test Layout"])
        assert result.exit_code == 0
        assert "demisto-sdk format" in result.output.lower()
        mock_content_env.subprocess_run.assert_called_once()

    def test_reattaches_after_write(self, invoke: InvokeHelper, mock_content_env, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        pack_dir = tmp_path / "Packs" / "SomePack" / "Layouts"
        pack_dir.mkdir(parents=True)
        existing = pack_dir / "layoutscontainer-Test_Layout.json"
        existing.write_text("{}")
        mock_content_env.download_layout.return_value = {"id": "test-layout", "name": "Test Layout", "packID": "SomePack"}
        result = invoke(["content", "download", "--type", "layout", "Test Layout"])
        assert result.exit_code == 0
        mock_content_env.attach.assert_called_once_with("layout", "Test Layout")


class TestContentDownloadMissingType:
    def test_download_missing_type(self, invoke: InvokeHelper, mock_content_env) -> None:
        result = invoke(["content", "download", "SomeName"])
        assert result.exit_code != 0
        assert "Missing option '--type'" in result.output
