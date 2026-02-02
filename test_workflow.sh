#!/usr/bin/env bash
set -euo pipefail

log_step() {
  echo "==> $1"
}

run_step() {
  local label="$1"
  shift
  if "$@"; then
    echo "[OK] $label"
  else
    echo "[FAIL] $label"
    return 1
  fi
}

log_step "Recording test audio..."
run_step "clipod record" clipod record --duration 5 --output test_recording.wav

log_step "Open the web editor and save BGM layout if needed."
echo "Manual step: clipod web test_recording.wav"

log_step "Processing audio..."
run_step "clipod process" clipod process test_recording.wav processed.wav

log_step "Exporting final MP3..."
run_step "clipod export" clipod export processed.wav -o final.mp3

log_step "Workflow complete."
