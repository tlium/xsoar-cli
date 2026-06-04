import logging
from typing import TYPE_CHECKING

import click

from xsoar_cli.utilities.config_file import get_xsoar_config, load_config
from xsoar_cli.utilities.validators import validate_xsoar_connectivity
from xsoar_cli.xsoar_client.execution import DEFAULT_SYNC_TIMEOUT, EXECUTION_MODES

if TYPE_CHECKING:
    from xsoar_cli.xsoar_client.client import Client

logger = logging.getLogger(__name__)

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


def build_entry_url(server_url: str, view: str, segment: str, entry_id: str) -> str:
    """Build a direct link to an entry in a given XSOAR view.

    The URL shape is <server_url>/#/<view>/<segment>/<entry_id>, where view is
    "WarRoom" or "artifactViewer" and segment is the literal "playground" for
    playground executions or the case ID for a case. The server URL's trailing
    slash, if any, is stripped.
    """
    base = server_url.rstrip("/")
    return f"{base}/#/{view}/{segment}/{entry_id}"


def _result_entry_lines(entry_id: str, server_url: str, segment: str) -> list[str]:
    """Build the grouped output lines for a single result entry.

    Each result entry is shown with a short header and two links: the War Room
    view for context and the artifact viewer for downloading the entry content.
    The short entry number (the part before "@") is used in the header for
    readability; the full id is preserved in the URLs.
    """
    short_id = entry_id.split("@", 1)[0]
    return [
        f"Entry {short_id}:",
        f"  War Room entry: {build_entry_url(server_url, 'WarRoom', segment, entry_id)}",
        f"  Artifact viewer: {build_entry_url(server_url, 'artifactViewer', segment, entry_id)}",
    ]


def render_command_output(
    result: dict,
    name: str,
    server_url: str,
    warroom_segment: str,
) -> tuple[str, bool]:
    """Render an execute-command result for display.

    Returns a (text, had_error) tuple. had_error is True when the command
    returned one or more error entries, so the caller can exit non-zero.

    Reports only what is known:

    * sync success: that the command completed, the entry count, and War Room
      and artifact viewer links per returned entry.
    * sync error: the contents of each error entry and links to it.
    * sync timeout: that no results arrived in time and the command may still
      be running, with a War Room link to the submitted entry.
    * async: that the command was submitted, with the created entry ID and a
      War Room link.
    """
    if "entries" in result:
        if result.get("timed_out"):
            return _render_timeout_summary(result, server_url, warroom_segment), False
        return _render_sync_summary(result["entries"], name, server_url, warroom_segment)
    return _render_async_summary(result.get("entry", {}), name, server_url, warroom_segment), False


def _render_sync_summary(entries: list[dict], name: str, server_url: str, warroom_segment: str) -> tuple[str, bool]:
    """Render the summary for a synchronous (blocking) command execution.

    Each result entry is shown grouped with its War Room and artifact viewer
    links, separated by a blank line for readability.
    """
    error_entries = [entry for entry in entries if entry.get("type") == ERROR_ENTRY_TYPE]

    if error_entries:
        total = len(entries)
        error_count = len(error_entries)
        total_plural = "entry" if total == 1 else "entries"
        error_plural = "error" if error_count == 1 else "errors"
        lines = [f"Command {name} completed with errors ({total} {total_plural}, {error_count} {error_plural})."]
        for entry in error_entries:
            entry_id = entry.get("id", "")
            if not entry_id:
                continue
            lines.append("")
            contents = entry.get("contents")
            if contents:
                lines.append(str(contents))
            lines.extend(_result_entry_lines(entry_id, server_url, warroom_segment))
        return "\n".join(lines), True

    count = len(entries)
    plural = "entry" if count == 1 else "entries"
    lines = [f"Command {name} completed ({count} {plural})."]
    for entry in entries:
        entry_id = entry.get("id", "")
        if not entry_id:
            continue
        lines.append("")
        lines.extend(_result_entry_lines(entry_id, server_url, warroom_segment))
    return "\n".join(lines), False


