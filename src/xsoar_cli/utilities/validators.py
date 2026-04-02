import logging
from collections.abc import Callable
from functools import update_wrapper

import click

from xsoar_cli.error_handling.connection import ConnectionErrorHandler
from xsoar_cli.utilities.config_file import get_xsoar_config

logger = logging.getLogger(__name__)


def validate_environments(*args, **kwargs) -> bool:  # noqa: ANN002, ANN003
    config = get_xsoar_config(kwargs["ctx"])
    return all(config.has_environment(env) for env in args)


def validate_xsoar_connectivity() -> Callable:
    """Decorator that validates XSOAR server connectivity before a command runs.

    Resolves the target environment from ctx.params["environment"], falling back
    to the default environment. Must be called with parentheses.
    """

    def decorator(f: Callable) -> Callable:
        @click.pass_context
        def wrapper(ctx: click.Context, *args, **kwargs) -> Callable:
            config = get_xsoar_config(ctx)
            env_name = ctx.params.get("environment") or config.default_environment

            logger.debug("Testing XSOAR connectivity for environment '%s'", env_name)
            env_config = config.get_environment(env_name)
            client = env_config.client
            try:
                client.test_connectivity()
            except ConnectionError as ex:
                handler = ConnectionErrorHandler()
                logger.info("Connection failed for environment '%s': %s", env_name, handler.get_message(ex))
                click.echo(f"Connection failed for '{env_name}': {handler.get_message(ex)}")
                ctx.exit(1)
            logger.debug("Connectivity OK for environment '%s'", env_name)

            return ctx.invoke(f, *args, **kwargs)

        return update_wrapper(wrapper, f)

    return decorator


def validate_artifacts_provider(f: Callable) -> Callable:
    """Decorator that validates artifact provider configuration and connectivity."""

    @click.pass_context
    def wrapper(ctx: click.Context, *args, **kwargs) -> Callable:
        config = get_xsoar_config(ctx)
        environment = ctx.params.get("environment")
        env_name = environment or config.default_environment

        # Exit early if no artifacts provider is configured
        if not config.environment_has_artifacts(environment):
            logger.debug("No artifact provider configured for environment '%s', skipping validation", env_name)
            return ctx.invoke(f, *args, **kwargs)

        # Test artifact provider connectivity
        env_config = config.get_environment(env_name)
        logger.debug("Testing artifact provider connectivity for environment '%s'", env_name)

        try:
            # Try to get the client (which creates the artifact provider)
            client = env_config.client
            # Test the artifact provider connection
            if client.artifact_provider:
                client.artifact_provider.test_connection()

        except Exception as e:
            logger.info("Artifact provider connection failed for environment '%s': %s", env_name, e)
            click.echo(f"Artifact repository connection failed: {e}")
            click.echo()
            click.echo("Run 'xsoar-cli config validate' to test your configuration")
            ctx.exit(1)

        logger.debug("Artifact provider connectivity OK for environment '%s'", env_name)
        return ctx.invoke(f, *args, **kwargs)

    return update_wrapper(wrapper, f)
