import json
from collections.abc import Callable
from functools import update_wrapper
from pathlib import Path
from typing import cast

import click

from xsoar_cli.configuration import XSOARConfig


def get_xsoar_config(ctx: click.Context) -> XSOARConfig:
    """Helper to get typed config from context."""
    return cast(XSOARConfig, ctx.obj)


def parse_string_to_dict(input_string: str | None, delimiter: str) -> dict:
    if not input_string:
        return {}
    # Parse a string into a python dictionary
    pairs = [pair.split("=", 1) for pair in input_string.split(delimiter)]
    # Filter pairs that have exactly 2 parts (key and value) after splitting by "="
    valid_pairs = [pair for pair in pairs if len(pair) == 2]  # noqa: PLR2004
    return {key.strip(): value.strip() for key, value in valid_pairs}


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
                "base_url": "https://api-xsoar-v8.example.com",
                "api_token": "YOUR API TOKEN HERE",
                "artifacts_location": "S3",
                "s3_bucket_name": "xsoar-cicd-prod",
                "verify_ssl": False,
                "server_version": 8,
                "xsiam_auth_id": 123,
            },
        },
    }


def validate_environments(*args, **kwargs) -> bool:  # noqa: ANN002, ANN003
    config = get_xsoar_config(kwargs["ctx"])
    return all(config.has_environment(env) for env in args)


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

        config_dict = get_config_file_contents(config_file_path)
        ctx.obj = XSOARConfig(config_dict)

        # Validate environment if provided
        if "environment" in ctx.params and ctx.params["environment"] is not None:
            config = get_xsoar_config(ctx)
            if not config.has_environment(ctx.params["environment"]):
                click.echo(f"Invalid environment: {ctx.params['environment']}")
                click.echo(f"Available environments as defined in config file are: {config.environment_names}")
                ctx.exit(1)

        return ctx.invoke(f, *args, **kwargs)

    return update_wrapper(wrapper, f)


def fail_if_no_artifacts_provider(f: Callable) -> Callable:
    """
    This function is only to be used as a decorator for various xsoar-cli subcommands, and only AFTER the load_config decorator has been called.
    The intention is to fail gracefully if any subcommand is executed which requires an artifacts provider."
    """

    @click.pass_context
    def wrapper(ctx: click.Context, *args, **kwargs) -> Callable:  # noqa: ANN002, ANN003
        config = get_xsoar_config(ctx)
        environment = ctx.params.get("environment")

        if not config.environment_has_artifacts(environment):
            click.echo("Command requires artifacts repository, but no artifacts_location defined in config.")
            ctx.exit(1)

        return ctx.invoke(f, *args, **kwargs)

    return update_wrapper(wrapper, f)