def _render_timeout_summary(result: dict, server_url: str, warroom_segment: str) -> str:
    """Render the summary when a sync command produced no results before timeout.

    A timeout is treated as success with a warning: the command was submitted
    successfully (a submit failure surfaces fast as an API error), so it is
    almost certainly still running. The link points at the submitted entry.
    """
    entry_id = result.get("entry_id", "")
    lines = ["No command results within timeout. It may still be running."]
    if entry_id:
        lines.append(f"War Room entry: {build_entry_url(server_url, 'WarRoom', warroom_segment, entry_id)}")
    return "\n".join(lines)


def _render_async_summary(entry: dict, name: str, server_url: str, warroom_segment: str) -> str:
    """Render the summary for an asynchronous command submission."""
    entry_id = entry.get("id", "")
    lines = [f"Command {name} submitted. Entry ID: {entry_id}"]
    if entry_id:
        lines.append(f"War Room entry: {build_entry_url(server_url, 'WarRoom', warroom_segment, entry_id)}")
    return "\n".join(lines)


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
    "--timeout",
    type=int,
    default=DEFAULT_SYNC_TIMEOUT,
    show_default=True,
    help="Seconds to wait for results in sync mode before reporting the command is still running.",
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
    timeout: int,
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

    In sync mode, --timeout bounds how long to wait for results. If the command
    has not produced results by then, it is reported as still running and a War
    Room link is printed; this is not treated as an error.

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
    # The leading "!" is optional on input; strip it for display so user-facing
    # messages read the same whether or not the user included it.
    display_name = name[1:] if name.startswith("!") else name
    logger.info("Executing command '%s' (mode=%s) against investigation '%s'", name, mode, investigation_id)
    if mode == "sync":
        click.echo(f"Executing {display_name}, waiting up to {timeout}s for results...", err=True)
    try:
        result = xsoar_client.execution.execute_command(name, parsed_args, investigation_id, mode=mode, timeout=timeout)
    except ApiException as ex:
        logger.info("Command execution failed with API error: %s", ex)
        click.echo(f"Error: command execution failed: {ex}")
        ctx.exit(1)
    output, had_error = render_command_output(result, display_name, xsoar_client.server_url, warroom_segment)
    click.echo(output)
    if had_error:
        ctx.exit(1)


@click.command()
@click.option("--environment", default=None, help="Default environment set in config file.")
@click.option("--case-id", type=int, default=None, help="Case ID to execute against. Defaults to the user's playground.")
@click.argument("name", type=str)
@click.pass_context
@load_config
@validate_xsoar_connectivity
def playbook(ctx: click.Context, environment: str | None, case_id: int | None, name: str) -> None:
    """Start a playbook.

    NAME is the playbook to run.

    By default the playbook is started in the user's playground. Pass --case-id
    to start it in a specific case instead.

    This is fire-and-forget: the playbook is started and the command returns
    without waiting for it to finish.

    Usage examples:

    xsoar-cli execute playbook "My Playbook"

    xsoar-cli execute playbook "My Playbook" --case-id 12345
    """
    # Lazy import for performance reasons
    from demisto_client.demisto_api.rest import ApiException

    config = get_xsoar_config(ctx)
    xsoar_client: Client = config.get_client(environment)
    investigation_id = resolve_investigation_id(ctx, xsoar_client, case_id)
    target = f"case {case_id}" if case_id is not None else "playground"
    logger.info("Starting playbook '%s' in %s (investigation '%s')", name, target, investigation_id)
    try:
        xsoar_client.execution.execute_playbook(name, investigation_id)
    except ValueError as ex:
        logger.info("Could not start playbook: %s", ex)
        click.echo(f"Error: {ex}", err=True)
        ctx.exit(1)
    except ApiException as ex:
        logger.info("Playbook start failed with API error: %s", ex)
        click.echo(f"Error: failed to start playbook: {ex}", err=True)
        ctx.exit(1)
    click.echo(f"Started playbook {name} in {target}")


execute.add_command(command)
execute.add_command(playbook)
