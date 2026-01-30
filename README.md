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
- `clipod edit` — edit recorded segments.
- `clipod process` — process audio (denoise, normalize, etc.).
- `clipod mix` — mix tracks together.
- `clipod export` — export final audio.
