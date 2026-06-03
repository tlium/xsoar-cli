import json
import logging
from typing import TYPE_CHECKING

import click

from xsoar_cli.utilities.config_file import get_xsoar_config, load_config
from xsoar_cli.utilities.validators import validate_xsoar_connectivity
from xsoar_cli.xsoar_client.execution import EXECUTION_MODES

if TYPE_CHECKING:
    from xsoar_cli.xsoar_client.client import Client

logger = logging.getLogger(__name__)

OUTPUT_LEVELS = ["summary", "raw"]

# XSOAR entry type identifying an error entry in command output.
ERROR_ENTRY_TYPE = 4


def parse_arg_tokens(tokens: tuple[str, ...]) -> dict[str, str]:
    """Parse variadic key=value tokens into a dictionary.

    Raises ValueError on any token that does not contain a "=" separator.
    """
    args: dict[str, str] = {}
    for token in tokens:
        if "=" not in token:
            msg = f"Malformed argument '{token}'. Arguments must be on the form key=value."
            raise ValueError(msg)
        key, value = token.split("=", 1)
        args[key.strip()] = value.strip()
    return args


def resolve_investigation_id(ctx: click.Context, xsoar_client: "Client", case_id: int | None) -> str:
    """Return the target investigation ID.

    Uses the supplied case ID when present, otherwise resolves the user's
    playground investigation ID.

    Distinguishes two failure modes when resolving the playground:

    * ApiException means the XSOAR API call itself failed (connectivity, auth,
      server error). The user is pointed at the environment.
    * RuntimeError means the calls succeeded but no single playground could be
      identified. The specific reason is surfaced to the user.

    Both cases print a message and exit with a non-zero status.
    """
    # Lazy import for performance reasons
    from demisto_client.demisto_api.rest import ApiException

    if case_id is not None:
        logger.debug("Using supplied case ID %d as investigation ID", case_id)
        return str(case_id)

    logger.debug("No case ID supplied, resolving user's playground investigation ID")
    try:
        investigation_id = xsoar_client.execution.resolve_playground_id()
    except ApiException as ex:
        logger.info("Playground lookup failed with API error: %s", ex)
        click.echo(f"Error: failed to query XSOAR for the playground investigation: {ex}")
        ctx.exit(1)
    except RuntimeError as ex:
        logger.info("Could not resolve playground investigation: %s", ex)
        click.echo(f"Error: {ex}")
        ctx.exit(1)
    logger.debug("Resolved playground investigation ID: %s", investigation_id)
    return investigation_id


def build_warroom_url(server_url: str, warroom_segment: str, entry_id: str) -> str:
    """Build a direct link to a War Room entry.

    The URL shape is <server_url>/#/WarRoom/<segment>/<entry_id>, where segment
    is the literal "playground" for playground executions or the case ID for a
    case. The server URL's trailing slash, if any, is stripped.
    """
    base = server_url.rstrip("/")
    return f"{base}/#/WarRoom/{warroom_segment}/{entry_id}"


def render_command_output(
    result: dict,
    output_level: str,
    name: str,
    server_url: str,
    warroom_segment: str,
) -> tuple[str, bool]:
    """Render an execute-command result for display.

    Returns a (text, had_error) tuple. had_error is True when the command
    returned one or more error entries, so the caller can exit non-zero.

    raw dumps the full result as JSON (had_error is always False; the caller is
    expected to inspect the JSON itself).

    summary reports only what is known:

    * sync success: that the command completed, the entry count, and a War Room
      link per returned entry.
    * sync error: the contents of each error entry and a link to it.
    * async: that the command was submitted, with the created entry ID and link.
    """
    if output_level == "raw":
        return json.dumps(result, indent=4), False

    if "entries" in result:
        return _render_sync_summary(result["entries"], name, server_url, warroom_segment)
    return _render_async_summary(result.get("entry", {}), name, server_url, warroom_segment), False


def _render_sync_summary(entries: list[dict], name: str, server_url: str, warroom_segment: str) -> tuple[str, bool]:
    """Render the summary for a synchronous (blocking) command execution."""
    error_entries = [entry for entry in entries if entry.get("type") == ERROR_ENTRY_TYPE]

    if error_entries:
        total = len(entries)
        error_count = len(error_entries)
        total_plural = "entry" if total == 1 else "entries"
        error_plural = "error" if error_count == 1 else "errors"
        lines = [f"Command {name} completed with errors ({total} {total_plural}, {error_count} {error_plural})."]
        for entry in error_entries:
            contents = entry.get("contents")
            if contents:
                lines.append(str(contents))
            entry_id = entry.get("id", "")
            if entry_id:
                lines.append(f"War Room entry: {build_warroom_url(server_url, warroom_segment, entry_id)}")
        return "\n".join(lines), True

    count = len(entries)
    plural = "entry" if count == 1 else "entries"
    lines = [f"Command {name} completed ({count} {plural})."]
    for entry in entries:
        entry_id = entry.get("id", "")
        if entry_id:
            lines.append(f"War Room entry: {build_warroom_url(server_url, warroom_segment, entry_id)}")
    return "\n".join(lines), False


