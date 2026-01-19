import contextlib
import json
from collections.abc import Callable
from functools import update_wrapper
from pathlib import Path

import click
from xsoar_client.artifact_providers.azure import AzureArtifactProvider
from xsoar_client.artifact_providers.s3 import S3ArtifactProvider
from xsoar_client.config import ClientConfig
from xsoar_client.xsoar_client import Client


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
        if (
            "environment" in ctx.params
            and ctx.params["environment"] not in ctx.obj["server_envs"]
            and ctx.params["environment"] is not None
        ):
            click.echo(f"Invalid environment: {ctx.params['environment']}")
            click.echo(f"Available environments as defined in config file are: {list(ctx.obj['server_envs'])}")
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
        if "environment" in ctx.params:  # noqa: SIM108
            key = ctx.params["environment"]
        else:
            key = ctx.obj["default_environment"]

        with contextlib.suppress(KeyError):
            location = ctx.obj["server_envs"][key].get("artifacts_location", None)
            if not location:
                click.echo("Command requires artifacts repository, but no artifacts_location defined in config.")
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
        ctx.obj["server_envs"][key] = {}
        server_version = config["server_config"][key]["server_version"]
        custom_pack_authors = config["custom_pack_authors"]

        server_url = config["server_config"][key]["base_url"]
        api_token = config["server_config"][key]["api_token"]
        verify_ssl = config["server_config"][key]["verify_ssl"]
        xsiam_auth_id = config["server_config"][key].get("xsiam_auth_id", "")

        xsoar_client_config = ClientConfig(
            server_version=server_version,
            custom_pack_authors=custom_pack_authors,
            api_token=api_token,
            server_url=server_url,
            xsiam_auth_id=xsiam_auth_id,
            verify_ssl=verify_ssl,
        )

        artifacts_location = config["server_config"][key].get("artifacts_location", None)
        if artifacts_location == "S3":
            bucket_name = config["server_config"][key].get("s3_bucket_name", None)
            artifact_provider = S3ArtifactProvider(bucket_name=bucket_name)
        elif artifacts_location == "Azure":
            url = config["server_config"][key]["azure_blobstore_url"]
            container_name = config["server_config"][key]["azure_container_name"]
            access_token = config["server_config"][key].get("azure_storage_access_token", "")
            artifact_provider = AzureArtifactProvider(storage_account_url=url, container_name=container_name, access_token=access_token)
        else:
            artifact_provider = None
        xsoar_client = Client(config=xsoar_client_config, artifact_provider=artifact_provider)

        ctx.obj["server_envs"][key]["xsoar_client"] = xsoar_client
