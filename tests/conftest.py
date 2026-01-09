import json
from pathlib import Path
from unittest.mock import patch

import pytest

from xsoar_cli.utilities import get_config_file_template_contents


@pytest.fixture
def mock_manifest_base():
    """Fixture that loads the valid base manifest file."""
    manifest_path = Path(__file__).parent / "test_data" / "manifest_base.json"
    with patch("xsoar_cli.manifest.commands.load_manifest") as mock_load_manifest:
        with manifest_path.open("r") as f:
            mock_load_manifest.return_value = json.load(f)
        yield mock_load_manifest


@pytest.fixture
def mock_manifest_invalid():
    """Fixture that simulates loading an invalid manifest (JSON decode error)."""
    with patch("xsoar_cli.manifest.commands.load_manifest") as mock_load_manifest:
        mock_load_manifest.side_effect = SystemExit(1)
        yield mock_load_manifest


@pytest.fixture
def mock_manifest_with_pack_not_on_server():
    """Fixture that loads the manifest with a pack not on the server."""
    manifest_path = Path(__file__).parent / "test_data" / "manifest_with_pack_not_on_server.json"
    with patch("xsoar_cli.manifest.commands.load_manifest") as mock_load_manifest:
        with manifest_path.open("r") as f:
            mock_load_manifest.return_value = json.load(f)
        yield mock_load_manifest


@pytest.fixture
def mock_xsoar_client_is_pack_available():
    """Fixture that mocks the is_pack_available method to return True for all packs."""
    with patch("xsoar_client.xsoar_client.Client.is_pack_available") as mock_is_available:
        mock_is_available.return_value = True
        yield mock_is_available


@pytest.fixture
def mock_config_file():  # noqa: ANN201
    with patch("xsoar_cli.utilities.get_config_file_contents") as mock_get_config:
        mock_get_config.return_value = get_config_file_template_contents()
        yield mock_get_config


@pytest.fixture
def mock_xsoar_client_create_case():  # noqa: ANN201
    with patch("xsoar_client.xsoar_client.Client.create_case") as mock_create:
        mock_create.return_value = {
            "name": "This is a test",
            "id": "66666666",
            "created": "asdfasdf",
            "details": "sdfad",
            "dbotMirrorId": "placeholder",
            "dbotMirrorInstance": "placeholder",
            "dbotMirrorDirection": "placeholder",
            "dbotDirtyFields": "placeholder",
            "dbotCurrentDirtyFields": "placeholder",
            "dbotMirrorTags": "placeholder",
            "dbotMirrorLastSync": "placeholder",
        }
        yield mock_create


@pytest.fixture
def mock_xsoar_client_get_case_zero():  # noqa: ANN201
    with patch("xsoar_client.xsoar_client.Client.get_case") as mock_get_zero:
        mock_get_zero.return_value = {
            "total": 0,
            "data": [],
        }
        yield mock_get_zero


@pytest.fixture
def mock_xsoar_client_get_case():  # noqa: ANN201
    with patch("xsoar_client.xsoar_client.Client.get_case") as mock_get:
        mock_get.return_value = {
            "total": 1,
            "data": [
                {
                    "name": "This is a test",
                    "id": "66666666",
                    "modified": "asdfadsfs",
                    "created": "asdfasdf",
                    "details": "sdfad",
                    "dbotMirrorId": "placeholder",
                    "dbotMirrorInstance": "placeholder",
                    "dbotMirrorDirection": "placeholder",
                    "dbotDirtyFields": "placeholder",
                    "dbotCurrentDirtyFields": "placeholder",
                    "dbotMirrorTags": "placeholder",
                    "dbotMirrorLastSync": "placeholder",
                },
            ],
        }
        yield mock_get
