from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from xsoar_cli import cli
from xsoar_cli.xsoar_client.content import Content


class TestContentDownloadCommand:
    """Tests for the `content download` CLI command."""

    @patch("xsoar_cli.xsoar_client.client.Client.test_connectivity", return_value=True)
    @patch("xsoar_cli.xsoar_client.content.Content.download_playbook")
    def test_download_playbook(self, mock_download, mock_connectivity, mock_config_file, tmp_path, monkeypatch) -> None:  # noqa: ANN001
        monkeypatch.chdir(tmp_path)
        mock_download.return_value = b"id: test-playbook\nname: Test Playbook\n"
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["content", "download", "--type", "playbook", "Test Playbook"])
        assert result.exit_code == 0
        assert "ok." in result.output
        output_file = tmp_path / "Test_Playbook.yml"
        assert output_file.exists()
        assert output_file.read_bytes() == b"id: test-playbook\nname: Test Playbook\n"

    @patch("xsoar_cli.xsoar_client.client.Client.test_connectivity", return_value=True)
    @patch("xsoar_cli.xsoar_client.content.Content.download_playbook")
    def test_download_playbook_spaces_in_name(self, mock_download, mock_connectivity, mock_config_file, tmp_path, monkeypatch) -> None:  # noqa: ANN001
        monkeypatch.chdir(tmp_path)
        mock_download.return_value = b"id: my-playbook\nname: My Cool Playbook\n"
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["content", "download", "--type", "playbook", "My Cool Playbook"])
        assert result.exit_code == 0
        output_file = tmp_path / "My_Cool_Playbook.yml"
        assert output_file.exists()

    @patch("xsoar_cli.xsoar_client.client.Client.test_connectivity", return_value=True)
    @patch("xsoar_cli.xsoar_client.content.Content.download_playbook")
    def test_download_playbook_failure(self, mock_download, mock_connectivity, mock_config_file) -> None:  # noqa: ANN001
        mock_download.side_effect = ValueError("Playbook 'Nonexistent' not found")
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["content", "download", "--type", "playbook", "Nonexistent"])
        assert result.exit_code == 1
        assert "FAILED" in result.output
        assert "Playbook 'Nonexistent' not found" in result.output

    def test_download_missing_type(self, mock_config_file) -> None:  # noqa: ANN001
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["content", "download", "SomeName"])
        assert result.exit_code != 0
        assert "Missing option '--type'" in result.output


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
