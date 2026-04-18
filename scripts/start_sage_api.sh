#!/usr/bin/env bash
# ═══════════════════════════════════════════════════
# SAGE.ai — Start API Backend
# ═══════════════════════════════════════════════════
# Launches the FastAPI server on port 5000.
# Run from ~/sage/ or adjust SAGE_DIR below.

set -e

SAGE_DIR="${SAGE_DIR:-$HOME/sage}"
cd "$SAGE_DIR"

# Activate virtualenv if it exists
if [ -f "sage_venv/bin/activate" ]; then
    source sage_venv/bin/activate
    echo "[SAGE] Virtual environment activated."
fi

# Ensure Ollama is running
if ! pgrep -f "ollama" > /dev/null 2>&1; then
    echo "[SAGE] Starting Ollama..."
    ollama serve &
    sleep 3
fi

echo "[SAGE] Starting SAGE.ai API on port 5000..."
python3 sage_api.py
