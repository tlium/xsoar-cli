from urllib3.exceptions import NameResolutionError


class ConnectionErrorHandler:
    """Extracts actionable error messages from connection exception chains."""

    def get_message(self, exception: BaseException | None) -> str:
        """Return a user-friendly error message from an exception chain."""
        if exception is None:
            return "Unknown error"

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
