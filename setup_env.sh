#!/usr/bin/env bash
set -euo pipefail

# Always run from the script's directory
cd "$(dirname "$0")"

VENV_DIR=".seoaudmach"

# Pick a Python executable
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "❌ Python not found. Install Python 3.10+ first."
  exit 1
fi

# Create venv if it doesn't exist (or is incomplete)
if [[ ! -d "$VENV_DIR" || ! -x "$VENV_DIR/bin/python" ]]; then
  echo "🔧 Creating virtual environment in '$VENV_DIR'..."
  "$PY" -m venv "$VENV_DIR"
fi

# Use venv's Python/pip for installs
"$VENV_DIR/bin/python" -m pip install --upgrade pip wheel
"$VENV_DIR/bin/python" -m pip install -U -r requirements.txt

echo
echo "🎉 Done."
echo "👉 To activate later: source $VENV_DIR/bin/activate"