def _render_async_summary(entry: dict, name: str, server_url: str, warroom_segment: str) -> str:
    """Render the summary for an asynchronous command submission."""
    entry_id = entry.get("id", "")
    lines = [f"Command {name} submitted. Entry ID: {entry_id}"]
    if entry_id:
        lines.append(f"War Room entry: {build_warroom_url(server_url, warroom_segment, entry_id)}")
    return "\n".join(lines)


def render_output(result: dict, output_level: str) -> str:
    """Render an execution result according to the chosen output level."""
    if output_level == "raw":
        return json.dumps(result, indent=4)
    # summary is a placeholder until the playbook execution layer is implemented.
    return json.dumps(result, indent=4)


@click.group()
def execute() -> None:
    """Execute scripts, integration commands, and playbooks"""
    pass


@click.command()
@click.option("--environment", default=None, help="Default environment set in config file.")
@click.option("--case-id", type=int, default=None, help="Case ID to execute against. Defaults to the user's playground.")
@click.option(
    "--mode",
    type=click.Choice(EXECUTION_MODES, case_sensitive=False),
    default="sync",
    show_default=True,
    help="Execute synchronously (wait for and return results) or asynchronously (submit and return the entry).",
)
@click.option(
    "--output-level",
    type=click.Choice(OUTPUT_LEVELS, case_sensitive=False),
    default="summary",
    show_default=True,
    help="Amount of detail to include in the output.",
)
@click.argument("name", type=str)
@click.argument("args", nargs=-1, type=str)
@click.pass_context
@load_config
@validate_xsoar_connectivity
def command(  # noqa: PLR0913
    ctx: click.Context,
    environment: str | None,
    case_id: int | None,
    mode: str,
    output_level: str,
    name: str,
    args: tuple[str, ...],
) -> None:
    """Execute an automation script or integration command.

    NAME is the script or integration command to run. There is no difference in
    how scripts and integration commands are invoked. Use the bare name (as you
    would reference it in a playbook). A leading "!" is accepted but optional.

    Arguments are supplied as space-separated key=value pairs. Values containing
    whitespace are quoted automatically.

    Shell note: interactive shells treat characters like "!" and "|" specially.
    Prefer omitting the "!" and wrap argument values in single quotes when they
    contain shell metacharacters, for example query='index=foo | head 1'.

    By default execution happens in the user's playground. Pass --case-id to run
    against a specific case instead.

    --mode sync waits for the command to finish and returns the resulting War
    Room entries. --mode async submits the command and returns immediately with
    the created entry.

    Usage examples:

    xsoar-cli execute command MyScript arg1=val1 arg2=val2

    xsoar-cli execute command whois query=example.com --case-id 12345

    xsoar-cli execute command splunk-search query='index=zscaler | head 1'

    xsoar-cli execute command MyScript arg1=val1 --mode async
    """
    # Lazy import for performance reasons
    from demisto_client.demisto_api.rest import ApiException

    try:
        parsed_args = parse_arg_tokens(args)
    except ValueError as ex:
        click.echo(f"Error: {ex}")
        ctx.exit(1)

    config = get_xsoar_config(ctx)
    xsoar_client: Client = config.get_client(environment)
    investigation_id = resolve_investigation_id(ctx, xsoar_client, case_id)
    # The War Room URL uses the literal "playground" segment for playground
    # executions, and the case ID when running against a specific case.
    warroom_segment = str(case_id) if case_id is not None else "playground"
    logger.info("Executing command '%s' (mode=%s) against investigation '%s'", name, mode, investigation_id)
    try:
        result = xsoar_client.execution.execute_command(name, parsed_args, investigation_id, mode=mode)
    except ApiException as ex:
        logger.info("Command execution failed with API error: %s", ex)
        click.echo(f"Error: command execution failed: {ex}")
        ctx.exit(1)
    output, had_error = render_command_output(result, output_level, name, xsoar_client.server_url, warroom_segment)
    click.echo(output)
    if had_error:
        ctx.exit(1)


@click.command()
@click.option("--environment", default=None, help="Default environment set in config file.")
@click.option("--case-id", type=int, default=None, help="Case ID to execute against. Defaults to the user's playground.")
@click.option(
    "--output-level",
    type=click.Choice(OUTPUT_LEVELS, case_sensitive=False),
    default="summary",
    show_default=True,
    help="Amount of detail to include in the output.",
)
@click.argument("name", type=str)
@click.pass_context
@load_config
@validate_xsoar_connectivity
def playbook(ctx: click.Context, environment: str | None, case_id: int | None, output_level: str, name: str) -> None:
    """Execute a playbook.

    NAME is the playbook to run.

    By default execution happens in the user's playground. Pass --case-id to run
    against a specific case instead.

    Usage examples:

    xsoar-cli execute playbook "My Playbook"

    xsoar-cli execute playbook "My Playbook" --case-id 12345
    """
    config = get_xsoar_config(ctx)
    xsoar_client: Client = config.get_client(environment)
    investigation_id = resolve_investigation_id(ctx, xsoar_client, case_id)
    logger.info("Executing playbook '%s' against investigation '%s'", name, investigation_id)
    result = xsoar_client.execution.execute_playbook(name, investigation_id)
    click.echo(render_output(result, output_level))


execute.add_command(command)
execute.add_command(playbook)
