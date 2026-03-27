import json
import logging
from collections.abc import Callable
from functools import update_wrapper
from pathlib import Path
from typing import cast

import click

from xsoar_cli.configuration import XSOARConfig

logger = logging.getLogger(__name__)


def get_xsoar_config(ctx: click.Context) -> XSOARConfig:
    """Helper to get typed config from context."""
    return cast(XSOARConfig, ctx.obj)


def get_config_file_path() -> Path:
    homedir = Path.home()
    config_file_path = homedir / ".config/xsoar-cli"
    config_file_name = "config.json"
    return Path(config_file_path / config_file_name)


def get_config_file_contents(filepath: Path):  # noqa: ANN201
    return json.load(filepath.open("r"))


def get_config_file_template_contents() -> dict:
    return {
        "default_environment": "dev",
        "default_new_case_type": "",
        "custom_pack_authors": ["SOMEONE"],
        "skip_version_check": True,
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
        logger.debug("Loading config from %s", config_file_path)
        if not config_file_path.is_file():
            click.echo(
                'Config file not found. Please create a template config file using "xsoar-cli config create" and replace placeholder values before retrying.',
            )
            ctx.exit(1)

        config_dict = get_config_file_contents(config_file_path)
        ctx.obj = XSOARConfig(config_dict)
        logger.debug("Config loaded with environments: %s", ctx.obj.environment_names)

        # Validate environment if provided
        if "environment" in ctx.params and ctx.params["environment"] is not None:
            config = get_xsoar_config(ctx)
            if not config.has_environment(ctx.params["environment"]):
                logger.info("Invalid environment requested: '%s'", ctx.params["environment"])
                click.echo(f"Invalid environment: {ctx.params['environment']}")
                click.echo(f"Available environments as defined in config file are: {config.environment_names}")
                ctx.exit(1)

        return ctx.invoke(f, *args, **kwargs)

    return update_wrapper(wrapper, f)
