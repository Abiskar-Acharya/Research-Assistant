#!/usr/bin/env bash
set -euo pipefail

MODEL="glm-4.7-flash"
OLLAMA_URL="http://localhost:11434"

echo "============================================"
echo "  ArXivMind - Startup Script"
echo "============================================"
echo ""

# -------------------------------------------
# 1. Check if Ollama is installed
# -------------------------------------------
if ! which ollama > /dev/null 2>&1; then
  echo "[ERROR] Ollama is not installed."
  echo ""
  echo "Install Ollama:"
  echo "  macOS:  brew install ollama"
  echo "  Linux:  curl -fsSL https://ollama.com/install.sh | sh"
  echo "  Visit:  https://ollama.com/download"
  echo ""
  exit 1
fi
echo "[OK] Ollama is installed."

# -------------------------------------------
# 2. Check if Ollama is running, start if not
# -------------------------------------------
if ! curl -sf "${OLLAMA_URL}/api/tags" > /dev/null 2>&1; then
  echo "[INFO] Ollama is not running. Starting it..."
  ollama serve &
  OLLAMA_PID=$!

  # Wait with exponential backoff (up to ~15s)
  WAIT=1
  TOTAL=0
  MAX_WAIT=15
  while [ "$TOTAL" -lt "$MAX_WAIT" ]; do
    if curl -sf "${OLLAMA_URL}/api/tags" > /dev/null 2>&1; then
      break
    fi
    echo "[INFO] Waiting for Ollama to start... (${TOTAL}s)"
    sleep "$WAIT"
    TOTAL=$((TOTAL + WAIT))
    WAIT=$((WAIT * 2))
    if [ "$WAIT" -gt 4 ]; then
      WAIT=4
    fi
  done

  if ! curl -sf "${OLLAMA_URL}/api/tags" > /dev/null 2>&1; then
    echo "[ERROR] Ollama failed to start within ${MAX_WAIT}s."
    exit 1
  fi
fi
echo "[OK] Ollama is running."

# -------------------------------------------
# 3. Check if model is pulled, pull if not
# -------------------------------------------
if ! ollama list | grep -q "${MODEL}"; then
  echo "[INFO] Model '${MODEL}' not found. Pulling..."
  ollama pull "${MODEL}"
else
  echo "[OK] Model '${MODEL}' is available."
fi

# -------------------------------------------
# 4. Start Docker Compose
# -------------------------------------------
echo ""
echo "[INFO] Starting Docker Compose services..."
docker compose up -d --build

echo ""
echo "============================================"
echo "  ArXivMind is running!"
echo "============================================"
echo ""
echo "  Frontend:  http://localhost:3000"
echo "  API:       http://localhost:8000"
echo "  API Docs:  http://localhost:8000/docs"
echo ""
echo "  Stop with: docker compose down"
echo "============================================"
