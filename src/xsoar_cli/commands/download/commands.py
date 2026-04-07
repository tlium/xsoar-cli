import click


@click.group(help="Create, validate, and manage CLI configuration")
def download() -> None:
    pass


@click.command("download")
def download_item():
    pass


download.add_command(download)
