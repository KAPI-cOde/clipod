from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable


class LayoutError(ValueError):
    """Invalid BGM layout."""


@dataclass(frozen=True)
class BgmSegment:
    path: Path
    start: float
    end: float
    offset: float
    volume: float
    fade_in: float
    fade_out: float

    @property
    def duration(self) -> float:
        return self.end - self.start


def load_layout(path: Path) -> dict:
    try:
        raw = path.read_text()
    except OSError as exc:
        raise LayoutError(f"Layout file not found: {path}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LayoutError(f"Invalid layout JSON: {path}") from exc
    if not isinstance(data, dict) or "segments" not in data:
        raise LayoutError("Layout must include a 'segments' array.")
    if not isinstance(data["segments"], list):
        raise LayoutError("Layout 'segments' must be a list.")
    return data


def _parse_segments(layout: dict, base_dir: Path) -> list[BgmSegment]:
    segments: list[BgmSegment] = []
    for idx, entry in enumerate(layout.get("segments", []), start=1):
        if not isinstance(entry, dict):
            raise LayoutError(f"Segment {idx} must be an object.")
        if "file" not in entry:
            raise LayoutError(f"Segment {idx} missing 'file'.")
        file_path = Path(entry["file"])
        if not file_path.is_absolute():
            file_path = (base_dir / file_path).resolve()
        if not file_path.exists():
            raise LayoutError(f"BGM file not found: {file_path}")
        try:
            start = float(entry["start"])
            end = float(entry["end"])
            offset = float(entry.get("offset", 0.0))
            volume = float(entry.get("volume", 0.25))
            fade_in = float(entry.get("fade_in", 3.0))
            fade_out = float(entry.get("fade_out", 3.0))
        except (TypeError, ValueError) as exc:
            raise LayoutError(f"Segment {idx} has invalid numeric values.") from exc
        if start < 0 or end <= start:
            raise LayoutError(f"Segment {idx} has invalid start/end.")
        if offset < 0:
            raise LayoutError(f"Segment {idx} has invalid offset.")
        if volume < 0:
            raise LayoutError(f"Segment {idx} has invalid volume.")
        if fade_in < 0 or fade_out < 0:
            raise LayoutError(f"Segment {idx} has invalid fade durations.")
        segments.append(
            BgmSegment(
                path=file_path,
                start=start,
                end=end,
                offset=offset,
                volume=volume,
                fade_in=fade_in,
                fade_out=fade_out,
            )
        )
    return segments


def _build_filter(segments: Iterable[BgmSegment]) -> tuple[str, str]:
    filter_parts: list[str] = []
    mix_inputs = ["[0:a]"]
    for idx, seg in enumerate(segments):
        duration = seg.duration
        if duration <= 0:
            raise LayoutError("Segment duration must be positive.")
        fade_in = min(seg.fade_in, duration)
        fade_out = min(seg.fade_out, duration)
        fade_out_start = max(0.0, duration - fade_out)
        delay_ms = int(round(seg.start * 1000))
        chain = [
            f"[{idx + 1}:a]atrim=start={seg.offset}:duration={duration}",
            "asetpts=PTS-STARTPTS",
        ]
        if fade_in > 0:
            chain.append(f"afade=t=in:st=0:d={fade_in}")
        if fade_out > 0:
            chain.append(f"afade=t=out:st={fade_out_start}:d={fade_out}")
        chain.append(f"volume={seg.volume}")
        chain.append(f"adelay={delay_ms}:all=1")
        label = f"[bgm{idx}]"
        filter_parts.append(",".join(chain) + label)
        mix_inputs.append(label)
    filter_parts.append(
        f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:duration=first:dropout_transition=0[mix]"
    )
    return ";".join(filter_parts), "[mix]"


def mix_bgm(
    main: Path,
    layout: dict,
    output: Path,
    ffmpeg: str = "ffmpeg",
    base_dir: Path | None = None,
    log_command: Callable[[list[str]], None] | None = None,
) -> None:
    if not main.exists():
        raise LayoutError(f"Main audio not found: {main}")
    base_dir = base_dir or Path.cwd()
    segments = _parse_segments(layout, base_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    if not segments:
        if main.resolve() == output.resolve():
            raise LayoutError("Output must differ from input when no BGM segments exist.")
        shutil.copy2(main, output)
        return
    filter_complex, output_label = _build_filter(segments)
    cmd: list[str] = [ffmpeg, "-y", "-i", str(main)]
    for seg in segments:
        cmd.extend(["-i", str(seg.path)])
    cmd.extend(["-filter_complex", filter_complex, "-map", output_label, str(output)])
    print(f"MAIN FILE: {main}", file=sys.stderr, flush=True)
    print(f"OUTPUT FILE: {output}", file=sys.stderr, flush=True)
    print(f"BGM LAYOUT: {layout}", file=sys.stderr, flush=True)
    print(f"FULL FFMPEG COMMAND: {' '.join(cmd)}", file=sys.stderr, flush=True)
    if log_command:
        log_command(cmd)
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"RETURN CODE: {result.returncode}", file=sys.stderr, flush=True)
        print(f"STDERR: {result.stderr}", file=sys.stderr, flush=True)
    except FileNotFoundError as exc:
        raise FileNotFoundError("ffmpeg not found. Ensure it is installed and on PATH.") from exc
    except subprocess.CalledProcessError:
        raise
