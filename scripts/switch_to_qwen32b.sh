#!/usr/bin/env bash
set -euo pipefail

MODEL="qwen2.5-coder:32b"
LOG_DIR=".proxy_runtime"
mkdir -p "$LOG_DIR"

PULL_LOG="$LOG_DIR/ollama_pull_qwen32b.log"
echo "==> Ensuring Ollama daemon is running..."
if ! pgrep -x ollama >/dev/null 2>&1; then
  nohup ollama serve > "$LOG_DIR/ollama_nohup.log" 2>&1 & echo $! > "$LOG_DIR/ollama.pid"
  for i in {1..60}; do
    curl -sf http://127.0.0.1:11434/api/tags >/dev/null && break || true
    sleep 1
  done
fi

if ollama list | grep -q "$MODEL"; then
  echo "==> $MODEL already present."
else
  echo "==> Pulling $MODEL (this may take a while)..."
  nohup ollama pull "$MODEL" > "$PULL_LOG" 2>&1 & echo $! > "$LOG_DIR/ollama_pull.pid"
fi

echo "==> Waiting for $MODEL to be available..."
for i in {1..720}; do
  if ollama list | grep -q "$MODEL"; then
    echo "==> $MODEL is ready. Restarting server with MODEL=$MODEL"
    break
  fi
  sleep 10
done

if ! ollama list | grep -q "$MODEL"; then
  echo "ERROR: Timed out waiting for $MODEL. Check $PULL_LOG"
  exit 1
fi

# Restart server with new model
PORT=${PORT:-8000}
kill $(cat server.pid 2>/dev/null) 2>/dev/null || true
export BACKEND=ollama
export MODEL="$MODEL"
nohup python3 openai_compatible_server.py > server_nohup.log 2>&1 & echo $! > server.pid

echo "==> Waiting for health on localhost:$PORT"
for i in {1..60}; do
  if curl -sf "http://127.0.0.1:$PORT/health" | grep -q '"backend": "ollama"'; then
    echo "==> Server now running with $MODEL"
    curl -s "http://127.0.0.1:$PORT/health"
    exit 0
  fi
  sleep 1
done

echo "ERROR: Server did not come up with $MODEL. See server_nohup.log"
exit 1

