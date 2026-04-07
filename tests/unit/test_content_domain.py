from unittest.mock import MagicMock

import pytest

from xsoar_cli.xsoar_client.content import Content


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
