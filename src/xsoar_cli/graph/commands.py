from pathlib import Path

import click
from xsoar_dependency_graph.xsoar_dependency_graph import ContentGraph


@click.group(help="(BETA) Create dependency graphs from one or more content packs")
def graph() -> None:
    pass


@click.option("-rp", "--repo-path", required=True, type=click.Path(exists=True), help="Path to content repository")
@click.argument("packs", nargs=-1, required=False, type=click.Path(exists=True))
@click.command()
def generate(packs: tuple[Path], repo_path: Path) -> None:
    """BETA

    Generates a XSOAR dependency graph for one or more content packs. If no packs are defined in the [PACKS] argument,
    a dependency graph is created for all content packs in the content repository.

    Usage examples:

    xsoar-cli graph generate -rp . Packs/Pack_one Packs/Pack_two

    xsoar-cli graph generate -rp ."""
    cg: ContentGraph = ContentGraph(repo_path=Path(repo_path))
    packs_list = [Path(item) for item in packs]
    cg.create_content_graph(pack_paths=packs_list)
    cg.plot_connected_components()


graph.add_command(generate)
