from pathlib import Path

import click
from xsoar_client.xsoar_client import Client
from xsoar_dependency_graph.xsoar_dependency_graph import ContentGraph

from xsoar_cli.utilities import (
    get_xsoar_config,
    load_config,
)


@click.group(help="(BETA) Create dependency graphs from one or more content packs")
def graph() -> None:
    pass

    def diff(ctx: click.Context, manifest: str, environment: str | None) -> None:
        """Prints out the differences (if any) between what is defined in the xsoar_config.json manifest and what is actually
        installed on the XSOAR server."""

        # Detect install content packs not defined in manifest
        # Find content packs defined in manifest but that are not defined
        # Find installed content packs that are outdated


@click.option("--environment", default=None, help="Default environment set in config file.")
@click.option(
    "-urp", "--upstream-repo-path", required=False, type=click.Path(exists=True), help="Path to local clone of Palo Alto content repository"
)
@click.option("-rp", "--repo-path", required=True, type=click.Path(exists=True), help="Path to content repository")
@click.argument("packs", nargs=-1, required=False, type=click.Path(exists=True))
@click.command()
@click.pass_context
@load_config
def generate(ctx: click.Context, packs: tuple[Path], repo_path: str, upstream_repo_path: str, environment: str | None) -> None:
    """BETA

    Generates a XSOAR dependency graph for one or more content packs. If no packs are defined in the [PACKS] argument,
    a dependency graph is created for all content packs in the content repository.

    Usage examples:

    xsoar-cli graph generate -rp . Packs/Pack_one Packs/Pack_two

    xsoar-cli graph generate -rp ."""
    config = get_xsoar_config(ctx)
    xsoar_client: Client = config.get_client(environment)
    installed_content = xsoar_client.get_installed_expired_packs()
    urp = Path(upstream_repo_path)
    rp = Path(repo_path)
    if upstream_repo_path:
        cg: ContentGraph = ContentGraph(repo_path=rp, upstream_repo_path=urp, installed_content=installed_content)  # ty: ignore[invalid-argument-type]
    else:
        cg: ContentGraph = ContentGraph(repo_path=Path(repo_path), installed_content=installed_content)  # ty: ignore[invalid-argument-type]

    packs_list = [Path(item) for item in packs]
    cg.create_content_graph(pack_paths=packs_list)
    cg.plot_connected_components()


graph.add_command(generate)
