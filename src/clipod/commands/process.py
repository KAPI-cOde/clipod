from __future__ import annotations

import subprocess
from pathlib import Path

import click


FFMPEG_FILTER = (
    "afftdn=nf=-25,"
    "highpass=f=80,"
    "equalizer=f=3000:t=h:width_type=q:width=1:g=3,"
    "acompressor=threshold=-18dB:ratio=3:attack=20:release=200,"
    "loudnorm=I=-16:LRA=11:TP=-1.5"
)


@click.command(name="process")
@click.argument("input", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("output", type=click.Path(dir_okay=False, path_type=Path))
@click.option(
    "--sample-rate",
    "-r",
    type=int,
    default=44100,
    show_default=True,
    help="Output sample rate.",
)
@click.option(
    "--channels",
    "-c",
    type=int,
    default=1,
    show_default=True,
    help="Output channels (1=mono, 2=stereo).",
)
@click.option(
    "--ffmpeg",
    default="ffmpeg",
    show_default=True,
    help="ffmpeg executable name or path.",
)
def process_command(input: Path, output: Path, sample_rate: int, channels: int, ffmpeg: str) -> None:
    """Apply denoise, EQ, compression, and loudness normalization via ffmpeg."""
    if channels not in (1, 2):
        raise click.BadParameter("Channels must be 1 (mono) or 2 (stereo).")

    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(input),
        "-af",
        FFMPEG_FILTER,
        "-ar",
        str(sample_rate),
        "-ac",
        str(channels),
        str(output),
    ]
    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError as exc:
        raise click.ClickException("ffmpeg not found. Ensure it is installed and on PATH.") from exc
    except subprocess.CalledProcessError as exc:
        raise click.ClickException(f"ffmpeg processing failed with exit code {exc.returncode}") from exc
    click.echo(f"Processed audio saved to {output}")
