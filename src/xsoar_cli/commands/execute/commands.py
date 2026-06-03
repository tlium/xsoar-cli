import json
import logging
from typing import TYPE_CHECKING

import click

from xsoar_cli.utilities.config_file import get_xsoar_config, load_config
from xsoar_cli.utilities.validators import validate_xsoar_connectivity

if TYPE_CHECKING:
    from xsoar_cli.xsoar_client.client import Client

logger = logging.getLogger(__name__)

OUTPUT_LEVELS = ["summary", "raw"]


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


def render_output(result: dict, output_level: str) -> str:
    """Render an execution result according to the chosen output level."""
    if output_level == "raw":
        return json.dumps(result, indent=4)
    # summary is a placeholder until the execution layer is implemented.
    return json.dumps(result, indent=4)


@click.group()
def execute() -> None:
    """Execute scripts, integration commands, and playbooks"""
    pass


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
@click.argument("args", nargs=-1, type=str)
@click.pass_context
@load_config
@validate_xsoar_connectivity
def command(  # noqa: PLR0913
    ctx: click.Context,
    environment: str | None,
    case_id: int | None,
    output_level: str,
    name: str,
    args: tuple[str, ...],
) -> None:
    """Execute an automation script or integration command.

    NAME is the script or integration command to run. There is no difference in
    how scripts and integration commands are invoked.

    Arguments are supplied as space-separated key=value pairs.

    By default execution happens in the user's playground. Pass --case-id to run
    against a specific case instead.

    Usage examples:

    xsoar-cli execute command MyScript arg1=val1 arg2=val2

    xsoar-cli execute command !whois query=example.com --case-id 12345
    """
    try:
        parsed_args = parse_arg_tokens(args)
    except ValueError as ex:
        click.echo(f"Error: {ex}")
        ctx.exit(1)

    config = get_xsoar_config(ctx)
    xsoar_client: Client = config.get_client(environment)
    investigation_id = resolve_investigation_id(ctx, xsoar_client, case_id)
    logger.info("Executing command '%s' against investigation '%s'", name, investigation_id)
    result = xsoar_client.execution.execute_command(name, parsed_args, investigation_id)
    click.echo(render_output(result, output_level))


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
