import json
from typing import TYPE_CHECKING

import click

from xsoar_cli.utilities import load_config, parse_string_to_dict, validate_environments

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
    if not environment:
        environment = ctx.obj["default_environment"]
    xsoar_client: Client = ctx.obj["server_envs"][environment]["xsoar_client"]
    response = xsoar_client.get_case(casenumber)
    if response["total"] == 0 and not response["data"]:
        click.echo(f"Cannot find case ID {casenumber}")
        ctx.exit(1)
    click.echo(json.dumps(response, indent=4))


@click.argument("casenumber", type=int)
@click.option("--source", default="prod", show_default=True, help="Source environment")
@click.option("--dest", default="dev", show_default=True, help="Destination environment")
@click.option(
    "--custom-fields",
    default=None,
    help='Additional fields on the form "myfield=my_value,anotherfield=another value". Use machine name for field names, e.g mycustomfieldname.',
)
@click.option("--custom-fields-delimiter", default=",", help='Delimiter when specifying additional fields. Default is ","')
@click.command()
@click.pass_context
@load_config
def clone(  # noqa: PLR0913
    ctx: click.Context,
    casenumber: int,
    source: str,
    dest: str,
    custom_fields: str | None,
    custom_fields_delimiter: str,
) -> None:
    """Clones a case from source to destination environment."""
    valid_envs = validate_environments(source, dest, ctx=ctx)
    if not valid_envs:
        click.echo(f"Error: cannot find environments {source} and/or {dest} in config")
        ctx.exit(1)
    if custom_fields and "=" not in custom_fields:
        click.echo('Malformed custom fields. Must be on the form "myfield=myvalue"')
        ctx.exit(1)
    xsoar_source_client: Client = ctx.obj["server_envs"][source]["xsoar_client"]
    results = xsoar_source_client.get_case(casenumber)
    data = results["data"][0]
    # Dbot mirror info is irrelevant. This will be added again if applicable by XSOAR after ticket creation in dev.
    data.pop("dbotMirrorId")
    data.pop("dbotMirrorInstance")
    data.pop("dbotMirrorDirection")
    data.pop("dbotDirtyFields")
    data.pop("dbotCurrentDirtyFields")
    data.pop("dbotMirrorTags")
    data.pop("dbotMirrorLastSync")
    data.pop("id")
    data.pop("created")
    data.pop("modified")
    # Ensure that playbooks run immediately when the case is created
    data["createInvestigation"] = True
    if "CustomFields" in data:
        data["CustomFields"] = data["CustomFields"] | parse_string_to_dict(custom_fields, custom_fields_delimiter)

    xsoar_dest_client: Client = ctx.obj["server_envs"][dest]["xsoar_client"]
    case_data = xsoar_dest_client.create_case(data=data)
    click.echo(json.dumps(case_data, indent=4))


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
    if not environment:
        environment = ctx.obj["default_environment"]
    xsoar_client: Client = ctx.obj["server_envs"][environment]["xsoar_client"]
    if not casetype:
        casetype = ctx.obj["default_new_case_type"]
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
