from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .client import Client

logger = logging.getLogger(__name__)

# XSOAR investigation type identifier for playgrounds.
PLAYGROUND_INVESTIGATION_TYPE = 9

# Valid execution modes for execute_command.
EXECUTION_MODES = ("sync", "async")


def _format_arg_value(value: str) -> str:
    """Format a single argument value for a War Room command string.

    Values containing whitespace are wrapped in double quotes for friendliness,
    so the caller does not have to quote them. Embedded double quotes are
    escaped as \\". Values without whitespace are passed through verbatim.
    """
    if any(char.isspace() for char in value):
        escaped = value.replace('"', '\\"')
        return f'"{escaped}"'
    return value


def build_command_string(name: str, args: dict[str, str]) -> str:
    """Build a War Room command string of the form '!name key=value ...'.

    The leading '!' is added if not already present. Argument values that
    contain whitespace are automatically quoted.
    """
    command = name if name.startswith("!") else f"!{name}"
    parts = [command]
    parts.extend(f"{key}={_format_arg_value(value)}" for key, value in args.items())
    return " ".join(parts)


class Execution:
    def __init__(self, client: Client) -> None:
        self.client = client

    def _playground_filter(self, page: int = 0) -> dict:
        """Build the search filter for playground investigations on a given page."""
        return {"filter": {"type": [PLAYGROUND_INVESTIGATION_TYPE], "page": page}}

    def _current_username(self) -> str:
        """Resolve the username tied to the current API token.

        Used to disambiguate when more than one playground is visible to the
        token. Raises RuntimeError if the username cannot be determined.
        """
        logger.debug("Resolving current username via GET /user to disambiguate playgrounds")
        user_data, status_code, _ = self.client.demisto_py_instance.generic_request(
            path="/user",
            method="GET",
            content_type="application/json",
            response_type=object,
        )
        if status_code != 200:  # noqa: PLR2004
            msg = f"Could not determine the current user (GET /user returned status {status_code})"
            raise RuntimeError(msg)
        username = user_data.get("username")
        logger.debug("Resolved current username: %s", username)
        return username

    def resolve_playground_id(self) -> str:
        """Resolves the current user's playground investigation ID.

        Used when no case ID is supplied, so that scripts, integration commands,
        and playbooks can be executed against the user's playground by default.

        Mirrors the resolution logic in demisto-sdk: search investigations of
        the playground type, and when several are visible to the token, filter
        them down to the one created by the current user.

        Raises RuntimeError when the API calls succeed but no single playground
        can be identified. The demisto-py ApiException propagates unchanged when
        an API call itself fails.
        """
        logger.debug("Searching for playground investigations (type %d)", PLAYGROUND_INVESTIGATION_TYPE)
        answer = self.client.demisto_py_instance.search_investigations(filter=self._playground_filter())
        logger.debug("Playground search returned total=%s", answer.total)

        if answer.total == 0:
            msg = "No playground investigation found in the environment"
            raise RuntimeError(msg)

        if answer.total == 1:
            playground_id = answer.data[0].id
            logger.debug("Single playground found, id=%s", playground_id)
            return playground_id

        # More than one playground is visible to this token. Narrow down to the
        # playground created by the current user, paging through all results.
        logger.debug("Multiple playgrounds (%s) visible, filtering by current user", answer.total)
        username = self._current_username()

        def created_by_user(playground) -> bool:  # noqa: ANN001
            return playground.creating_user_id == username

        playgrounds = [pg for pg in answer.data if created_by_user(pg)]
        page_size = len(answer.data)
        remaining_pages = int((answer.total - 1) / page_size)
        for page in range(remaining_pages):
            next_page = self.client.demisto_py_instance.search_investigations(filter=self._playground_filter(page + 1))
            playgrounds.extend(pg for pg in next_page.data if created_by_user(pg))

        if len(playgrounds) != 1:
            msg = f"Expected exactly one playground for the current user but found {len(playgrounds)}"
            raise RuntimeError(msg)

        playground_id = playgrounds[0].id
        logger.debug("Resolved user playground, id=%s", playground_id)
        return playground_id

    def execute_command(self, name: str, args: dict[str, str], investigation_id: str, *, mode: str = "sync") -> dict:
        """Executes an automation script or integration command.

        There is no user-facing distinction between scripts and integration
        commands. The name is resolved to the correct type at execution time.

        args holds the key=value arguments for the script or command.
        investigation_id is the target investigation, either a case ID or the
        user's playground.

        mode selects the XSOAR execution endpoint:

        * "sync" submits the command and blocks until it completes, returning
          the resulting War Room entries. Wrapped as {"entries": [...]}.
        * "async" submits the command and returns immediately with the created
          entry. Wrapped as {"entry": {...}}.

        Raises ValueError for an unknown mode. The demisto-py ApiException
        propagates unchanged when the API call itself fails.
        """
        if mode not in EXECUTION_MODES:
            msg = f"Invalid execution mode '{mode}'. Must be one of {EXECUTION_MODES}."
            raise ValueError(msg)

        # Lazy import for performance reasons
        from demisto_client.demisto_api import UpdateEntry

        command_string = build_command_string(name, args)
        logger.debug("Executing command (mode=%s) in investigation '%s': %s", mode, investigation_id, command_string)
        update_entry = UpdateEntry(investigation_id=investigation_id, data=command_string)

        if mode == "sync":
            entries = self.client.demisto_py_instance.investigation_add_entries_sync(update_entry=update_entry)
            logger.debug("Sync execution returned %d entry/entries", len(entries or []))
            return {"entries": [entry.to_dict() for entry in (entries or [])]}

        entry = self.client.demisto_py_instance.investigation_add_entry_handler(update_entry=update_entry)
        logger.debug("Async execution submitted, entry id=%s", getattr(entry, "id", None))
        return {"entry": entry.to_dict()}

    def execute_playbook(self, name: str, investigation_id: str) -> dict:
        """Executes a playbook against the given investigation.

        investigation_id is either a case ID or the user's playground.
        """
        raise NotImplementedError
