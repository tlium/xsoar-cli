import tarfile
from io import BytesIO
from unittest.mock import MagicMock

import pytest
from requests.exceptions import HTTPError

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


# ===========================================================================
# Content.get_bundle
# ===========================================================================


def _make_tarball(files: dict[str, str]) -> bytes:
    """Build an in-memory tar.gz containing the given filename->content pairs."""
    buf = BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, data in files.items():
            encoded = data.encode("utf-8")
            info = tarfile.TarInfo(name=name)
            info.size = len(encoded)
            tar.addfile(info, BytesIO(encoded))
    return buf.getvalue()


class TestGetBundle:
    """Tests for the Content.get_bundle method."""

    def test_extracts_files_from_tarball(self) -> None:
        tarball = _make_tarball(
            {
                "playbook-Test.yml": "id: test-playbook\nname: Test\n",
                "script-Helper.yml": "id: helper\ncomment: A helper script\n",
            }
        )
        mock_client = MagicMock()
        response = MagicMock()
        response.content = tarball
        mock_client.make_request.return_value = response

        content = Content(mock_client)
        result = content.get_bundle()

        assert "playbook-Test.yml" in result
        assert "script-Helper.yml" in result
        assert result["playbook-Test.yml"].read() == "id: test-playbook\nname: Test\n"

    def test_calls_correct_endpoint(self) -> None:
        tarball = _make_tarball({"empty.yml": ""})
        mock_client = MagicMock()
        response = MagicMock()
        response.content = tarball
        mock_client.make_request.return_value = response

        content = Content(mock_client)
        content.get_bundle()

        mock_client.make_request.assert_called_once_with(endpoint="/content/bundle", method="GET")

    def test_empty_tarball(self) -> None:
        buf = BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz"):
            pass
        mock_client = MagicMock()
        response = MagicMock()
        response.content = buf.getvalue()
        mock_client.make_request.return_value = response

        content = Content(mock_client)
        result = content.get_bundle()

        assert result == {}


# ===========================================================================
# Content.get_detached
# ===========================================================================


class TestGetDetached:
    """Tests for the Content.get_detached method."""

    def test_scripts_endpoint(self) -> None:
        mock_client = MagicMock()
        response = MagicMock()
        response.raise_for_status.return_value = None
        mock_client.make_request.return_value = response

        content = Content(mock_client)
        content.get_detached("scripts")

        mock_client.make_request.assert_called_once_with(
            endpoint="/automation/search",
            method="POST",
            json={"query": "system:T"},
        )

    def test_playbooks_endpoint(self) -> None:
        mock_client = MagicMock()
        response = MagicMock()
        response.raise_for_status.return_value = None
        mock_client.make_request.return_value = response

        content = Content(mock_client)
        content.get_detached("playbooks")

        mock_client.make_request.assert_called_once_with(
            endpoint="/playbook/search",
            method="POST",
            json={"query": "system:T"},
        )

    def test_calls_raise_for_status(self) -> None:
        mock_client = MagicMock()
        response = MagicMock()
        response.raise_for_status.return_value = None
        mock_client.make_request.return_value = response

        content = Content(mock_client)
        content.get_detached("scripts")

        response.raise_for_status.assert_called_once()

    def test_invalid_content_type_raises(self) -> None:
        mock_client = MagicMock()
        content = Content(mock_client)
        with pytest.raises(ValueError, match="Invalid value"):
            content.get_detached("invalid")

    def test_none_content_type_raises(self) -> None:
        mock_client = MagicMock()
        content = Content(mock_client)
        with pytest.raises(ValueError, match="Invalid value"):
            content.get_detached(None)

    def test_http_error_propagates(self) -> None:
        mock_client = MagicMock()
        response = MagicMock()
        response.raise_for_status.side_effect = HTTPError("500 Server Error")
        mock_client.make_request.return_value = response

        content = Content(mock_client)
        with pytest.raises(HTTPError, match="500 Server Error"):
            content.get_detached("scripts")


# ===========================================================================
# Content.download_item
# ===========================================================================


class TestDownloadItem:
    """Tests for the Content.download_item method."""

    def test_playbook_happy_path(self) -> None:
        mock_client = MagicMock()
        response = MagicMock()
        response.content = b"id: my-playbook\nname: My Playbook\n"
        response.raise_for_status.return_value = None
        mock_client.make_request.return_value = response

        content = Content(mock_client)
        result = content.download_item("playbook", "my-playbook")

        assert result == b"id: my-playbook\nname: My Playbook\n"
        mock_client.make_request.assert_called_once_with(endpoint="/playbook/my-playbook/yaml", method="GET")

    def test_calls_raise_for_status(self) -> None:
        mock_client = MagicMock()
        response = MagicMock()
        response.content = b"data"
        response.raise_for_status.return_value = None
        mock_client.make_request.return_value = response

        content = Content(mock_client)
        content.download_item("playbook", "test-id")

        response.raise_for_status.assert_called_once()

    def test_unsupported_type_raises(self) -> None:
        mock_client = MagicMock()
        content = Content(mock_client)
        with pytest.raises(ValueError, match="Unknown item_type"):
            content.download_item("script", "some-id")

    def test_http_error_propagates(self) -> None:
        mock_client = MagicMock()
        response = MagicMock()
        response.raise_for_status.side_effect = HTTPError("404 Not Found")
        mock_client.make_request.return_value = response

        content = Content(mock_client)
        with pytest.raises(HTTPError, match="404 Not Found"):
            content.download_item("playbook", "nonexistent")


