"""Fixtures for direct unit tests (no CliRunner).

These fixtures provide lightweight mocks for testing domain classes,
handlers, and utilities in isolation.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def load_test_data():  # noqa: ANN201
    """Load a JSON fixture from the fixtures directory by relative path."""

    def _load(relative_path: str) -> dict | list:
        path = _FIXTURES_DIR / relative_path
        return json.loads(path.read_text())

    return _load


@pytest.fixture
def mock_client() -> MagicMock:
    """Return a plain MagicMock standing in for ``xsoar_cli.xsoar_client.client.Client``.

    Tests can configure return values or side effects on the mock before
    passing it to domain class constructors::

        def test_download(mock_client):
            response = MagicMock(ok=True, content=b"data")
            mock_client.make_request.return_value = response
            content = Content(mock_client)
            result = content.download_playbook("My Playbook")
    """
    return MagicMock()
