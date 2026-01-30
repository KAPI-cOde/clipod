from __future__ import annotations

import sys
import time
import wave
from pathlib import Path
from typing import Iterable

import click
import numpy as np
import sounddevice as sd


def _write_wav(path: Path, data: np.ndarray, sample_rate: int, channels: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # 16-bit PCM
        wf.setframerate(sample_rate)
        wf.writeframes(data.tobytes())


def _progress(duration: float, step: float = 0.25) -> Iterable[None]:
    start = time.time()
    while True:
        elapsed = time.time() - start
        percent = min(1.0, elapsed / duration) * 100
        click.echo(f"\rRecording... {percent:05.1f}% ", nl=False)
        yield
        if elapsed >= duration:
            break
        time.sleep(step)
    click.echo("\rRecording... 100.0% ")


def record_audio(
    output: Path,
    duration: float,
    sample_rate: int,
    channels: int,
) -> None:
    if duration <= 0:
        raise click.BadParameter("Duration must be positive.")
    if channels not in (1, 2):
        raise click.BadParameter("Channels must be 1 (mono) or 2 (stereo).")

    num_frames = int(duration * sample_rate)
    click.echo(f"Recording {duration:.2f}s at {sample_rate} Hz, channels={channels} -> {output}")

    try:
        recording = sd.rec(
            frames=num_frames,
            samplerate=sample_rate,
            channels=channels,
            dtype="int16",
        )
    except Exception as exc:  # sounddevice raises various backend errors
        raise click.ClickException(f"Failed to start recording: {exc}") from exc

    for _ in _progress(duration):
        pass

    try:
        sd.wait()
    except Exception as exc:
        raise click.ClickException(f"Recording failed: {exc}") from exc

    _write_wav(output, recording, sample_rate, channels)
    click.echo(f"Saved: {output}")


@click.command()
@click.option(
    "--duration",
    "-d",
    type=float,
    required=True,
    help="Recording length in seconds.",
)
@click.option(
    "--sample-rate",
    "-r",
    type=int,
    default=44100,
    show_default=True,
    help="Sample rate in Hz.",
)
@click.option(
    "--channels",
    "-c",
    type=int,
    default=1,
    show_default=True,
    help="Number of channels (1=mono, 2=stereo).",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, path_type=Path),
    default="output.wav",
    show_default=True,
    help="Output WAV file path.",
)
def record_command(duration: float, sample_rate: int, channels: int, output: Path) -> None:
    """Record audio from the default microphone into a WAV file."""
    try:
        record_audio(output=output, duration=duration, sample_rate=sample_rate, channels=channels)
    except click.ClickException:
        raise
    except Exception as exc:
        raise click.ClickException(f"Unexpected error: {exc}") from exc
