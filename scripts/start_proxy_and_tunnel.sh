#!/usr/bin/env bash
set -euo pipefail

# Repo awareness and config defaults
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_PATH="${CONFIG_PATH:-$REPO_ROOT/config/trapdoor.json}"

PORT_DEFAULT="$(
  python3 - "$CONFIG_PATH" <<'PY'
import json, sys
cfg = json.load(open(sys.argv[1]))
print(cfg["app"]["port"])
PY
)"

TOKEN_FILE_DEFAULT="$(
  python3 - "$CONFIG_PATH" <<'PY'
import json, sys
cfg = json.load(open(sys.argv[1]))
print(cfg["auth"]["token_file"])
PY
)"

KEYCHAIN_SERVICE_DEFAULT="$(
  python3 - "$CONFIG_PATH" <<'PY'
import json, sys
cfg = json.load(open(sys.argv[1]))
print(cfg["auth"]["keychain_service"])
PY
)"

KEYCHAIN_ACCOUNT_DEFAULT="$(
  python3 - "$CONFIG_PATH" <<'PY'
import json, sys
cfg = json.load(open(sys.argv[1]))
print(cfg["auth"]["keychain_account"])
PY
)"

SERVER_PATH_DEFAULT="$(
  python3 - "$CONFIG_PATH" <<'PY'
import json, sys
cfg = json.load(open(sys.argv[1]))
print(cfg["launch_agents"].get("server_path", "openai_compatible_server.py"))
PY
)"

PYTHON_PATH_DEFAULT="$(
  python3 - "$CONFIG_PATH" <<'PY'
import json, sys
cfg = json.load(open(sys.argv[1]))
print(cfg["launch_agents"].get("python_path", "python3"))
PY
)"

PROMPT_FALLBACK="You are Qwen 2.5 Coder 32B running locally behind an OpenAI-compatible proxy. When you need filesystem or command actions, propose explicit HTTP calls (method, path, JSON body) to /fs/* or /exec, and note that the caller must include Authorization: Bearer <token>."

DEFAULT_PROFILE="$(
  python3 - "$CONFIG_PATH" <<'PY'
import json, sys
cfg = json.load(open(sys.argv[1]))
print(cfg.get("models", {}).get("default_profile", "default"))
PY
)"

MODEL_PROFILE="${MODEL_PROFILE:-$DEFAULT_PROFILE}"
eval "$(python3 - "$CONFIG_PATH" "$MODEL_PROFILE" <<'PY'
import json, sys, shlex

cfg = json.load(open(sys.argv[1]))
profile = sys.argv[2]
profiles = cfg.get("models", {}).get("profiles", {})
if profile not in profiles:
    sys.stderr.write(f"[trapdoor] Unknown model profile '{profile}'\n")
    sys.exit(1)
data = profiles[profile]
model = data.get("name")
if not model:
    sys.stderr.write(f"[trapdoor] Profile '{profile}' missing 'name'\n")
    sys.exit(1)
prompt = data.get("system_prompt", "")
print(f"MODE_FROM_PROFILE={shlex.quote(model)}")
print(f"PROMPT_FROM_PROFILE={shlex.quote(prompt)}")
PY
)"

PROFILE_PROMPT="${PROMPT_FROM_PROFILE:-$PROMPT_FALLBACK}"

export MODEL_PROFILE

