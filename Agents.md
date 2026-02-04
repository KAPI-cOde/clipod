# Agents

This file captures the default operating guidelines for automated changes in this repository.

## Principles
- Stability and data safety come first.
- Keep the UI minimal and focused on waveforms.
- Prefer simple, readable code over cleverness.
- Small, focused changes only; avoid unrelated refactors.

## Web UI (src/clipod/web/index.html)
- Keep recording UX calm: low-intensity waveform, warm dark palette, minimal chrome.
- Default view should be just VOICE + BGM waveforms; reveal controls on demand.
- Maintain keybindings: Space play/pause, Shift+I/Shift+O range, D delete, R punch-in, ? shortcuts, i info.
- Keep VOICE/BGM playheads and timeline scaling in sync.
- Avoid unnecessary numbers/labels; Japanese labels are preferred.

## Recording
- Use MediaRecorder with a supported mimeType.
- For long recordings, allow direct save without decode.
- Always preserve uploaded audio and reload safely.

## Server (src/clipod/web/server.py)
- /api/auto should serve the latest AUTO_FILE or requested file in the same directory.
- Always validate ranges and file paths.
- Keep ffmpeg calls explicit and logged on failure.

## Testing/Verification
- Prefer running existing scripts (test_workflow.sh) and python3 py_compile when available.
- If unavailable, document the limitation clearly.
