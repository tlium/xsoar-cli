from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .client import Client


class Execution:
    def __init__(self, client: Client) -> None:
        self.client = client

    def resolve_playground_id(self) -> str:
        """Resolves the current user's playground investigation ID.

        Used when no case ID is supplied, so that scripts, integration commands,
        and playbooks can be executed against the user's playground by default.
        """
        raise NotImplementedError

    def execute_command(self, name: str, args: dict[str, str], investigation_id: str) -> dict:
        """Executes an automation script or integration command.

        There is no user-facing distinction between scripts and integration
        commands. The name is resolved to the correct type at execution time.

        args holds the key=value arguments for the script or command.
        investigation_id is the target investigation, either a case ID or the
        user's playground.
        """
        raise NotImplementedError

    def execute_playbook(self, name: str, investigation_id: str) -> dict:
        """Executes a playbook against the given investigation.

        investigation_id is either a case ID or the user's playground.
        """
        raise NotImplementedError
