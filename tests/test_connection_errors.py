"""Tests for ConnectionErrorHandler.

Covers get_message and _extract_hostname using a single parametrized test method.
Exception objects that require raise/except chains are built by module-level helpers
and passed directly as parameter values.
"""

import socket
from unittest.mock import MagicMock

import pytest
from urllib3.exceptions import NameResolutionError

from xsoar_cli.connection_errors import ConnectionErrorHandler


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


handler = ConnectionErrorHandler()


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
        result = getattr(handler, method)(exception)
        assert result == expected
