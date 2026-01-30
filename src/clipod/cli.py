import click


@click.group()
def cli() -> None:
    """Podcast production helper CLI."""


from clipod.commands.record import record_command


cli.add_command(record_command, name="record")


@cli.command()
def edit() -> None:
    """Edit recorded segments."""
    click.echo("Editing audio... (stub)")


@cli.command()
def process() -> None:
    """Process audio (denoise, normalize, etc.)."""
    click.echo("Processing audio... (stub)")


@cli.command()
def mix() -> None:
    """Mix tracks together."""
    click.echo("Mixing tracks... (stub)")


@cli.command()
def export() -> None:
    """Export final audio."""
    click.echo("Exporting audio... (stub)")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
