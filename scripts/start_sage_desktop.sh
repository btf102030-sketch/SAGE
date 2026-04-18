#!/usr/bin/env bash
# ═══════════════════════════════════════════════════
# SAGE.ai — Start Desktop App
# ═══════════════════════════════════════════════════
# Launches the Electron desktop application.
# Run from ~/sage/ or adjust SAGE_DIR below.

set -e

SAGE_DIR="${SAGE_DIR:-$HOME/sage}"
cd "$SAGE_DIR/electron"

# Install deps if needed
if [ ! -d "node_modules" ]; then
    echo "[SAGE] Installing Electron dependencies..."
    npm install
fi

echo "[SAGE] Launching SAGE.ai Desktop..."
npm start
