#!/usr/bin/env bash
set -euo pipefail

# Generates a reusable "Access Pack" for any external agent.
# Usage: ./scripts/generate_access_pack.sh [PARTNER_NAME] [BASE_URL] [TOKEN_FILE]
# Defaults: PARTNER_NAME=partner BASE_URL from named tunnel, TOKEN_FILE=./auth_token.txt

PARTNER=${1:-partner}
BASE_URL=${2:-}
TOKEN_FILE=${3:-$(pwd)/auth_token.txt}

if [[ -z "$BASE_URL" ]]; then
  # Try to use the stable hostname if present in cloudflared config
  if grep -Eq 'hostname:\s*([a-zA-Z0-9.-]+)' "$HOME/.cloudflared/config.yml" 2>/dev/null; then
    HOST=$(grep -Eo 'hostname:\s*([a-zA-Z0-9.-]+)' "$HOME/.cloudflared/config.yml" | head -n1 | awk '{print $2}')
    BASE_URL="https://$HOST"
  else
    echo "Provide BASE_URL explicitly, e.g. https://trapdoor.treehouse.tech" >&2
    exit 1
  fi
fi

if [[ ! -f "$TOKEN_FILE" ]]; then
  echo "Token file not found at $TOKEN_FILE" >&2
  exit 1
fi

TOKEN=$(tr -d '\n' < "$TOKEN_FILE")
OUT_DIR=.proxy_runtime/packs
mkdir -p "$OUT_DIR"

TXT="$OUT_DIR/${PARTNER}_access_pack.txt"
JSON="$OUT_DIR/${PARTNER}_access_pack.json"

cat > "$TXT" <<TXT
Below is your connection context and the credentials/endpoints you should use to work on my machine safely.

Context
- You are an external, sandboxed AI agent connecting to my local LLM proxy.
- Chat is OpenAI-compatible; filesystem and terminal access are token-protected.
- Propose explicit HTTP calls for tools and include the Authorization header shown below.

Service URL
- Base: ${BASE_URL}
- Health: GET ${BASE_URL}/health
- Current model: qwen2.5-coder:32b (local via Ollama)

Auth
- Tools token: ${TOKEN}
- Header for tools: Authorization: Bearer ${TOKEN}

Chat API (OpenAI-compatible)
- POST /v1/chat/completions
- Example: {"model":"qwen2.5-coder:32b","messages":[{"role":"user","content":"Say ready."}]}
- For streaming: add "stream": true (SSE)

Tooling API (Filesystem + Exec)
- GET /fs/ls?path=/
- GET /fs/read?path=/etc/hosts
- POST /fs/write  {"path":"/tmp/file.txt","content":"hello","mode":"write"}
- POST /fs/mkdir  {"path":"/tmp/newdir","parents":true,"exist_ok":true}
- POST /fs/rm     {"path":"/tmp/file.txt","recursive":false}
- POST /exec      {"cmd":["uname","-a"],"cwd":"/","timeout":300,"sudo":false}

Recommended system prompt
- You are Qwen 2.5 Coder 32B running locally behind an OpenAI-compatible proxy. When you need filesystem or command actions, propose explicit HTTP calls (method, path, JSON body) to /fs/* or /exec, and note that the caller must include Authorization: Bearer <token>.

Quick checks
- curl -s ${BASE_URL}/health
- curl -s -X POST ${BASE_URL}/v1/chat/completions -H 'Content-Type: application/json' -d '{"model":"qwen2.5-coder:32b","messages":[{"role":"user","content":"Say ready."}]}'
- TOKEN=${TOKEN}; curl -s -H "Authorization: Bearer $TOKEN" "${BASE_URL}/fs/ls?path=/"
TXT

cat > "$JSON" <<JSON
{
  "version": 1,
  "base_url": "${BASE_URL}",
  "auth": {
    "scheme": "Bearer",
    "token": "${TOKEN}",
    "applies_to": ["/fs/*", "/exec"]
  },
  "apis": {
    "chat": {"path": "/v1/chat/completions", "openai_compatible": true},
    "fs": {"base": "/fs", "endpoints": ["ls", "read", "write", "mkdir", "rm"]},
    "exec": {"path": "/exec"}
  },
  "instructions": "Use the system prompt to request explicit HTTP calls for file/exec."
}
JSON

echo "Wrote $TXT and $JSON"

