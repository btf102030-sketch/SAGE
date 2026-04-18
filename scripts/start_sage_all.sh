#!/usr/bin/env bash
# ═══════════════════════════════════════════════════
# SAGE.ai — One-Click Startup (API + Desktop)
# ═══════════════════════════════════════════════════
# Starts the FastAPI backend in the background, waits
# for it to be ready, then launches the Electron app.

set -e

SAGE_DIR="${SAGE_DIR:-$HOME/sage}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "══════════════════════════════════════"
echo "    SAGE.ai — System Startup"
echo "══════════════════════════════════════"

# ── 1. Start Ollama if needed ──
if ! pgrep -f "ollama" > /dev/null 2>&1; then
    echo "[1/3] Starting Ollama..."
    ollama serve &
    sleep 3
else
    echo "[1/3] Ollama already running."
fi

# ── 2. Start API in background ──
echo "[2/3] Starting SAGE API..."
cd "$SAGE_DIR"

if [ -f "sage_venv/bin/activate" ]; then
    source sage_venv/bin/activate
fi

python3 sage_api.py &
API_PID=$!
echo "       API PID: $API_PID"

# Wait for API to be ready
echo "       Waiting for API to come online..."
for i in $(seq 1 30); do
    if curl -s http://localhost:5000/status > /dev/null 2>&1; then
        echo "       API is ready!"
        break
    fi
    sleep 1
done

# ── 3. Start Electron ──
echo "[3/3] Launching SAGE Desktop..."
cd "$SAGE_DIR/electron"

if [ ! -d "node_modules" ]; then
    npm install
fi

npm start

# Cleanup when Electron closes
echo "[SAGE] Desktop closed. Stopping API (PID $API_PID)..."
kill $API_PID 2>/dev/null
echo "[SAGE] Goodbye."
