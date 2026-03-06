from unittest.mock import MagicMock, patch

import pytest
from requests.exceptions import HTTPError

from xsoar_cli.utilities import get_config_file_template_contents


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
def mock_xsoar_client_get_case_http_error():  # noqa: ANN201
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "Bad Request"
    mock_response.url = "https://xsoar.example.com/incident/load/99999"
    with patch("xsoar_client.xsoar_client.Client.get_case") as mock_get_error:
        mock_get_error.side_effect = HTTPError(response=mock_response)
        yield mock_get_error


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
