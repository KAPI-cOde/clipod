from __future__ import annotations

import json
import subprocess
from pathlib import Path

import click

from clipod.web.server import SELECTION_FILE


def _load_selection(selection_path: Path) -> tuple[float, float]:
    if not selection_path.exists():
        raise click.ClickException(f"Selection file not found: {selection_path}")
    try:
        data = json.loads(selection_path.read_text())
        start = float(data["start"])
        end = float(data["end"])
    except Exception as exc:
        raise click.ClickException(f"Invalid selection file: {selection_path}") from exc
    if start < 0 or end <= start:
        raise click.ClickException(f"Invalid trim range: start={start}, end={end}")
    return start, end


@click.command(name="trim")
@click.argument("input", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("output", type=click.Path(dir_okay=False, path_type=Path))
@click.option(
    "--selection",
    "-s",
    type=click.Path(dir_okay=False, path_type=Path),
    default=SELECTION_FILE,
    show_default=True,
    help="Path to selection JSON with start/end seconds.",
)
@click.option(
    "--ffmpeg",
    default="ffmpeg",
    show_default=True,
    help="ffmpeg executable name or path.",
)
def trim_command(input: Path, output: Path, selection: Path, ffmpeg: str) -> None:
    """Trim audio based on start/end seconds stored in selection.json."""
    start, end = _load_selection(selection)
    duration = end - start
    cmd = [
        ffmpeg,
        "-y",
        "-ss",
        str(start),
        "-t",
        str(duration),
        "-i",
        str(input),
        "-c",
        "copy",
        str(output),
    ]
    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError as exc:
        raise click.ClickException("ffmpeg not found. Ensure it is installed and on PATH.") from exc
    except subprocess.CalledProcessError as exc:
        raise click.ClickException(f"ffmpeg trim failed with exit code {exc.returncode}") from exc
    click.echo(f"Trimmed audio saved to {output} (start={start:.2f}s, end={end:.2f}s)")
