import json
from typing import TYPE_CHECKING

import click

from xsoar_cli.utilities import load_config, validate_environments

if TYPE_CHECKING:
    from xsoar_client.xsoar_client import Client


@click.group(help="Add new or modify existing XSOAR case")
def case() -> None:
    pass


@click.argument("casenumber", type=int)
@click.option("--environment", default="dev", show_default=True, help="Environment as defined in config file")
@click.command(help="Get basic information about a single case in XSOAR")
@click.pass_context
@load_config
def get(ctx: click.Context, casenumber: int, environment: str) -> None:
    xsoar_client: Client = ctx.obj["server_envs"][environment]
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
def clone(ctx: click.Context, casenumber: int, source: str, dest: str) -> None:
    """Clones a case from source to destination environment."""
    valid_envs = validate_environments(source, dest, ctx=ctx)
    if not valid_envs:
        click.echo(f"Error: cannot find environments {source} and/or {dest} in config")
        ctx.exit(1)
    xsoar_source_client: Client = ctx.obj["server_envs"][source]
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

    xsoar_dest_client: Client = ctx.obj["server_envs"][dest]
    case_data = xsoar_dest_client.create_case(data=data)
    click.echo(json.dumps(case_data, indent=4))


@click.option("--environment", default="dev", show_default=True, help="Environment as defined in config file")
@click.option("--casetype", default="", show_default=True, help="Create case of specified type. Default type set in config file.")
@click.argument("details", type=str, default="Placeholder case details")
@click.argument("name", type=str, default="Test case created from xsoar-cli")
@click.command()
@click.pass_context
@load_config
def create(ctx: click.Context, environment: str, casetype: str, name: str, details: str) -> None:
    """Creates a new case in XSOAR. If invalid case type is specified as a command option, XSOAR will default to using Unclassified."""
    xsoar_client: Client = ctx.obj["server_envs"][environment]
    if not casetype:
        casetype = ctx.obj["default_new_case_type"]
    data = {
        "createInvestigation": True,
        "name": name,
        "type": casetype,
        "details": details,
    }
    case_data = xsoar_client.create_case(data=data)
    case_id = case_data["id"]
    click.echo(f"Created XSOAR case {case_id}")


case.add_command(get)
case.add_command(clone)
case.add_command(create)