# Defaults (override with env)
PORT="${PORT:-$PORT_DEFAULT}"
BACKEND="${BACKEND:-ollama}"
MODEL="${MODEL:-$MODE_FROM_PROFILE}"
AUTH_TOKEN_FILE="${AUTH_TOKEN_FILE:-$TOKEN_FILE_DEFAULT}"
BASE_DIR="${BASE_DIR:-/}"
ALLOW_ABSOLUTE="${ALLOW_ABSOLUTE:-1}"
ALLOW_SUDO="${ALLOW_SUDO:-1}"
DEFAULT_SYSTEM_PROMPT="${DEFAULT_SYSTEM_PROMPT:-$PROFILE_PROMPT}"
AUTH_TOKEN_USE_KEYCHAIN="${AUTH_TOKEN_USE_KEYCHAIN:-1}"
AUTH_TOKEN_KEYCHAIN_SERVICE="${AUTH_TOKEN_KEYCHAIN_SERVICE:-$KEYCHAIN_SERVICE_DEFAULT}"
AUTH_TOKEN_KEYCHAIN_ACCOUNT="${AUTH_TOKEN_KEYCHAIN_ACCOUNT:-$KEYCHAIN_ACCOUNT_DEFAULT}"
SERVER_PATH="${SERVER_PATH:-$SERVER_PATH_DEFAULT}"
PYTHON_BIN="${PYTHON_BIN:-$PYTHON_PATH_DEFAULT}"

mkdir -p .proxy_runtime

# Ensure requested Ollama model is available before booting the proxy
ensure_ollama_model() {
  local log_dir=".proxy_runtime"
  mkdir -p "$log_dir"
  if ! command -v ollama >/dev/null 2>&1; then
    echo "ERROR: ollama CLI not found. Install it from https://ollama.ai/download" >&2
    exit 1
  fi
  if ! pgrep -x ollama >/dev/null 2>&1; then
    echo "==> Starting Ollama daemon..."
    nohup ollama serve > "$log_dir/ollama_nohup.log" 2>&1 & echo $! > "$log_dir/ollama.pid"
    for i in {1..60}; do
      if command -v curl >/dev/null 2>&1 && curl -sf http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
        break
      fi
      sleep 1
    done
  fi
  if ! ollama list | awk -v m="$MODEL" 'NR>1 && $1==m {found=1} END{exit !found}'; then
    echo "==> Pulling Ollama model $MODEL (this may take a while)..."
    if ! ollama pull "$MODEL" > "$log_dir/ollama_pull.log" 2>&1; then
      echo "ERROR: Failed to pull model $MODEL. See $log_dir/ollama_pull.log" >&2
      exit 1
    fi
  fi
  if ! ollama list | awk -v m="$MODEL" 'NR>1 && $1==m {found=1} END{exit !found}'; then
    echo "ERROR: Model $MODEL not available after pull. Check $log_dir/ollama_pull.log" >&2
    exit 1
  fi
}

# Ensure a token exists in AUTH_TOKEN_FILE
if [[ "$AUTH_TOKEN_USE_KEYCHAIN" == "1" && "$(uname -s)" == "Darwin" && -n "$AUTH_TOKEN_KEYCHAIN_SERVICE" ]]; then
  AUTH_TOKEN_FILE="$AUTH_TOKEN_FILE" AUTH_TOKEN_KEYCHAIN_SERVICE="$AUTH_TOKEN_KEYCHAIN_SERVICE" AUTH_TOKEN_KEYCHAIN_ACCOUNT="$AUTH_TOKEN_KEYCHAIN_ACCOUNT" "$SCRIPT_DIR/manage_auth_token.sh" ensure-file >/dev/null
else
  if [[ ! -f "$AUTH_TOKEN_FILE" ]]; then
    python3 - <<'PY' > token.tmp
import secrets
print(secrets.token_hex(16))
PY
    mv token.tmp "$AUTH_TOKEN_FILE"
  fi
fi
chmod 600 "$AUTH_TOKEN_FILE" 2>/dev/null || true

echo "==> Using AUTH_TOKEN_FILE at $AUTH_TOKEN_FILE"
if [[ "$BACKEND" == "ollama" ]]; then
  ensure_ollama_model
fi

echo "==> Starting server: BACKEND=$BACKEND MODEL=$MODEL (profile: $MODEL_PROFILE)"
echo "    Using Python: $PYTHON_BIN"
echo "    Server path: $SERVER_PATH"
export BACKEND MODEL PORT MODEL_PROFILE AUTH_TOKEN_FILE BASE_DIR ALLOW_ABSOLUTE ALLOW_SUDO DEFAULT_SYSTEM_PROMPT

