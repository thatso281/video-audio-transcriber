#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 was not found."
    exit 1
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "FFmpeg was not found in PATH. Install FFmpeg first."
    exit 1
fi

if ! command -v ffprobe >/dev/null 2>&1; then
    echo "ffprobe was not found in PATH. Install a complete FFmpeg package."
    exit 1
fi

if [[ ! -d ".venv" ]]; then
    python3 -m venv .venv
fi

.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

echo
echo "Installation completed."
echo "Run ./run_linux_mac.sh to open the application."
