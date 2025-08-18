import json
from functools import update_wrapper
from pathlib import Path
from typing import Callable

import click
from xsoar_client.xsoar_client import Client


def get_config_file_template_contents() -> dict:
    return {
        "default_environment": "dev",
        "default_new_case_type": "",
        "custom_pack_authors": ["SOMEONE"],
        "server_config": {
            "dev": {
                "base_url": "https://xsoar.example.com",
                "api_token": "YOUR API TOKEN HERE",
                "artifacts_location": "S3",
                "s3_bucket_name": "xsoar-cicd",
                "verify_ssl": "/path/to/your/CA_bundle.pem",
                "server_version": 6,
            },
            "prod": {
                "base_url": "https://xsoar.example.com",
                "api_token": "YOUR API TOKEN HERE",
                "artifacts_location": "S3",
                "s3_bucket_name": "xsoar-cicd-prod",
                "verify_ssl": False,
                "server_version": 6,
            },
        },
    }


def validate_environments(*args, **kwargs) -> bool:  # noqa: ANN002, ANN003
    return all(env in kwargs["ctx"].obj["server_envs"] for env in args)


def get_config_file_path() -> Path:
    homedir = Path.home()
    config_file_path = homedir / ".config/xsoar-cli"
    config_file_name = "config.json"
    return Path(config_file_path / config_file_name)


def get_config_file_contents(filepath: Path):  # noqa: ANN201
    return json.load(filepath.open("r"))


def load_config(f: Callable) -> Callable:
    """
    This function is only to be used as a decorator for various xsoar-cli subcommands. Loads and parses the config file if
    exists, or prompts the user to create one otherwise.
    If an illegal environment is provided by the user, i.e by invoking "xsoar-cli command --environment illegal subcommand",
    then prints out helpful error message and returns non-zero exit value.
    """

    @click.pass_context
    def wrapper(ctx: click.Context, *args, **kwargs) -> Callable:  # noqa: ANN002, ANN003
        config_file_path = get_config_file_path()
        if not config_file_path.is_file():
            click.echo(
                'Config file not found. Please create a template config file using "xsoar-cli config create" and replace placeholder values before retrying.',
            )
            ctx.exit(1)
        config = get_config_file_contents(config_file_path)
        parse_config(config, ctx)
        if "environment" in ctx.params and ctx.params["environment"] not in ctx.obj["server_envs"]:
            click.echo(f"Invalid environment: {ctx.params['environment']}")
            click.echo(f"Available environments as defined in config file are: {list(ctx.obj['server_envs'])}")
            ctx.exit(1)
        return ctx.invoke(f, *args, **kwargs)

    return update_wrapper(wrapper, f)


def parse_config(config: dict, ctx: click.Context) -> None:
    # Set the two XSOAR client objects in Click Context for use in later functions
    ctx.obj = {}
    ctx.obj["default_environment"] = config["default_environment"]
    ctx.obj["custom_pack_authors"] = config["custom_pack_authors"]
    ctx.obj["default_new_case_type"] = config["default_new_case_type"]
    ctx.obj["server_envs"] = {}
    for key in config["server_config"]:
        ctx.obj["server_envs"][key] = Client(
            api_token=config["server_config"][key]["api_token"],
            server_url=config["server_config"][key]["base_url"],
            verify_ssl=config["server_config"][key]["verify_ssl"],
            custom_pack_authors=config["custom_pack_authors"],
            xsiam_auth_id=config["server_config"][key].get("xsiam_auth_id", ""),
            server_version=config["server_config"][key]["server_version"],
            artifacts_location=config["server_config"][key]["artifacts_location"],
            s3_bucket_name=config["server_config"][key]["s3_bucket_name"],
        )
