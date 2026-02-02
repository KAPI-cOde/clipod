from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import click

from clipod import bgm
from clipod.commands.process import FFMPEG_FILTER
from clipod.web.server import BGM_LAYOUT_FILE


def _resolve_layout(layout: Path | None) -> Path | None:
    if layout is not None:
        return layout
    if BGM_LAYOUT_FILE.exists():
        return BGM_LAYOUT_FILE
    return None


@click.command(name="export")
@click.argument("main", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, path_type=Path),
    default="final.mp3",
    show_default=True,
    help="Output MP3 file path.",
)
@click.option(
    "--layout",
    "-l",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to bgm_layout.json from the web UI.",
)
@click.option("--ffmpeg", default="ffmpeg", show_default=True, help="ffmpeg executable name or path.")
def export_command(main: Path, output: Path, layout: Path | None, ffmpeg: str) -> None:
    """Export final audio with optional BGM and loudness normalization."""
    layout_path = _resolve_layout(layout)
    temp_dir = Path(tempfile.mkdtemp(prefix="clipod_export_"))
    mixed_path = temp_dir / "mixed.wav"
    source_path = main
    try:
        if layout_path:
            data = bgm.load_layout(layout_path)
            bgm.mix_bgm(main=main, layout=data, output=mixed_path, ffmpeg=ffmpeg, base_dir=layout_path.parent)
            source_path = mixed_path

        cmd = [
            ffmpeg,
            "-y",
            "-i",
            str(source_path),
            "-af",
            FFMPEG_FILTER,
            "-codec:a",
            "libmp3lame",
            "-q:a",
            "2",
            str(output),
        ]
        subprocess.run(cmd, check=True)
    except bgm.LayoutError as exc:
        raise click.ClickException(str(exc)) from exc
    except FileNotFoundError as exc:
        raise click.ClickException("ffmpeg not found. Ensure it is installed and on PATH.") from exc
    except subprocess.CalledProcessError as exc:
        raise click.ClickException(f"ffmpeg export failed with exit code {exc.returncode}") from exc
    finally:
        if mixed_path.exists():
            mixed_path.unlink()
        try:
            temp_dir.rmdir()
        except OSError:
            pass
    click.echo(f"Exported audio saved to {output}")
