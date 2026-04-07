"""Root conftest. Fixtures defined here are available to both cli/ and unit/ tests."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from requests.exceptions import HTTPError

from xsoar_cli.commands.config.commands import get_config_file_template_contents

if TYPE_CHECKING:
    from collections.abc import Iterator


# ---------------------------------------------------------------------------
# Config file mock
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_config_file() -> Iterator[MagicMock]:  # noqa: ANN201
    """Patch config file I/O so commands see the built-in template config.

    Also patches ``Path.is_file`` so that ``read_config_file`` treats the
    config file as present on disk.
    """
    with (
        patch("xsoar_cli.utilities.config_file.get_config_file_contents") as mock_get_config,
        patch("pathlib.Path.is_file", return_value=True),
    ):
        mock_get_config.return_value = get_config_file_template_contents()
        yield mock_get_config


# ---------------------------------------------------------------------------
# XSOAR client factory
# ---------------------------------------------------------------------------


@pytest.fixture
def make_mock_client():  # noqa: ANN201
    """Factory fixture that builds a mock XSOAR client with configurable behavior.

    Returns a callable. Keyword arguments:

    * ``connectivity_ok`` (bool, default True) -- whether ``test_connectivity``
      succeeds or raises ``ConnectionError``.
    * ``artifacts_ok`` (bool, default True) -- whether the artifact provider's
      ``test_connection`` succeeds or raises.

    Example::

        def test_something(make_mock_client):
            client = make_mock_client(connectivity_ok=False)
            assert client.test_connectivity.side_effect is not None
    """

    def _factory(*, connectivity_ok: bool = True, artifacts_ok: bool = True) -> MagicMock:
        instance = MagicMock()
        if connectivity_ok:
            instance.test_connectivity.return_value = True
        else:
            instance.test_connectivity.side_effect = ConnectionError("Connection refused")

        provider = MagicMock()
        if artifacts_ok:
            provider.test_connection.return_value = True
        else:
            provider.test_connection.side_effect = Exception("Artifact connection failed")
        instance.artifact_provider = provider

        return instance

    return _factory


# ---------------------------------------------------------------------------
# HTTP error factory
# ---------------------------------------------------------------------------


@pytest.fixture
def make_http_error():  # noqa: ANN201
    """Factory fixture that builds an ``HTTPError`` with a mock response.

    Returns a callable accepting ``status_code``, ``text``, and ``url``.

    Example::

        def test_bad_request(make_http_error):
            err = make_http_error(400, text="Bad Request")
    """

    def _factory(
        status_code: int,
        text: str = "",
        url: str = "https://xsoar.example.com/incident/load/99999",
    ) -> HTTPError:
        response = MagicMock()
        response.status_code = status_code
        response.text = text
        response.url = url
        return HTTPError(response=response)

    return _factory


# ---------------------------------------------------------------------------
# Case response factory
# ---------------------------------------------------------------------------

_CASE_MIRROR_DEFAULTS: dict[str, str] = {
    "dbotMirrorId": "placeholder",
    "dbotMirrorInstance": "placeholder",
    "dbotMirrorDirection": "placeholder",
    "dbotDirtyFields": "placeholder",
    "dbotCurrentDirtyFields": "placeholder",
    "dbotMirrorTags": "placeholder",
    "dbotMirrorLastSync": "placeholder",
}


@pytest.fixture
def make_case_response():  # noqa: ANN201
    """Factory fixture that builds case API response dicts.

    Returns a callable. Keyword arguments are merged into the case dict,
    so callers can override any field.

    Example::

        def test_case(make_case_response):
            single = make_case_response()
            empty  = make_case_response(total=0, data=[])
    """

    def _factory(
        *,
        name: str = "This is a test",
        case_id: str = "66666666",
        total: int = 1,
        **overrides: object,
    ) -> dict:
        case: dict = {
            "name": name,
            "id": case_id,
            "created": "2024-01-01T00:00:00Z",
            "modified": "2024-01-01T00:00:00Z",
            "details": "test details",
            **_CASE_MIRROR_DEFAULTS,
        }
        case.update(overrides)
        if "data" in overrides:
            return {"total": total, "data": overrides["data"]}
        return {"total": total, "data": [case]}

    return _factory


@pytest.fixture
def make_case_create_response():  # noqa: ANN201
    """Factory fixture that builds a case-creation response dict."""

    def _factory(
        *,
        name: str = "This is a test",
        case_id: str = "66666666",
        **overrides: object,
    ) -> dict:
        case: dict = {
            "name": name,
            "id": case_id,
            "created": "2024-01-01T00:00:00Z",
            "details": "test details",
            **_CASE_MIRROR_DEFAULTS,
        }
        case.update(overrides)
        return case

    return _factory
