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
- `clipod web` — launch the waveform editor with BGM timeline support.
- `clipod export` — export final audio with BGM layout + loudness normalization.

## Web editor
- Waveform editor with a dedicated BGM timeline.
- Multiple BGM blocks with drag/trim placement.
- Default BGM mix at -12 dB with 3s fade in/out.

## Quick Start
1. `clipod record --duration 5 --output test.wav`
2. `clipod web test.wav`
3. `clipod process test.wav processed.wav`
4. `clipod export processed.wav -o output.mp3`