# Kill prior server
kill $(cat server.pid 2>/dev/null) 2>/dev/null || true
if [[ ! -f "$SERVER_PATH" ]]; then
  echo "ERROR: Server script not found at $SERVER_PATH" >&2
  exit 1
fi
nohup "$PYTHON_BIN" "$SERVER_PATH" > .proxy_runtime/server_nohup.log 2>&1 & echo $! > server.pid

for i in {1..60}; do
  if curl -sf "http://127.0.0.1:$PORT/health" >/dev/null; then
    echo "==> Server healthy on :$PORT"; break
  fi
  sleep 1
done

# Prefer ngrok if available and account active; else use cloudflared
start_ngrok() {
  echo "==> Starting ngrok tunnel..." >&2
  nohup ngrok http "$PORT" > .proxy_runtime/ngrok_nohup.log 2>&1 & echo $! > ngrok.pid
  for i in {1..30}; do
    if curl -sf http://127.0.0.1:4040/api/tunnels >/dev/null; then
      URL=$(curl -sf http://127.0.0.1:4040/api/tunnels | python3 -c 'import sys,json;d=json.load(sys.stdin);print([t["public_url"] for t in d.get("tunnels",[]) if t.get("proto")=="https"][0])' 2>/dev/null || true)
      if [[ -n "$URL" ]]; then echo "$URL"; return 0; fi
    fi
    sleep 1
  done
  return 1
}

start_cloudflared() {
  echo "==> Starting cloudflared tunnel..." >&2
  nohup cloudflared tunnel --url "http://127.0.0.1:$PORT" --no-autoupdate > .proxy_runtime/cloudflared_nohup.log 2>&1 & echo $! > cloudflared.pid
  sleep 2
  for i in {1..30}; do
    URL=$(grep -Eo 'https://[-a-z0-9]+\.trycloudflare\.com' .proxy_runtime/cloudflared_nohup.log | tail -n1 || true)
    if [[ -n "$URL" ]]; then echo "$URL"; return 0; fi
    sleep 1
  done
  return 1
}

URL=""
if command -v ngrok >/dev/null 2>&1; then
  URL=$(start_ngrok || true)
fi
if [[ -z "$URL" ]]; then
  if ! command -v cloudflared >/dev/null 2>&1; then
    echo "Installing cloudflared..."; brew install cloudflared >/dev/null
  fi
  URL=$(start_cloudflared || true)
fi

if [[ -z "$URL" ]]; then
  echo "ERROR: Could not establish a public tunnel. Check .proxy_runtime logs."
  exit 1
fi

echo "==> Public URL: $URL"
echo "$URL" > .proxy_runtime/public_url.txt
# Verify health via public URL
code="$(curl -s -o /dev/null -w "%{http_code}" "$URL/health" || true)"
if [[ "$code" != "200" ]]; then
  for i in {1..5}; do
    sleep 1
    code="$(curl -s -o /dev/null -w "%{http_code}" "$URL/health" || true)"
    [[ "$code" == "200" ]] && break
  done
fi
echo "==> Health via tunnel: $code"

PUBLIC_URL="$URL" python3 - <<'PY'
import json, os, time, pathlib

session = {
    "started_at": time.time(),
    "profile": os.environ.get("MODEL_PROFILE"),
    "backend": os.environ.get("BACKEND"),
    "model": os.environ.get("MODEL"),
    "port": os.environ.get("PORT"),
    "system_prompt": os.environ.get("DEFAULT_SYSTEM_PROMPT"),
    "public_url": os.environ.get("PUBLIC_URL"),
    "auth_token_file": os.environ.get("AUTH_TOKEN_FILE"),
}
path = pathlib.Path(".proxy_runtime/session.json")
path.write_text(json.dumps(session, indent=2), encoding="utf-8")
PY

echo "==> Done. Share this with the sandbox: $URL"
echo "==> FS/exec token is in $AUTH_TOKEN_FILE"
