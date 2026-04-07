from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from xsoar_cli import cli
from xsoar_cli.commands.content.commands import _resolve_output_path
from xsoar_cli.xsoar_client.content import Content

# Sample playbook YAML that includes a packID in the expected location.
PLAYBOOK_YAML = "id: test-playbook\nname: Test Playbook\ncontentitemexportablefields:\n  contentitemfields:\n    packID: MyPack\n"

PLAYBOOK_YAML_NO_PACK = "id: test-playbook\nname: Test Playbook\n"


class TestContentDownloadPlaybookCommand:
    """Tests for the `content download --type playbook` CLI command."""

    @patch("xsoar_cli.xsoar_client.client.Client.test_connectivity", return_value=True)
    @patch("xsoar_cli.xsoar_client.content.Content.download_playbook")
    def test_overwrites_existing_file(self, mock_download, mock_connectivity, mock_config_file, tmp_path, monkeypatch) -> None:  # noqa: ANN001
        """File already exists in the pack directory. Should overwrite without prompts."""
        monkeypatch.chdir(tmp_path)
        pack_dir = tmp_path / "Packs" / "MyPack" / "Playbooks"
        pack_dir.mkdir(parents=True)
        existing = pack_dir / "Test_Playbook.yml"
        existing.write_text("old content")
        mock_download.return_value = PLAYBOOK_YAML.encode()
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["content", "download", "--type", "playbook", "Test Playbook"])
        assert result.exit_code == 0
        assert "ok." in result.output
        assert existing.read_text() == PLAYBOOK_YAML

    @patch("xsoar_cli.xsoar_client.client.Client.test_connectivity", return_value=True)
    @patch("xsoar_cli.xsoar_client.content.Content.download_playbook")
    def test_new_file_confirm_yes(self, mock_download, mock_connectivity, mock_config_file, tmp_path, monkeypatch) -> None:  # noqa: ANN001
        """Pack directory exists but file does not. User confirms writing."""
        monkeypatch.chdir(tmp_path)
        pack_dir = tmp_path / "Packs" / "MyPack" / "Playbooks"
        pack_dir.mkdir(parents=True)
        mock_download.return_value = PLAYBOOK_YAML.encode()
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["content", "download", "--type", "playbook", "Test Playbook"], input="y\n")
        assert result.exit_code == 0
        assert (pack_dir / "Test_Playbook.yml").exists()

    @patch("xsoar_cli.xsoar_client.client.Client.test_connectivity", return_value=True)
    @patch("xsoar_cli.xsoar_client.content.Content.download_playbook")
    def test_new_file_confirm_no(self, mock_download, mock_connectivity, mock_config_file, tmp_path, monkeypatch) -> None:  # noqa: ANN001
        """Pack directory exists but file does not. User declines writing."""
        monkeypatch.chdir(tmp_path)
        pack_dir = tmp_path / "Packs" / "MyPack" / "Playbooks"
        pack_dir.mkdir(parents=True)
        mock_download.return_value = PLAYBOOK_YAML.encode()
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["content", "download", "--type", "playbook", "Test Playbook"], input="n\n")
        assert result.exit_code == 0
        assert "discarded" in result.output.lower()
        assert not (pack_dir / "Test_Playbook.yml").exists()

    @patch("xsoar_cli.xsoar_client.client.Client.test_connectivity", return_value=True)
    @patch("xsoar_cli.xsoar_client.content.Content.download_playbook")
    def test_missing_dir_fallback_to_cwd(self, mock_download, mock_connectivity, mock_config_file, tmp_path, monkeypatch) -> None:  # noqa: ANN001
        """Pack directory does not exist. User opts to save to cwd, then confirms new file."""
        monkeypatch.chdir(tmp_path)
        mock_download.return_value = PLAYBOOK_YAML.encode()
        runner = CliRunner()
        # First prompt: save to cwd? -> y. Second prompt: new file, write? -> y.
        result = runner.invoke(cli.cli, ["content", "download", "--type", "playbook", "Test Playbook"], input="y\ny\n")
        assert result.exit_code == 0
        assert (tmp_path / "Test_Playbook.yml").exists()

    @patch("xsoar_cli.xsoar_client.client.Client.test_connectivity", return_value=True)
    @patch("xsoar_cli.xsoar_client.content.Content.download_playbook")
    def test_missing_dir_decline_fallback(self, mock_download, mock_connectivity, mock_config_file, tmp_path, monkeypatch) -> None:  # noqa: ANN001
        """Pack directory does not exist. User declines saving to cwd."""
        monkeypatch.chdir(tmp_path)
        mock_download.return_value = PLAYBOOK_YAML.encode()
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["content", "download", "--type", "playbook", "Test Playbook"], input="n\n")
        assert result.exit_code == 0
        assert "discarded" in result.output.lower()

    @patch("xsoar_cli.xsoar_client.client.Client.test_connectivity", return_value=True)
    @patch("xsoar_cli.xsoar_client.content.Content.download_playbook")
    def test_no_pack_id_falls_back_to_cwd(self, mock_download, mock_connectivity, mock_config_file, tmp_path, monkeypatch) -> None:  # noqa: ANN001
        """Playbook YAML has no packID. Falls back to cwd, user confirms."""
        monkeypatch.chdir(tmp_path)
        mock_download.return_value = PLAYBOOK_YAML_NO_PACK.encode()
        runner = CliRunner()
        # Prompt: new file in cwd, write? -> y.
        result = runner.invoke(cli.cli, ["content", "download", "--type", "playbook", "Test Playbook"], input="y\n")
        assert result.exit_code == 0
        assert (tmp_path / "Test_Playbook.yml").exists()

    @patch("xsoar_cli.xsoar_client.client.Client.test_connectivity", return_value=True)
    @patch("xsoar_cli.xsoar_client.content.Content.download_playbook")
    def test_spaces_in_name(self, mock_download, mock_connectivity, mock_config_file, tmp_path, monkeypatch) -> None:  # noqa: ANN001
        monkeypatch.chdir(tmp_path)
        pack_dir = tmp_path / "Packs" / "MyPack" / "Playbooks"
        pack_dir.mkdir(parents=True)
        existing = pack_dir / "My_Cool_Playbook.yml"
        existing.write_text("old")
        yaml_data = "id: my-playbook\nname: My Cool Playbook\ncontentitemexportablefields:\n  contentitemfields:\n    packID: MyPack\n"
        mock_download.return_value = yaml_data.encode()
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["content", "download", "--type", "playbook", "My Cool Playbook"])
        assert result.exit_code == 0
        assert existing.exists()

    @patch("xsoar_cli.xsoar_client.client.Client.test_connectivity", return_value=True)
    @patch("xsoar_cli.xsoar_client.content.Content.download_playbook")
    def test_download_failure(self, mock_download, mock_connectivity, mock_config_file) -> None:  # noqa: ANN001
        mock_download.side_effect = ValueError("Playbook 'Nonexistent' not found")
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["content", "download", "--type", "playbook", "Nonexistent"])
        assert result.exit_code == 1
        assert "FAILED" in result.output
        assert "Playbook 'Nonexistent' not found" in result.output

    @patch("xsoar_cli.xsoar_client.client.Client.test_connectivity", return_value=True)
    @patch("xsoar_cli.xsoar_client.content.Content.download_playbook")
    def test_output_option_writes_to_specified_path(self, mock_download, mock_connectivity, mock_config_file, tmp_path) -> None:  # noqa: ANN001
        """--output points to a content repo root outside cwd."""
        repo_root = tmp_path / "my-repo"
        pack_dir = repo_root / "Packs" / "MyPack" / "Playbooks"
        pack_dir.mkdir(parents=True)
        existing = pack_dir / "Test_Playbook.yml"
        existing.write_text("old")
        mock_download.return_value = PLAYBOOK_YAML.encode()
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["content", "download", "--type", "playbook", "--output", str(repo_root), "Test Playbook"])
        assert result.exit_code == 0
        assert existing.read_text() == PLAYBOOK_YAML

    @patch("xsoar_cli.xsoar_client.client.Client.test_connectivity", return_value=True)
    @patch("xsoar_cli.xsoar_client.content.Content.download_playbook")
    def test_output_option_new_file_confirm_yes(self, mock_download, mock_connectivity, mock_config_file, tmp_path) -> None:  # noqa: ANN001
        """--output with pack dir present but file missing. User confirms."""
        repo_root = tmp_path / "my-repo"
        pack_dir = repo_root / "Packs" / "MyPack" / "Playbooks"
        pack_dir.mkdir(parents=True)
        mock_download.return_value = PLAYBOOK_YAML.encode()
        runner = CliRunner()
        result = runner.invoke(
            cli.cli, ["content", "download", "--type", "playbook", "--output", str(repo_root), "Test Playbook"], input="y\n"
        )
        assert result.exit_code == 0
        assert (pack_dir / "Test_Playbook.yml").exists()


