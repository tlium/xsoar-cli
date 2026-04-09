from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import click

from xsoar_cli.utilities.config_file import get_xsoar_config, load_config
from xsoar_cli.utilities.validators import validate_xsoar_connectivity

if TYPE_CHECKING:
    from xsoar_dependency_graph.xsoar_dependency_graph import ContentGraph

    from xsoar_cli.xsoar_client.client import Client

logger = logging.getLogger(__name__)


def _common_graph_options(func):
    """Stacks the Click options and arguments shared by all graph subcommands."""
    func = click.argument("packs", nargs=-1, required=False, type=click.Path(exists=True))(func)
    func = click.option("-rp", "--repo-path", required=True, type=click.Path(exists=True), help="Path to content repository")(func)
    func = click.option(
        "-urp",
        "--upstream-repo-path",
        required=False,
        type=click.Path(exists=True),
        help="Path to local clone of Palo Alto content repository",
    )(func)
    func = click.option("--environment", default=None, help="Default environment set in config file.")(func)
    return func


def _build_content_graph(
    ctx: click.Context,
    packs: tuple[Path],
    repo_path: str,
    upstream_repo_path: str | None,
    environment: str | None,
) -> ContentGraph:
    """Shared setup: load config, connect to XSOAR, build and return a ContentGraph."""
    # Lazy import for performance reasons
    from xsoar_dependency_graph.xsoar_dependency_graph import ContentGraph

    config = get_xsoar_config(ctx)
    xsoar_client: Client = config.get_client(environment)
    logger.info("Generating dependency graph (environment: '%s', repo: '%s')", environment or config.default_environment, repo_path)

    installed_content = xsoar_client.packs.get_installed_expired()
    logger.debug("Fetched %d installed/expired pack(s) from server", len(installed_content))

    rp = Path(repo_path)
    if upstream_repo_path:
        urp = Path(upstream_repo_path)
        logger.debug("Using upstream repo path: %s", urp)
        cg = ContentGraph(repo_path=rp, upstream_repo_path=urp, installed_content=installed_content)  # ty: ignore[invalid-argument-type]
    else:
        cg = ContentGraph(repo_path=rp, installed_content=installed_content)  # ty: ignore[invalid-argument-type]

    packs_list = [Path(item) for item in packs]
    if packs_list:
        logger.debug("Generating graph for %d specified pack(s): %s", len(packs_list), [str(p) for p in packs_list])
    else:
        logger.debug("No packs specified, generating graph for all packs in repo")
    cg.create_content_graph(pack_paths=packs_list)
    return cg


@click.group()
def graph() -> None:
    """(BETA) Create dependency graphs from one or more content packs"""
    pass


@_common_graph_options
@click.command()
@click.pass_context
@load_config
@validate_xsoar_connectivity()
def generate(ctx: click.Context, packs: tuple[Path], repo_path: str, upstream_repo_path: str, environment: str | None) -> None:
    """BETA

    Generates a XSOAR dependency graph for one or more content packs. If no packs are defined in the [PACKS] argument,
    a dependency graph is created for all content packs in the content repository.

    Usage examples:

    xsoar-cli graph generate -rp . Packs/Pack_one Packs/Pack_two

    xsoar-cli graph generate -rp ."""
    cg = _build_content_graph(ctx, packs, repo_path, upstream_repo_path, environment)
    cg.plot_connected_components()
    logger.info("Dependency graph generation complete")


@click.command()
@click.option("-of", "--output-format", type=click.Choice(["GML", "GraphML"]), default="GML", help="File format for the exported graph")
@click.option("-o", "--output-path", required=True, type=click.Path(exists=True), help="Path to output directory.")
@_common_graph_options
@click.pass_context
@load_config
@validate_xsoar_connectivity()
def export(
    ctx: click.Context,
    packs: tuple[Path],
    repo_path: str,
    upstream_repo_path: str,
    environment: str | None,
    output_path: Path,
    output_format: str,
) -> None:
    """BETA

    Exports a XSOAR dependency graph to a file. If no packs are defined in the [PACKS] argument,
    a dependency graph is created for all content packs in the content repository.

    Usage examples:

    xsoar-cli graph export -rp . -o /tmp Packs/Pack_one Packs/Pack_two

    xsoar-cli graph export -rp . -o /tmp -of GraphML"""
    cg = _build_content_graph(ctx, packs, repo_path, upstream_repo_path, environment)
    output = cg.export(output_path=output_path, output_format=output_format)
    logger.debug("Done exporting: %s", output)
    click.echo(f"Done exporting: {output}")


graph.add_command(generate)
graph.add_command(export)
