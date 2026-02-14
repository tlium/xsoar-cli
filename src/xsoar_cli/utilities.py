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


def validate_artifacts_provider(f: Callable) -> Callable:
    """Decorator that validates artifact provider configuration and connectivity."""

    @click.pass_context
    def wrapper(ctx: click.Context, *args, **kwargs) -> Callable:
        config = get_xsoar_config(ctx)
        environment = ctx.params.get("environment")

        # Exit early if no artifacts provider is configured
        if not config.environment_has_artifacts(environment):
            return ctx.invoke(f, *args, **kwargs)

        # Test artifact provider connectivity
        env_name = environment or config.default_environment
        env_config = config._environments[env_name]

        try:
            # Try to get the client (which creates the artifact provider)
            client = env_config.client
            # Test the artifact provider connection
            if client.artifact_provider:
                client.artifact_provider.test_connection()

        except Exception as e:
            click.echo(f"Artifact repository connection failed: {e}")
            click.echo()
            click.echo("Run 'xsoar-cli config validate' to test your configuration")
            ctx.exit(1)

        return ctx.invoke(f, *args, **kwargs)

    return update_wrapper(wrapper, f)


def find_installed_packs_not_in_manifest(installed_packs, manifest_data) -> list[dict[str, str]]:
    """Find packs that are installed on the XSOAR server but missing manifest definitions."""
    undefined_packs = []
    for pack in installed_packs:
        for key in manifest_data:
            installed = next((item for item in manifest_data[key] if item["id"] == pack["id"]), {})
            if installed:
                break
        if not installed:
            undefined_packs.append(pack)
    return undefined_packs


def find_packs_in_manifest_not_installed(installed_packs, manifest_data):
    """Find packs defined in the manifest that are not installed on the XSOAR server."""
    not_installed = []
    for key in manifest_data:
        for pack in manifest_data[key]:
            installed = next((item for item in installed_packs if item["id"] == pack["id"]), {})
            if not installed:
                not_installed.append(pack)
                break
    return not_installed


def find_version_mismatch(installed_packs, manifest_data):
    """Find packs where the version installed in XSOAR differs from the version defined in the manifest."""
    outdated = []
    for key in manifest_data:
        for pack in manifest_data[key]:
            installed = next((item for item in installed_packs if item["id"] == pack["id"]), {})
            if not installed:
                # We don't care about packs that are not installed here. That use case is handled
                # in a separate function
                continue
            if installed["currentVersion"] != pack["version"]:
                tmpobj = {"id": pack["id"], "manifest_version": pack["version"], "installed_version": installed["currentVersion"]}
                outdated.append(tmpobj)
                break
    return outdated