class TestContentDownloadLayoutCommand:
    """Tests for the `content download --type layout` CLI command."""

    @patch("xsoar_cli.xsoar_client.client.Client.test_connectivity", return_value=True)
    @patch("xsoar_cli.xsoar_client.content.Content.download_layout")
    def test_overwrites_existing_file(self, mock_download, mock_connectivity, mock_config_file, tmp_path, monkeypatch) -> None:  # noqa: ANN001
        monkeypatch.chdir(tmp_path)
        pack_dir = tmp_path / "Packs" / "SomePack" / "Layouts"
        pack_dir.mkdir(parents=True)
        existing = pack_dir / "layoutscontainer-Test_Layout.json"
        existing.write_text("{}")
        mock_download.return_value = {"id": "test-layout", "name": "Test Layout", "packID": "SomePack"}
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["content", "download", "--type", "layout", "Test Layout"])
        assert result.exit_code == 0
        assert "ok." in result.output
        assert '"name": "Test Layout"' in existing.read_text()

    @patch("xsoar_cli.xsoar_client.client.Client.test_connectivity", return_value=True)
    @patch("xsoar_cli.xsoar_client.content.Content.download_layout")
    def test_new_file_confirm_yes(self, mock_download, mock_connectivity, mock_config_file, tmp_path, monkeypatch) -> None:  # noqa: ANN001
        monkeypatch.chdir(tmp_path)
        pack_dir = tmp_path / "Packs" / "SomePack" / "Layouts"
        pack_dir.mkdir(parents=True)
        mock_download.return_value = {"id": "test-layout", "name": "Test Layout", "packID": "SomePack"}
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["content", "download", "--type", "layout", "Test Layout"], input="y\n")
        assert result.exit_code == 0
        assert (pack_dir / "layoutscontainer-Test_Layout.json").exists()

    @patch("xsoar_cli.xsoar_client.client.Client.test_connectivity", return_value=True)
    @patch("xsoar_cli.xsoar_client.content.Content.download_layout")
    def test_new_file_confirm_no(self, mock_download, mock_connectivity, mock_config_file, tmp_path, monkeypatch) -> None:  # noqa: ANN001
        monkeypatch.chdir(tmp_path)
        pack_dir = tmp_path / "Packs" / "SomePack" / "Layouts"
        pack_dir.mkdir(parents=True)
        mock_download.return_value = {"id": "test-layout", "name": "Test Layout", "packID": "SomePack"}
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["content", "download", "--type", "layout", "Test Layout"], input="n\n")
        assert result.exit_code == 0
        assert "discarded" in result.output.lower()
        assert not (pack_dir / "layoutscontainer-Test_Layout.json").exists()

    @patch("xsoar_cli.xsoar_client.client.Client.test_connectivity", return_value=True)
    @patch("xsoar_cli.xsoar_client.content.Content.download_layout")
    def test_missing_dir_fallback_to_cwd(self, mock_download, mock_connectivity, mock_config_file, tmp_path, monkeypatch) -> None:  # noqa: ANN001
        monkeypatch.chdir(tmp_path)
        mock_download.return_value = {"id": "test-layout", "name": "Test Layout", "packID": "SomePack"}
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["content", "download", "--type", "layout", "Test Layout"], input="y\ny\n")
        assert result.exit_code == 0
        assert (tmp_path / "layoutscontainer-Test_Layout.json").exists()

    @patch("xsoar_cli.xsoar_client.client.Client.test_connectivity", return_value=True)
    @patch("xsoar_cli.xsoar_client.content.Content.download_layout")
    def test_missing_dir_decline_fallback(self, mock_download, mock_connectivity, mock_config_file, tmp_path, monkeypatch) -> None:  # noqa: ANN001
        monkeypatch.chdir(tmp_path)
        mock_download.return_value = {"id": "test-layout", "name": "Test Layout", "packID": "SomePack"}
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["content", "download", "--type", "layout", "Test Layout"], input="n\n")
        assert result.exit_code == 0
        assert "discarded" in result.output.lower()

    @patch("xsoar_cli.xsoar_client.client.Client.test_connectivity", return_value=True)
    @patch("xsoar_cli.xsoar_client.content.Content.download_layout")
    def test_download_failure(self, mock_download, mock_connectivity, mock_config_file) -> None:  # noqa: ANN001
        mock_download.side_effect = ValueError("Layout 'Nonexistent' not found")
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["content", "download", "--type", "layout", "Nonexistent"])
        assert result.exit_code == 1
        assert "FAILED" in result.output
        assert "Layout 'Nonexistent' not found" in result.output

    @patch("xsoar_cli.xsoar_client.client.Client.test_connectivity", return_value=True)
    @patch("xsoar_cli.xsoar_client.content.Content.download_layout")
    def test_output_option_writes_to_specified_path(self, mock_download, mock_connectivity, mock_config_file, tmp_path) -> None:  # noqa: ANN001
        repo_root = tmp_path / "my-repo"
        pack_dir = repo_root / "Packs" / "SomePack" / "Layouts"
        pack_dir.mkdir(parents=True)
        existing = pack_dir / "layoutscontainer-Test_Layout.json"
        existing.write_text("{}")
        mock_download.return_value = {"id": "test-layout", "name": "Test Layout", "packID": "SomePack"}
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["content", "download", "--type", "layout", "--output", str(repo_root), "Test Layout"])
        assert result.exit_code == 0
        assert '"name": "Test Layout"' in existing.read_text()


