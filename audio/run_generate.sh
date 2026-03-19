#!/usr/bin/env bash
# Run generate_audio.py in the foreground, logging output.
# Ctrl-C or SIGTERM kills the python process automatically.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$SCRIPT_DIR/generate_audio.log"

# Forward all arguments to generate_audio.py
exec python3 "$SCRIPT_DIR/generate_audio.py" "$@" 2>&1 | tee "$LOG"