# ===========================================================================
# Content.attach_item
# ===========================================================================


class TestAttachItem:
    """Tests for the Content.attach_item method."""

    def test_playbook(self) -> None:
        mock_client = MagicMock()
        response = MagicMock()
        response.raise_for_status.return_value = None
        mock_client.make_request.return_value = response

        content = Content(mock_client)
        content.attach_item("playbook", "my-playbook-id")

        mock_client.make_request.assert_called_once_with(endpoint="/playbook/attach/my-playbook-id", method="POST")

    def test_layout(self) -> None:
        mock_client = MagicMock()
        response = MagicMock()
        response.raise_for_status.return_value = None
        mock_client.make_request.return_value = response

        content = Content(mock_client)
        content.attach_item("layout", "my-layout-id")

        mock_client.make_request.assert_called_once_with(endpoint="/layout/my-layout-id/attach", method="POST")

    def test_calls_raise_for_status(self) -> None:
        mock_client = MagicMock()
        response = MagicMock()
        response.raise_for_status.return_value = None
        mock_client.make_request.return_value = response

        content = Content(mock_client)
        content.attach_item("playbook", "test-id")

        response.raise_for_status.assert_called_once()

    def test_unsupported_type_raises(self) -> None:
        mock_client = MagicMock()
        content = Content(mock_client)
        with pytest.raises(ValueError, match='Unknown item_type "script"'):
            content.attach_item("script", "some-id")

    def test_http_error_propagates(self) -> None:
        mock_client = MagicMock()
        response = MagicMock()
        response.raise_for_status.side_effect = HTTPError("500 Server Error")
        mock_client.make_request.return_value = response

        content = Content(mock_client)
        with pytest.raises(HTTPError, match="500 Server Error"):
            content.attach_item("playbook", "test-id")


# ===========================================================================
# Content.detach_item
# ===========================================================================


class TestDetachItem:
    """Tests for the Content.detach_item method."""

    def test_playbook(self) -> None:
        mock_client = MagicMock()
        response = MagicMock()
        response.raise_for_status.return_value = None
        mock_client.make_request.return_value = response

        content = Content(mock_client)
        content.detach_item("playbook", "my-playbook-id")

        mock_client.make_request.assert_called_once_with(endpoint="/playbook/detach/my-playbook-id", method="POST")

    def test_layout(self) -> None:
        mock_client = MagicMock()
        response = MagicMock()
        response.raise_for_status.return_value = None
        mock_client.make_request.return_value = response

        content = Content(mock_client)
        content.detach_item("layout", "my-layout-id")

        mock_client.make_request.assert_called_once_with(endpoint="/layout/my-layout-id/detach", method="POST")

    def test_calls_raise_for_status(self) -> None:
        mock_client = MagicMock()
        response = MagicMock()
        response.raise_for_status.return_value = None
        mock_client.make_request.return_value = response

        content = Content(mock_client)
        content.detach_item("playbook", "test-id")

        response.raise_for_status.assert_called_once()

    def test_unsupported_type_raises(self) -> None:
        mock_client = MagicMock()
        content = Content(mock_client)
        with pytest.raises(ValueError, match='Unknown item_type "script"'):
            content.detach_item("script", "some-id")

    def test_http_error_propagates(self) -> None:
        mock_client = MagicMock()
        response = MagicMock()
        response.raise_for_status.side_effect = HTTPError("500 Server Error")
        mock_client.make_request.return_value = response

        content = Content(mock_client)
        with pytest.raises(HTTPError, match="500 Server Error"):
            content.detach_item("playbook", "test-id")


# ===========================================================================
# Content._list_playbooks / _list_scripts / _list_commands
# ===========================================================================


_PLAYBOOK_SEARCH_RESPONSE = {
    "playbooks": [
        {"id": "pb-uuid-1", "name": "Phishing Investigation", "deprecated": False, "hidden": False},
        {"id": "pb-uuid-2", "name": "Malware Investigation", "deprecated": False, "hidden": False},
    ],
}

_AUTOMATION_SEARCH_RESPONSE = {
    "scripts": [
        {"id": "SetAndHandleEmpty", "name": "SetAndHandleEmpty", "comment": "Set a value"},
        {"id": "Print", "name": "Print", "comment": "Prints text"},
    ],
}

_USER_COMMANDS_RESPONSE = [
    {"brand": "EWS v2", "name": "EWS_Main", "commands": [{"name": "ews-search-mailbox"}]},
    {"brand": "VirusTotal", "name": "VT_Prod", "commands": [{"name": "vt-file-scan"}]},
]