class TestContentDownloadMissingType:
    def test_download_missing_type(self, mock_config_file) -> None:  # noqa: ANN001
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["content", "download", "SomeName"])
        assert result.exit_code != 0
        assert "Missing option '--type'" in result.output


class TestResolveOutputPath:
    """Tests for the _resolve_output_path helper."""

    def test_file_exists_returns_path(self, tmp_path) -> None:
        """Existing file: return path immediately (overwrite case)."""
        target_dir = tmp_path / "Packs" / "MyPack" / "Playbooks"
        target_dir.mkdir(parents=True)
        existing = target_dir / "playbook.yml"
        existing.write_text("old")
        result = _resolve_output_path("MyPack", "Playbooks", "playbook.yml", cwd=tmp_path)
        assert result == existing

    def test_dir_exists_file_missing_confirm_yes(self, tmp_path) -> None:
        target_dir = tmp_path / "Packs" / "MyPack" / "Playbooks"
        target_dir.mkdir(parents=True)
        with patch("xsoar_cli.commands.content.commands.click.confirm", return_value=True):
            result = _resolve_output_path("MyPack", "Playbooks", "playbook.yml", cwd=tmp_path)
        assert result == target_dir / "playbook.yml"

    def test_dir_exists_file_missing_confirm_no(self, tmp_path) -> None:
        target_dir = tmp_path / "Packs" / "MyPack" / "Playbooks"
        target_dir.mkdir(parents=True)
        with patch("xsoar_cli.commands.content.commands.click.confirm", return_value=False):
            result = _resolve_output_path("MyPack", "Playbooks", "playbook.yml", cwd=tmp_path)
        assert result is None

    def test_dir_missing_fallback_to_cwd_and_confirm(self, tmp_path) -> None:
        """Dir missing, user accepts cwd, then confirms new file."""
        with patch("xsoar_cli.commands.content.commands.click.confirm", side_effect=[True, True]):
            result = _resolve_output_path("MissingPack", "Playbooks", "playbook.yml", cwd=tmp_path)
        assert result == tmp_path / "playbook.yml"

    def test_dir_missing_decline_cwd(self, tmp_path) -> None:
        with patch("xsoar_cli.commands.content.commands.click.confirm", return_value=False):
            result = _resolve_output_path("MissingPack", "Playbooks", "playbook.yml", cwd=tmp_path)
        assert result is None

    def test_no_pack_id_uses_cwd(self, tmp_path) -> None:
        """No pack ID: target dir is cwd. File is new, user confirms."""
        with patch("xsoar_cli.commands.content.commands.click.confirm", return_value=True):
            result = _resolve_output_path(None, "Playbooks", "playbook.yml", cwd=tmp_path)
        assert result == tmp_path / "playbook.yml"

    def test_no_pack_id_existing_file_in_cwd(self, tmp_path) -> None:
        """No pack ID, but file already exists in cwd: overwrite silently."""
        existing = tmp_path / "playbook.yml"
        existing.write_text("old")
        result = _resolve_output_path(None, "Playbooks", "playbook.yml", cwd=tmp_path)
        assert result == existing


