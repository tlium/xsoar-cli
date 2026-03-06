from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from requests.exceptions import HTTPError


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
