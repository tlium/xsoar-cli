import json
from typing import TYPE_CHECKING

import click

from xsoar_cli.utilities import get_xsoar_config, load_config, parse_string_to_dict, validate_environments, validate_xsoar_connectivity

if TYPE_CHECKING:
    from xsoar_client.xsoar_client import Client


@click.group(help="Add new or modify existing XSOAR case")
def case() -> None:
    pass


@click.argument("casenumber", type=int)
@click.option("--environment", default=None, help="Default environment set in config file.")
@click.command(help="Get basic information about a single case in XSOAR")
@click.pass_context
@load_config
def get(ctx: click.Context, casenumber: int, environment: str | None) -> None:
    config = get_xsoar_config(ctx)
    xsoar_client: Client = config.get_client(environment)
    response = xsoar_client.get_case(casenumber)
    if response["total"] == 0 and not response["data"]:
        click.echo(f"Cannot find case ID {casenumber}")
        ctx.exit(1)
    click.echo(json.dumps(response, indent=4))


@click.argument("casenumber", type=int)
@click.option("--source", default="prod", show_default=True, help="Source environment")
@click.option("--dest", default="dev", show_default=True, help="Destination environment")
@click.command()
@click.pass_context
@load_config
@validate_xsoar_connectivity(lambda ctx: [ctx.params["source"], ctx.params["dest"]])
def clone(ctx: click.Context, casenumber: int, source: str, dest: str) -> None:
    """Clones a case from source to destination environment."""
    valid_envs = validate_environments(source, dest, ctx=ctx)
    if not valid_envs:
        click.echo(f"Error: cannot find environments {source} and/or {dest} in config")
        ctx.exit(1)

    # Grab configi and set up source and destination xsoar-client objects
    config = get_xsoar_config(ctx)
    xsoar_source_client: Client = config.get_client(source)
    xsoar_dest_client: Client = config.get_client(dest)

    results = xsoar_source_client.get_case(casenumber)
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
    for key in remove_keys:
        results.pop(key)

    # Pop the labels here because XSOAR chokes on to much data in the incident creation request. Create the
    # new case clone without labels now and add labels in a later request.
    labels = results.pop("labels")
    results.pop("owner")

    # Ensure that playbooks run immediately when the case is created
    results["createInvestigation"] = True
    case_data = xsoar_dest_client.create_case(data=results)
    case_id = case_data["id"]

    # Fetch updated version etc for the newly created case. We need this to prevent errors stemming from optimistic locking
    new_case_data = xsoar_dest_client.get_case(case_id)

    new_labels = new_case_data["labels"] + labels
    new_case_data["labels"] = new_labels
    # Keep the source case status. If the case is closed in source environment, it should be closed in dest environment
    # new_case_data["status"] = results["status"]
    case_data = xsoar_dest_client.create_case(data=new_case_data)
    click.echo(f"Case {casenumber} from {source} cloned into case {case_id} in {dest}")


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
@click.command()
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
    """Creates a new case in XSOAR. If invalid case type is specified as a command option, XSOAR will default to using Unclassified."""
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
    case_data = xsoar_client.create_case(data=data)
    case_id = case_data["id"]
    click.echo(f"Created XSOAR case {case_id}")


case.add_command(get)
case.add_command(clone)
case.add_command(create)