class TestDownloadPlaybook:
    """Tests for the Content.download_playbook method."""

    def test_direct_download_succeeds(self) -> None:
        mock_client = MagicMock()
        response = MagicMock()
        response.ok = True
        response.content = b"id: test-playbook\nname: Test Playbook\n"
        mock_client.make_request.return_value = response

        content = Content(mock_client)
        result = content.download_playbook("Test Playbook")

        assert result == b"id: test-playbook\nname: Test Playbook\n"
        mock_client.make_request.assert_called_once_with(endpoint="/playbook/Test Playbook/yaml", method="GET")

    def test_fallback_to_id_resolution(self) -> None:
        mock_client = MagicMock()

        # First call (direct download) fails, second call (search) succeeds,
        # third call (download by ID) succeeds.
        direct_response = MagicMock()
        direct_response.ok = False
        direct_response.status_code = 404

        search_response = MagicMock()
        search_response.raise_for_status.return_value = None
        search_response.json.return_value = {
            "playbooks": [
                {"id": "abc-123-uuid", "name": "My Custom Playbook"},
            ],
        }

        resolved_response = MagicMock()
        resolved_response.ok = True
        resolved_response.content = b"id: abc-123-uuid\nname: My Custom Playbook\n"
        resolved_response.raise_for_status.return_value = None

        mock_client.make_request.side_effect = [direct_response, search_response, resolved_response]

        content = Content(mock_client)
        result = content.download_playbook("My Custom Playbook")

        assert result == b"id: abc-123-uuid\nname: My Custom Playbook\n"
        assert mock_client.make_request.call_count == 3

    def test_playbook_not_found(self) -> None:
        mock_client = MagicMock()

        direct_response = MagicMock()
        direct_response.ok = False
        direct_response.status_code = 404

        search_response = MagicMock()
        search_response.raise_for_status.return_value = None
        search_response.json.return_value = {"playbooks": []}

        mock_client.make_request.side_effect = [direct_response, search_response]

        content = Content(mock_client)
        with pytest.raises(ValueError, match="Playbook 'Nonexistent' not found"):
            content.download_playbook("Nonexistent")


