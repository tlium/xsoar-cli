from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .client import Client

logger = logging.getLogger(__name__)

# XSOAR investigation type identifier for playgrounds.
PLAYGROUND_INVESTIGATION_TYPE = 9

# Valid execution modes for execute_command.
EXECUTION_MODES = ("sync", "async")

# Default wall-clock limit (seconds) for polling a sync command's results before
# giving up and reporting that execution is still in progress.
DEFAULT_SYNC_TIMEOUT = 30

# Interval (seconds) between polls of the investigation for a sync command's
# result entries.
SYNC_POLL_INTERVAL = 2

# Page size requested when fetching investigation entries during polling. The
# playground accumulates history over time, so this is set high to ensure a
# freshly created result entry is included in the response.
INVESTIGATION_PAGE_SIZE = 1000


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

    def execute_command(
        self,
        name: str,
        args: dict[str, str],
        investigation_id: str,
        *,
        mode: str = "sync",
        timeout: int = DEFAULT_SYNC_TIMEOUT,
    ) -> dict:
        """Executes an automation script or integration command.

        There is no user-facing distinction between scripts and integration
        commands. The name is resolved to the correct type at execution time.

        args holds the key=value arguments for the script or command.
        investigation_id is the target investigation, either a case ID or the
        user's playground.

        mode selects how results are handled:

        * "sync" submits the command and then polls the investigation for the
          resulting War Room entries until they appear or timeout (seconds)
          elapses. XSOAR commits a command's War Room entries atomically when
          the command finishes, so the first poll where result entries appear
          means execution has completed. Returns {"entries": [...]} with only
          the entries produced by this command. On timeout, returns
          {"entries": [], "timed_out": True, "entry_id": <submitted id>} so the
          caller can report that execution is still in progress.
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

        # Both modes submit asynchronously. The submitted entry's id is the
        # parent of the result entries that the command produces.
        submitted = self.client.demisto_py_instance.investigation_add_entry_handler(update_entry=update_entry)
        submitted_id = submitted.id
        logger.debug("Command submitted, entry id=%s", submitted_id)

        if mode == "async":
            return {"entry": submitted.to_dict()}

        entries = self._poll_for_result_entries(investigation_id, submitted_id, timeout)
        if entries is None:
            logger.debug("No result entries after %ds, execution still in progress", timeout)
            return {"entries": [], "timed_out": True, "entry_id": submitted_id}
        logger.debug("Sync execution produced %d result entry/entries", len(entries))
        return {"entries": entries}

    def _poll_for_result_entries(self, investigation_id: str, parent_id: str, timeout: int) -> list[dict] | None:
        """Poll the investigation for entries produced by a submitted command.

        Repeatedly fetches the investigation's entries and returns those whose
        parentId matches the submitted command's entry id. Returns the result
        entries as soon as any appear, since XSOAR commits a command's entries
        atomically on completion. Returns None when timeout (seconds) elapses
        without any result entries appearing.
        """
        deadline = time.monotonic() + timeout
        while True:
            entries = self._fetch_child_entries(investigation_id, parent_id)
            if entries:
                return entries
            if time.monotonic() >= deadline:
                return None
            time.sleep(SYNC_POLL_INTERVAL)

    def _fetch_child_entries(self, investigation_id: str, parent_id: str) -> list[dict]:
        """Fetch the investigation's entries whose parentId matches parent_id.

        POST /investigation/<id> returns the full War Room history, so the
        entries are filtered down to those produced by the submitted command.
        """
        data, _, _ = self.client.demisto_py_instance.generic_request(
            path=f"/investigation/{investigation_id}",
            method="POST",
            body={"pageSize": INVESTIGATION_PAGE_SIZE},
            content_type="application/json",
            response_type=object,
        )
        all_entries = data.get("entries") or []
        return [entry for entry in all_entries if entry.get("parentId") == parent_id]

    def execute_playbook(self, name: str, investigation_id: str) -> dict:
        """Executes a playbook against the given investigation.

        investigation_id is either a case ID or the user's playground.
        """
        raise NotImplementedError
