import json
import logging
from typing import TYPE_CHECKING

import click
from requests.exceptions import HTTPError

from xsoar_cli.error_handling.connection import ConnectionErrorHandler
from xsoar_cli.error_handling.http import HTTPErrorHandler
from xsoar_cli.utilities.config_file import get_xsoar_config, load_config
from xsoar_cli.utilities.validators import validate_environments

logger = logging.getLogger(__name__)


def parse_string_to_dict(input_string: str | None, delimiter: str) -> dict:
    """Parse a delimited key=value string into a dictionary."""
    if not input_string:
        return {}
    pairs = [pair.split("=", 1) for pair in input_string.split(delimiter)]
    valid_pairs = [pair for pair in pairs if len(pair) == 2]  # noqa: PLR2004
    return {key.strip(): value.strip() for key, value in valid_pairs}


if TYPE_CHECKING:
    from xsoar_cli.xsoar_client.client import Client


@click.group(help="Create, retrieve, and clone cases")
def case() -> None:
    pass


@click.command()
@click.argument("casenumber", type=int)
@click.option("--environment", default=None, help="Default environment set in config file.")
@click.pass_context
@load_config
def get(ctx: click.Context, casenumber: int, environment: str | None) -> None:
    """Retrieve and display a single case.

    CASENUMBER is the numeric case ID to look up. Output is formatted as JSON.

    Usage examples:

    xsoar-cli case get 12345
    """
    config = get_xsoar_config(ctx)
    xsoar_client: Client = config.get_client(environment)
    try:
        response = xsoar_client.cases.get(casenumber)
    except HTTPError as ex:
        handler = HTTPErrorHandler()
        click.echo(f"Error: {handler.get_message(ex, context='case')}")
        ctx.exit(1)
    click.echo(json.dumps(response, indent=4))


@click.command()
@click.argument("casenumber", type=int)
@click.option("--source", required=True, show_default=True, help="Source environment")
@click.option("--dest", required=True, show_default=True, help="Destination environment")
@click.pass_context
@load_config
def clone(ctx: click.Context, casenumber: int, source: str, dest: str) -> None:
    """Clone a case from source to destination environment.

    CASENUMBER is the numeric case ID to clone. Both --source and --dest must refer to
    environments defined in the config file.

    The cloned case preserves labels and triggers playbook execution on creation.
    Attachments are not included in the clone.

    Usage examples:

    xsoar-cli case clone --source prod --dest staging 12345
    """
    logger.info("Cloning case %d from '%s' to '%s'", casenumber, source, dest)

    valid_envs = validate_environments(source, dest, ctx=ctx)
    if not valid_envs:
        click.echo(f"Error: cannot find environments {source} and/or {dest} in config")
        ctx.exit(1)

    # Test connectivity to both environments before proceeding
    config = get_xsoar_config(ctx)
    for env_name in (source, dest):
        logger.debug("Testing XSOAR connectivity for environment '%s'", env_name)
        try:
            config.get_client(env_name).test_connectivity()
        except ConnectionError as ex:
            handler = ConnectionErrorHandler()
            logger.info("Connection failed for environment '%s': %s", env_name, handler.get_message(ex))
            click.echo(f"Connection failed for '{env_name}': {handler.get_message(ex)}")
            ctx.exit(1)
        logger.debug("Connectivity OK for environment '%s'", env_name)

    xsoar_source_client: Client = config.get_client(source)
    xsoar_dest_client: Client = config.get_client(dest)

    results = xsoar_source_client.cases.get(casenumber)
    # These keys can safely be removed from the results dict before creating a new case
    remove_keys = [
        "dbotMirrorId",
        "dbotMirrorInstance",
        "dbotMirrorDirection",
        "dbotDirtyFields",
        "dbotCurrentDirtyFields",
        "dbotMirrorTags",
        "dbotMirrorLastSync",
        "id",
        "version",
        "created",
        "modified",
        "cacheVersn",
        "sizeInBytes",
        "attachment",
    ]
    logger.debug("Removing keys from case %d before cloning: %s", casenumber, remove_keys)
    for key in remove_keys:
        results.pop(key)

    # Pop the labels here because XSOAR chokes on to much data in the incident creation request. Create the
    # new case clone without labels now and add labels in a later request.
    labels = results.pop("labels")
    logger.debug("Popped %d label(s) from case %d for deferred merge", len(labels), casenumber)
    results.pop("owner")

    # Ensure that playbooks run immediately when the case is created
    results["createInvestigation"] = True
    case_data = xsoar_dest_client.cases.create(data=results)
    case_id = case_data["id"]
    logger.info("Created destination case %s in '%s'", case_id, dest)

    # Fetch updated version etc for the newly created case. We need this to prevent errors stemming from optimistic locking
    new_case_data = xsoar_dest_client.cases.get(case_id)
    logger.debug("Re-fetched destination case %s to obtain current version for label merge", case_id)

    existing_labels = new_case_data["labels"]
    logger.debug("Merging %d existing label(s) with %d source label(s)", len(existing_labels), len(labels))
    new_case_data["labels"] = existing_labels + labels
    # Keep the source case status. If the case is closed in source environment, it should be closed in dest environment
    # new_case_data["status"] = results["status"]
    case_data = xsoar_dest_client.cases.create(data=new_case_data)
    logger.info("Clone complete: case %d ('%s') -> case %s ('%s')", casenumber, source, case_id, dest)
    click.echo(f"Case {casenumber} from {source} cloned into case {case_id} in {dest}")


@click.command()
@click.option("--environment", default=None, help="Default environment set in config file.")
@click.option("--casetype", default="", show_default=True, help="Create case of specified type. Default type set in config file.")
@click.option(
    "--custom-fields",
    default=None,
    help='Additional fields on the form "myfield=my_value,anotherfield=another value". Use machine name for field names, e.g mycustomfieldname.',
)
@click.option("--custom-fields-delimiter", default=",", help='Delimiter when specifying additional fields. Default is ","')
@click.argument("details", type=str, default="Placeholder case details")
@click.argument("name", type=str, default="Test case created from xsoar-cli")
@click.pass_context
@load_config
def create(  # noqa: PLR0913
    ctx: click.Context,
    environment: str | None,
    casetype: str,
    name: str,
    custom_fields: str | None,
    custom_fields_delimiter: str,
    details: str,
) -> None:
    """Create a new case.

    NAME is the title of the created case. DETAILS is the case description body.

    Custom fields must use the machine name (e.g. mycustomfieldname) and be specified as
    key=value pairs separated by the configured delimiter.

    If --casetype is omitted, the default case type from the config file is used.
    If an invalid case type is specified, XSOAR will default to Unclassified.

    Usage examples:

    xsoar-cli case create "My case title" "Case description"

    xsoar-cli case create --casetype Malware --custom-fields "severity=high,owner=analyst1" "My case" "Details here"
    """
    if custom_fields and "=" not in custom_fields:
        click.echo('Malformed custom fields. Must be on the form "myfield=myvalue"')
        ctx.exit(1)
    config = get_xsoar_config(ctx)
    xsoar_client: Client = config.get_client(environment)
    if not casetype:
        casetype = config.default_new_case_type
    data = {
        "createInvestigation": True,
        "name": name,
        "type": casetype,
        "details": details,
        "CustomFields": parse_string_to_dict(custom_fields, custom_fields_delimiter),
    }
    case_data = xsoar_client.cases.create(data=data)
    case_id = case_data["id"]
    click.echo(f"Created XSOAR case {case_id}")


case.add_command(get)
case.add_command(clone)
case.add_command(create)
