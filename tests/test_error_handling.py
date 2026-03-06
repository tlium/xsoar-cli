"""Tests for ConnectionErrorHandler and HTTPErrorHandler.

ConnectionErrorHandler tests cover get_message and _extract_hostname using a single
parametrized test method. Exception objects that require raise/except chains are built
by module-level helpers and passed directly as parameter values.

HTTPErrorHandler tests cover context-aware message mapping for HTTP status codes.
"""

import socket
from unittest.mock import MagicMock

import pytest
from requests.exceptions import HTTPError
from urllib3.exceptions import NameResolutionError

from xsoar_cli.error_handling.connection import ConnectionErrorHandler
from xsoar_cli.error_handling.http import HTTPErrorHandler


def _make_name_resolution_error(hostname: str, reason: str) -> NameResolutionError:
    """Build a NameResolutionError for the given hostname and reason string.

    Uses a MagicMock for the conn argument, with __str__ fixed to 'conn' so the
    formatted message is predictable across test runs.
    """
    conn = MagicMock()
    conn.__str__ = lambda self: "conn"
    return NameResolutionError(hostname, conn, socket.gaierror(reason))


def _chained_name_resolution_error() -> NameResolutionError:
    """Return a NameResolutionError chained from an OSError root cause.

    Represents the realistic urllib3 case where a NameResolutionError wraps a
    lower-level socket error.
    """
    try:
        try:
            raise OSError("nodename nor servname provided, or not known")
        except OSError as root:
            raise _make_name_resolution_error("example.com", "nodename nor servname provided, or not known") from root
    except NameResolutionError as exc:
        return exc


def _chained_without_name_resolution_error() -> RuntimeError:
    """Return a RuntimeError chained from an OSError root cause, with no NameResolutionError in the chain.

    Used to verify that get_message falls back to the root cause string when no
    hostname can be extracted.
    """
    try:
        try:
            raise OSError("connection refused")
        except OSError as root:
            raise RuntimeError("operation failed") from root
    except RuntimeError as exc:
        return exc


def _name_resolution_error_no_args() -> NameResolutionError:
    """Return a NameResolutionError with an empty args tuple.

    Bypasses the normal constructor to simulate a malformed exception object,
    used to verify that _extract_hostname handles missing args gracefully.
    """
    exc = NameResolutionError.__new__(NameResolutionError)
    exc.args = ()
    return exc


def _name_resolution_error_with_message(message: str) -> NameResolutionError:
    """Return a NameResolutionError with args set to the given message string.

    Bypasses the normal constructor so arbitrary message content can be injected,
    used to test _extract_hostname's message parsing edge cases.
    """
    exc = NameResolutionError.__new__(NameResolutionError)
    exc.args = (message,)
    return exc


connection_handler = ConnectionErrorHandler()
http_handler = HTTPErrorHandler()


def _make_http_error(status_code: int, text: str = "", url: str = "https://xsoar.example.com/incident/load/99999") -> HTTPError:
    """Build an HTTPError with a mock response carrying the given status code, body text, and URL."""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.text = text
    mock_response.url = url
    return HTTPError(response=mock_response)


class TestConnectionErrorHandler:
    """Tests for ConnectionErrorHandler.

    Both get_message and _extract_hostname are exercised through a single
    parametrized method. The method column selects which handler method to call
    via getattr, keeping all cases in one place.
    """

    @pytest.mark.parametrize(
        ("method", "exception", "expected"),
        [
            # get_message: simple cases
            ("get_message", None, "Unknown error"),
            ("get_message", ValueError("something went wrong"), "something went wrong"),
            # get_message: exception chain without NameResolutionError
            ("get_message", _chained_without_name_resolution_error(), "connection refused"),
            # get_message: NameResolutionError with chained root cause
            (
                "get_message",
                _chained_name_resolution_error(),
                "Failed to resolve 'example.com' (nodename nor servname provided, or not known)",
            ),
            # _extract_hostname: valid hostnames
            (
                "_extract_hostname",
                _make_name_resolution_error("example.com", "nodename nor servname provided, or not known"),
                "example.com",
            ),
            ("_extract_hostname", _make_name_resolution_error("my-host.internal", "Name or service not known"), "my-host.internal"),
            # _extract_hostname: no args
            ("_extract_hostname", _name_resolution_error_no_args(), None),
            # _extract_hostname: message without "Failed to resolve"
            ("_extract_hostname", _name_resolution_error_with_message("some unrelated error message"), None),
            ("_extract_hostname", _name_resolution_error_with_message("conn: Could not connect to host"), None),
            # _extract_hostname: malformed quotes
            ("_extract_hostname", _name_resolution_error_with_message("conn: Failed to resolve 'example.com"), None),
        ],
    )
    def test_connection_error_handler(self, method: str, exception: BaseException | None, expected: str | None) -> None:
        """Invoke the named handler method with exception and assert the result matches expected.

        method:    name of the ConnectionErrorHandler method to call
        exception: exception instance (or None) passed as the sole argument
        expected:  expected return value; None for _extract_hostname failure cases
        """
        result = getattr(connection_handler, method)(exception)
        assert result == expected


class TestHTTPErrorHandler:
    """Tests for HTTPErrorHandler.

    Exercises get_message with various status codes and context values to verify
    context-specific messages, default fallbacks, and the generic catch-all.
    """

    @pytest.mark.parametrize(
        ("status_code", "text", "context", "expected"),
        [
            # 400 with matching context
            (
                400,
                "Bad Request",
                "case",
                "HTTP 400: Bad request from https://xsoar.example.com/incident/load/99999. Please verify the case number.",
            ),
            # 400 with unknown context falls back to _default
            (
                400,
                "Bad Request",
                "unknown_context",
                "HTTP 400: Bad request from https://xsoar.example.com/incident/load/99999. Please verify that the provided arguments are correct.",
            ),
            # Unknown status code falls through to generic message
            (500, "Internal Server Error", "case", "HTTP 500 from https://xsoar.example.com/incident/load/99999: Internal Server Error"),
            (403, "Forbidden", "case", "HTTP 403 from https://xsoar.example.com/incident/load/99999: Forbidden"),
            # Generic fallback with empty body
            (502, "", "case", "HTTP 502 from https://xsoar.example.com/incident/load/99999: "),
        ],
    )
    def test_http_error_handler(self, status_code: int, text: str, context: str, expected: str) -> None:
        """Verify that get_message returns the correct message for a given status code and context."""
        exception = _make_http_error(status_code, text)
        result = http_handler.get_message(exception, context=context)
        assert result == expected
