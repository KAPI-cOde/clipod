from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List

import click


def _build_inputs(main: Path, intro: Path | None, outro: Path | None) -> List[str]:
    inputs: List[str] = []
    streams = 0
    for path in (intro, main, outro):
        if path is None:
            continue
        inputs.extend(["-i", str(path)])
        streams += 1
    if streams == 0:
        raise click.ClickException("No inputs provided. At least provide main audio.")
    return inputs


@click.command(name="mix")
@click.argument("main", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("output", type=click.Path(dir_okay=False, path_type=Path))
@click.option("--intro", type=click.Path(exists=True, dir_okay=False, path_type=Path), help="Intro audio file.")
@click.option("--outro", type=click.Path(exists=True, dir_okay=False, path_type=Path), help="Outro audio file.")
@click.option("--ffmpeg", default="ffmpeg", show_default=True, help="ffmpeg executable name or path.")
def mix_command(main: Path, output: Path, intro: Path | None, outro: Path | None, ffmpeg: str) -> None:
    """Concatenate intro + main + outro using ffmpeg concat filter."""
    inputs = _build_inputs(main, intro, outro)
    stream_count = (1 if intro else 0) + 1 + (1 if outro else 0)

    # Build concat filter with audio only
    inputs_spec = "".join(f"[{i}:a]" for i in range(stream_count))
    filter_arg = f"{inputs_spec}concat=n={stream_count}:v=0:a=1[outa]"

    cmd = [
        ffmpeg,
        "-y",
        *inputs,
        "-filter_complex",
        filter_arg,
        "-map",
        "[outa]",
        str(output),
    ]

    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError as exc:
        raise click.ClickException("ffmpeg not found. Ensure it is installed and on PATH.") from exc
    except subprocess.CalledProcessError as exc:
        raise click.ClickException(f"ffmpeg mix failed with exit code {exc.returncode}") from exc

    parts = [p for p in (intro and intro.name, main.name, outro and outro.name) if p]
    click.echo(f"Mixed {' + '.join(parts)} -> {output}")