class TestResolvePlaybookId:
    """Tests for the Content._resolve_playbook_id method."""

    def test_resolves_matching_name(self) -> None:
        mock_client = MagicMock()
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "playbooks": [
                {"id": "abc-123", "name": "My Playbook"},
                {"id": "def-456", "name": "Other Playbook"},
            ],
        }
        mock_client.make_request.return_value = response

        content = Content(mock_client)
        result = content._resolve_playbook_id("My Playbook")
        assert result == "abc-123"

    def test_case_insensitive_match(self) -> None:
        mock_client = MagicMock()
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "playbooks": [{"id": "abc-123", "name": "My Playbook"}],
        }
        mock_client.make_request.return_value = response

        content = Content(mock_client)
        result = content._resolve_playbook_id("my playbook")
        assert result == "abc-123"

    def test_no_match_returns_none(self) -> None:
        mock_client = MagicMock()
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "playbooks": [{"id": "abc-123", "name": "Other Playbook"}],
        }
        mock_client.make_request.return_value = response

        content = Content(mock_client)
        result = content._resolve_playbook_id("Nonexistent")
        assert result is None

    def test_empty_playbooks_list(self) -> None:
        mock_client = MagicMock()
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"playbooks": None}
        mock_client.make_request.return_value = response

        content = Content(mock_client)
        result = content._resolve_playbook_id("Anything")
        assert result is None


class TestDownloadLayout:
    """Tests for the Content.download_layout method."""

    def test_download_matching_layout(self) -> None:
        mock_client = MagicMock()
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = [
            {"id": "layout-1", "name": "Incident Layout"},
            {"id": "layout-2", "name": "Alert Layout"},
        ]
        mock_client.make_request.return_value = response

        content = Content(mock_client)
        result = content.download_layout("Alert Layout")
        assert result == {"id": "layout-2", "name": "Alert Layout"}

    def test_case_insensitive_match(self) -> None:
        mock_client = MagicMock()
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = [
            {"id": "layout-1", "name": "Incident Layout"},
        ]
        mock_client.make_request.return_value = response

        content = Content(mock_client)
        result = content.download_layout("incident layout")
        assert result == {"id": "layout-1", "name": "Incident Layout"}

    def test_layout_not_found(self) -> None:
        mock_client = MagicMock()
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = [
            {"id": "layout-1", "name": "Incident Layout"},
        ]
        mock_client.make_request.return_value = response

        content = Content(mock_client)
        with pytest.raises(ValueError, match="Layout 'Nonexistent' not found"):
            content.download_layout("Nonexistent")

    def test_empty_layouts_list(self) -> None:
        mock_client = MagicMock()
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = []
        mock_client.make_request.return_value = response

        content = Content(mock_client)
        with pytest.raises(ValueError, match="Layout 'Anything' not found"):
            content.download_layout("Anything")