class TestListPlaybooks:
    """Tests for the Content._list_playbooks method."""

    def test_happy_path(self) -> None:
        mock_client = MagicMock()
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = _PLAYBOOK_SEARCH_RESPONSE
        mock_client.make_request.return_value = response

        content = Content(mock_client)
        result = content._list_playbooks()

        assert len(result) == 2
        assert result[0]["name"] == "Phishing Investigation"
        mock_client.make_request.assert_called_once_with(
            endpoint="/playbook/search",
            json={"query": "hidden:F AND deprecated:F"},
            method="POST",
        )

    def test_http_error_propagates(self) -> None:
        mock_client = MagicMock()
        response = MagicMock()
        response.raise_for_status.side_effect = HTTPError("500 Server Error")
        mock_client.make_request.return_value = response

        content = Content(mock_client)
        with pytest.raises(HTTPError):
            content._list_playbooks()


class TestListScripts:
    """Tests for the Content._list_scripts method."""

    def test_happy_path(self) -> None:
        mock_client = MagicMock()
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = _AUTOMATION_SEARCH_RESPONSE
        mock_client.make_request.return_value = response

        content = Content(mock_client)
        result = content._list_scripts()

        assert len(result) == 2
        assert result[0]["id"] == "SetAndHandleEmpty"
        mock_client.make_request.assert_called_once_with(
            endpoint="/automation/search",
            json={"query": "", "stripContext": False},
            method="POST",
        )

    def test_http_error_propagates(self) -> None:
        mock_client = MagicMock()
        response = MagicMock()
        response.raise_for_status.side_effect = HTTPError("500 Server Error")
        mock_client.make_request.return_value = response

        content = Content(mock_client)
        with pytest.raises(HTTPError):
            content._list_scripts()


class TestListCommands:
    """Tests for the Content._list_commands method."""

    def test_happy_path(self) -> None:
        mock_client = MagicMock()
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = _USER_COMMANDS_RESPONSE
        mock_client.make_request.return_value = response

        content = Content(mock_client)
        result = content._list_commands()

        assert len(result) == 2
        assert result[0]["brand"] == "EWS v2"
        mock_client.make_request.assert_called_once_with(endpoint="/user/commands", method="GET")

    def test_http_error_propagates(self) -> None:
        mock_client = MagicMock()
        response = MagicMock()
        response.raise_for_status.side_effect = HTTPError("500 Server Error")
        mock_client.make_request.return_value = response

        content = Content(mock_client)
        with pytest.raises(HTTPError):
            content._list_commands()


# ===========================================================================
# Content.list (dispatcher)
# ===========================================================================


class TestContentList:
    """Tests for the Content.list dispatcher method."""

    def test_list_playbooks(self) -> None:
        mock_client = MagicMock()
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = _PLAYBOOK_SEARCH_RESPONSE
        mock_client.make_request.return_value = response

        content = Content(mock_client)
        result = content.list("playbooks")

        assert result == _PLAYBOOK_SEARCH_RESPONSE["playbooks"]

    def test_list_scripts(self) -> None:
        mock_client = MagicMock()
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = _AUTOMATION_SEARCH_RESPONSE
        mock_client.make_request.return_value = response

        content = Content(mock_client)
        result = content.list("scripts")

        assert result == _AUTOMATION_SEARCH_RESPONSE["scripts"]

    def test_list_commands(self) -> None:
        mock_client = MagicMock()
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = _USER_COMMANDS_RESPONSE
        mock_client.make_request.return_value = response

        content = Content(mock_client)
        result = content.list("commands")

        assert result == _USER_COMMANDS_RESPONSE

    def test_list_all(self) -> None:
        mock_client = MagicMock()

        pb_response = MagicMock()
        pb_response.raise_for_status.return_value = None
        pb_response.json.return_value = _PLAYBOOK_SEARCH_RESPONSE

        script_response = MagicMock()
        script_response.raise_for_status.return_value = None
        script_response.json.return_value = _AUTOMATION_SEARCH_RESPONSE

        cmd_response = MagicMock()
        cmd_response.raise_for_status.return_value = None
        cmd_response.json.return_value = _USER_COMMANDS_RESPONSE

        mock_client.make_request.side_effect = [pb_response, script_response, cmd_response]

        content = Content(mock_client)
        result = content.list("all")

        assert isinstance(result, dict)
        assert set(result.keys()) == {"playbooks", "scripts", "commands"}
        assert result["playbooks"] == _PLAYBOOK_SEARCH_RESPONSE["playbooks"]
        assert result["scripts"] == _AUTOMATION_SEARCH_RESPONSE["scripts"]
        assert result["commands"] == _USER_COMMANDS_RESPONSE

    def test_invalid_type_raises(self) -> None:
        mock_client = MagicMock()
        content = Content(mock_client)
        with pytest.raises(ValueError, match="invalid argument"):
            content.list("invalid")
