import click


@click.group()
def cli() -> None:
    """Podcast production helper CLI."""


from clipod.commands.record import record_command
from clipod.commands.process import process_command
from clipod.commands.web import web_command
from clipod.commands.trim import trim_command
from clipod.commands.mix import mix_command
from clipod.commands.bgm import bgm_command
from clipod.commands.export import export_command


cli.add_command(record_command, name="record")
cli.add_command(process_command, name="process")
cli.add_command(web_command, name="web")
cli.add_command(trim_command, name="trim")
cli.add_command(mix_command, name="mix")
cli.add_command(bgm_command, name="bgm")
cli.add_command(export_command, name="export")


@cli.command()
def edit() -> None:
    """Edit recorded segments."""
    click.echo("Editing audio... (stub)")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
