import contextlib
import json
import logging
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from xsoar_client.xsoar_client import Client

from xsoar_cli.utilities.config_file import (
    get_config_file_contents,
    get_config_file_path,
    get_config_file_template_contents,
    get_xsoar_config,
    load_config,
)

logger = logging.getLogger(__name__)


@click.group(help="Create, validate, and manage CLI configuration")
def config() -> None:
    pass


@click.command()
@click.option("--unmask", "masked", is_flag=True, default=False)
@click.pass_context
@load_config
def show(ctx: click.Context, masked: bool) -> None:
    """Print current config. API keys are masked by default."""
    config_file = get_config_file_path()
    logger.info("Showing config (masked=%s)", not masked)
    config = get_config_file_contents(config_file)
    if not masked:
        for key in config["server_config"]:
            config["server_config"][key]["api_token"] = "MASKED"  # noqa: S105
            if "azure_storage_access_token" in config["server_config"][key]:
                config["server_config"][key]["azure_storage_access_token"] = "*****"  # noqa: S105

    print(json.dumps(config, indent=4))
    ctx.exit()


@click.command()
@click.option("--only-test-environment", default=None, show_default=True, help="Environment as defined in config file")
@click.option("--stacktrace", is_flag=True, default=False, help="Print full stack trace on config validation failure.")
@click.pass_context
@load_config
def validate(ctx: click.Context, only_test_environment: str, stacktrace: bool) -> None:
    """Validate the configuration file and test connectivity for each environment."""
    return_code = 0
    config = get_xsoar_config(ctx)
    logger.info("Validating config (environments: %s)", config.environment_names)
    for server_env in config.environment_names:
        if only_test_environment and server_env != only_test_environment:
            # Ignore environment if --only-test-environment option is given and environment does not match
            # what the user specified in option
            logger.debug("Skipping environment '%s' (not selected)", server_env)
            continue
        logger.debug("Testing environment '%s'", server_env)
        click.echo(f'Testing "{server_env}" environment')
        xsoar_client: Client = config.get_client(server_env)
        click.echo("  - XSOAR connectivity: ", nl=False)
        try:
            xsoar_client.test_connectivity()
            logger.debug("XSOAR connectivity OK for '%s'", server_env)
            click.echo("OK")
        except ConnectionError as ex:
            logger.info("XSOAR connectivity failed for '%s': %s", server_env, ex)
            if stacktrace:
                # Print the original cause if available, otherwise the main message
                error_msg = str(ex.__cause__) if ex.__cause__ else str(ex)
                click.echo(error_msg)
            else:
                click.echo("FAILED")
            return_code = 1
        if config.environment_has_artifacts(server_env):
            click.echo("  - Artifacts repository: ", nl=False)
            try:
                if xsoar_client.artifact_provider:
                    xsoar_client.artifact_provider.test_connection()
                    logger.debug("Artifact provider OK for '%s'", server_env)
                    click.echo("OK")
                else:
                    logger.debug("No artifact provider configured for '%s'", server_env)
                    click.echo("No artifact provider configured")
            except Exception as ex:
                logger.info("Artifact provider failed for '%s': %s", server_env, ex)
                if stacktrace:
                    # Print the original cause if available, otherwise the main message
                    error_msg = str(ex.__cause__) if ex.__cause__ else str(ex)
                    click.echo(error_msg)
                else:
                    click.echo("FAILED")
                return_code = 1
    if not config.has_environment(config.default_environment):
        logger.info("Default environment '%s' not found in server config", config.default_environment)
        click.echo(f'Error: default environment "{config.default_environment}" not found in server config.')
        return_code = 1
    logger.info("Config validation finished with return code %d", return_code)
    ctx.exit(return_code)


@click.command()
def create() -> None:
    """Create a new configuration file based on a template."""
    # if confdir does not exist, create it
    # if conf file does not exist, create it
    config_file = get_config_file_path()
    logger.debug("Config file path: %s", config_file)
    if config_file.is_file():
        logger.debug("Config file already exists, prompting for overwrite")
        click.confirm(f"WARNING: {config_file} already exists. Overwrite?", abort=True)
    config_file.parent.mkdir(exist_ok=True, parents=True)
    config_data = get_config_file_template_contents()
    config_file.write_text(json.dumps(config_data, indent=4))
    logger.info("Created template config file at %s", config_file)
    click.echo(f"Wrote template configuration file {config_file}")


@click.command()
@click.option("--environment", default="dev", show_default=True, help="Environment as defined in config file")
@click.option("--key_id", type=int, help="If set then server config for server_version will be set to 8.")
@click.argument("apitoken", type=str)
@click.pass_context
@load_config
def set_credentials(ctx: click.Context, environment: str, apitoken: str, key_id: int) -> None:  # noqa: ARG001
    """Set API credentials for an environment in the config file."""
    config_file = get_config_file_path()
    logger.info("Setting credentials for environment '%s' (server_version=%s)", environment, 8 if key_id else 6)
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
    logger.info("Credentials updated for environment '%s'", environment)


@click.command()
@click.option("--environment", default="dev", show_default=True, help="Environment as defined in config file")
@click.argument("sastoken", type=str)
@click.pass_context
@load_config
def set_azure_token(ctx: click.Context, environment: str, sastoken: str) -> None:  # noqa: ARG001
    """Set Azure Blob Storage SAS token for an environment in the config file."""
    config_file = get_config_file_path()
    logger.info("Setting Azure SAS token for environment '%s'", environment)
    config_data = json.loads(config_file.read_text())
    config_data["server_config"][environment]["azure_storage_access_token"] = sastoken
    config_file.write_text(json.dumps(config_data, indent=4))
    logger.info("Azure SAS token updated for environment '%s'", environment)


config.add_command(create)
config.add_command(validate)
config.add_command(show)
config.add_command(set_credentials)
config.add_command(set_azure_token)
