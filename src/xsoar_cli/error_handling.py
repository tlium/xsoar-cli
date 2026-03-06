from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from requests.exceptions import HTTPError
    from urllib3.exceptions import NameResolutionError


class ConnectionErrorHandler:
    """Extracts actionable error messages from connection exception chains."""

    def get_message(self, exception: BaseException | None) -> str:
        """Return a user-friendly error message from an exception chain."""
        if exception is None:
            return "Unknown error"

        # Lazy import for performance reasons
        from urllib3.exceptions import NameResolutionError

        # Walk through the exception chain to find known error types and the root cause
        current = exception
        hostname = None
        root_cause = None

        while current is not None:
            if isinstance(current, NameResolutionError):
                hostname = self._extract_hostname(current)

            if current.__context__ is not None:
                current = current.__context__
            else:
                root_cause = str(current)
                break

        if hostname and root_cause:
            return f"Failed to resolve '{hostname}' ({root_cause})"

        return root_cause or str(exception)

    @staticmethod
    def _extract_hostname(exception: NameResolutionError) -> str | None:
        """Extract hostname from a NameResolutionError.

        urllib3 does not expose the hostname as an attribute, so we extract it
        from the formatted message: "conn: Failed to resolve 'hostname' (reason)"
        """
        if not exception.args:
            return None

        msg = str(exception.args[0])
        if "Failed to resolve" not in msg or "'" not in msg:
            return None

        start = msg.find("'") + 1
        end = msg.find("'", start)
        if end > start:
            return msg[start:end]
        return None


class HTTPErrorHandler:
    """Maps HTTP error responses to user-friendly messages.

    Messages are organized by status code and context. Each status code maps to
    a dict of context-specific messages. The "_default" key provides a fallback
    for contexts that don't have a specific entry.
    """

    # Extend this dict as new status codes or contexts need specific handling.
    _messages: dict[int, dict[str, str]] = {
        400: {
            "case": "Please verify the case number.",
            "_default": "Please verify that the provided arguments are correct.",
        },
    }

    def get_message(self, exception: HTTPError, *, context: str) -> str:
        """Return a user-friendly error message for an HTTP error response.

        context: identifies the calling operation (e.g. "case", "playbook") so
        the returned message can be tailored to the specific use case.
        """
        status = exception.response.status_code
        url = exception.response.url
        if status in self._messages:
            messages = self._messages[status]
            hint = messages.get(context, messages.get("_default", ""))
            return f"HTTP {status}: Bad request from {url}. {hint}"
        return f"HTTP {status} from {url}: {exception.response.text}"
