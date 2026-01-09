import json
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from xsoar_client.xsoar_client import Client

import contextlib

from xsoar_cli.utilities import (
    get_config_file_contents,
    get_config_file_path,
    get_config_file_template_contents,
    load_config,
)


@click.group(help="Create/validate etc")
def config() -> None:
    pass


@click.command()
@click.option("--unmask", "masked", is_flag=True, default=False)
@click.pass_context
@load_config
def show(ctx: click.Context, masked: bool) -> None:
    """Prints out current config. API keys are masked."""
    config_file = get_config_file_path()
    config = get_config_file_contents(config_file)
    if not masked:
        for key in config["server_config"]:
            config["server_config"][key]["api_token"] = "MASKED"  # noqa: S105
    print(json.dumps(config, indent=4))
    ctx.exit()


@click.command()
@click.option("--only-test-environment", default=None, show_default=True, help="Environment as defined in config file")
@click.option("--stacktrace", is_flag=True, default=False, help="Print full stack trace on config validation failure.")
@click.pass_context
@load_config
def validate(ctx: click.Context, only_test_environment: str, stacktrace: bool) -> None:
    """Validates that the configuration file is JSON and tests connectivity for each XSOAR Client environment defined."""
    return_code = 0
    for server_env in ctx.obj["server_envs"]:
        if only_test_environment and server_env != only_test_environment:
            # Ignore environment if --only-test-environment option is given and environment does not match
            # what the user specified in option
            continue
        click.echo(f'Testing "{server_env}" environment...', nl=False)
        xsoar_client: Client = ctx.obj["server_envs"][server_env]["xsoar_client"]
        try:
            xsoar_client.test_connectivity()
        except ConnectionError as ex:
            if stacktrace:
                raise ConnectionError from ex
            click.echo("FAILED")
            return_code = 1
            continue
        click.echo("OK")
    if ctx.obj["default_environment"] not in ctx.obj["server_envs"]:
        click.echo(f'Error: default environment "{ctx.obj["default_environment"]}" not found in server config.')
        return_code = 1
    ctx.exit(return_code)


@click.command()
def create() -> None:
    """Create a new configuration file based on a template."""
    # if confdir does not exist, create it
    # if conf file does not exist, create it
    config_file = get_config_file_path()
    if config_file.is_file():
        click.confirm(f"WARNING: {config_file} already exists. Overwrite?", abort=True)
    config_file.parent.mkdir(exist_ok=True, parents=True)
    config_data = get_config_file_template_contents()
    config_file.write_text(json.dumps(config_data, indent=4))
    click.echo(f"Wrote template configuration file {config_file}")


@click.option("--environment", default="dev", show_default=True, help="Environment as defined in config file")
@click.option("--key_id", type=int, help="If set then server config for server_version will be set to 8.")
@click.argument("apitoken", type=str)
@click.command()
@click.pass_context
@load_config
def set_credentials(ctx: click.Context, environment: str, apitoken: str, key_id: int) -> None:  # noqa: ARG001
    """Set individual credentials for an environment in the config file."""
    config_file = get_config_file_path()
    config_data = json.loads(config_file.read_text())
    config_data["server_config"][environment]["api_token"] = apitoken
    # If we are given an API key ID, then we know it's supposed to be used in XSOAR 8.
    # Set or remove the xsiam_auth_id accordingly.
    if key_id:
        config_data["server_config"][environment]["xsiam_auth_id"] = key_id
        config_data["server_config"][environment]["server_version"] = 8
    else:
        config_data["server_config"][environment]["server_version"] = 6
        with contextlib.suppress(KeyError):
            config_data["server_config"][environment].pop("xsiam_auth_id")
    config_file.write_text(json.dumps(config_data, indent=4))


config.add_command(create)
config.add_command(validate)
config.add_command(show)
config.add_command(set_credentials)
