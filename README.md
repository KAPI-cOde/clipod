# clipod

Podcast-specific CLI tool — "80% done before opening Audacity".

## Setup

```bash
pip install -e .
```

## Usage

```bash
clipod --help
```

Commands:

- `clipod record --duration 5 --sample-rate 44100 --channels 1 --output output.wav` — record audio input.
- `clipod process` — process audio (denoise, normalize, etc.).
- `clipod trim` — trim audio based on selection JSON.
- `clipod mix` — mix tracks together.
- `clipod web [audio.wav]` — launch the waveform editor (record directly in the browser or load a file).
- `clipod export` — export final audio with BGM layout + loudness normalization.

## Web editor
- Record directly in the browser with a live waveform preview.
- Punch-in re-recording for selected regions.
- Waveform editor with a dedicated BGM timeline.
- Multiple BGM blocks with drag/trim placement.
- Default BGM mix at -12 dB with 3s fade in/out.

## Quick Start
1. `clipod web`
2. Record in the browser, then edit the waveform.
3. `clipod export auto.wav -o output.mp3`
