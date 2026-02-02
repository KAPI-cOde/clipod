from __future__ import annotations

from pathlib import Path

import click

from clipod import bgm


@click.command(name="bgm")
@click.argument("main", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--layout",
    "-l",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to bgm_layout.json from the web UI.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, path_type=Path),
    required=True,
    help="Output mixed WAV file path.",
)
@click.option("--ffmpeg", default="ffmpeg", show_default=True, help="ffmpeg executable name or path.")
def bgm_command(main: Path, layout: Path, output: Path, ffmpeg: str) -> None:
    """Mix BGM segments with a main audio file using a layout JSON."""
    try:
        data = bgm.load_layout(layout)
        bgm.mix_bgm(main=main, layout=data, output=output, ffmpeg=ffmpeg, base_dir=layout.parent)
    except bgm.LayoutError as exc:
        raise click.ClickException(str(exc)) from exc
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    except Exception as exc:
        raise click.ClickException(f"Failed to mix BGM: {exc}") from exc
