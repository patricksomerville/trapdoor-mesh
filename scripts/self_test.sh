#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_PATH="${CONFIG_PATH:-$REPO_ROOT/config/trapdoor.json}"

PORT="$(
  python3 - "$CONFIG_PATH" <<'PY'
import json, sys
cfg = json.load(open(sys.argv[1]))
print(cfg["app"]["port"])
PY
)"

MODEL="$(
  python3 - "$CONFIG_PATH" <<'PY'
import json, sys
cfg = json.load(open(sys.argv[1]))
print(cfg["app"]["model"])
PY
)"

TOKEN_FILE="$(
  python3 - "$CONFIG_PATH" <<'PY'
import json, sys
cfg = json.load(open(sys.argv[1]))
print(cfg["auth"]["token_file"])
PY
)"

ensure_token() {
  if command -v security >/dev/null 2>&1; then
    AUTH_TOKEN_FILE="$TOKEN_FILE" "$REPO_ROOT/scripts/manage_auth_token.sh" ensure-file >/dev/null
  elif [[ ! -f "$TOKEN_FILE" ]]; then
    python3 - <<'PY' > "$TOKEN_FILE"
import secrets; print(secrets.token_hex(16))
PY
    chmod 600 "$TOKEN_FILE"
  fi
}

require_command() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required command: $cmd" >&2
    exit 1
  fi
}

ensure_token
require_command curl

TOKEN="$(head -n1 "$TOKEN_FILE" | tr -d '[:space:]')"
BASE_URL="http://127.0.0.1:$PORT"
CHAT_PAYLOAD_FILE="$(mktemp)"
trap 'rm -f "$CHAT_PAYLOAD_FILE"' EXIT

cat <<JSON >"$CHAT_PAYLOAD_FILE"
{"model":"$MODEL","messages":[{"role":"user","content":"Say ready."}]}
JSON

retry_health() {
  local attempt=1
  while (( attempt <= 5 )); do
    if HEALTH_JSON=$(curl -sf "$BASE_URL/health"); then
      echo "$HEALTH_JSON"
      return 0
    fi
    sleep 1
    ((attempt++))
  done
  echo "Health check failed after 5 attempts." >&2
  return 1
}

retry_chat() {
  local attempt=1
  while (( attempt <= 5 )); do
    if CHAT_RESPONSE=$(curl -sf -X POST \
      -H "Content-Type: application/json" \
      --data-binary "@$CHAT_PAYLOAD_FILE" \
      "$BASE_URL/v1/chat/completions"); then
      echo "$CHAT_RESPONSE"
      return 0
    fi
    sleep 1
    ((attempt++))
  done
  echo "Chat endpoint failed after 5 attempts." >&2
  return 1
}

echo "==> Checking local health at $BASE_URL/health"
HEALTH_JSON="$(retry_health)" || exit 1
echo "Health response: $HEALTH_JSON"

echo "==> Verifying chat completion"
CHAT_RESPONSE="$(retry_chat)" || exit 1
READY_TEXT="$(python3 -c 'import json, sys; data=json.loads(sys.argv[1]); print(data["choices"][0]["message"]["content"])' "$CHAT_RESPONSE")"
echo "Chat replied with: $READY_TEXT"

if ! echo "$READY_TEXT" | grep -qi "ready"; then
  echo "Chat response did not contain the word 'ready'." >&2
  exit 1
fi

echo "==> Testing /fs/ls with auth token"
FS_RESPONSE="$(curl -sf \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/fs/ls?path=/")" || {
  echo "FS listing failed. Check token permissions." >&2
  exit 1
}
ENTRY_COUNT="$(python3 -c 'import json, sys; data=json.loads(sys.argv[1]); print(len(data.get("entries", [])))' "$FS_RESPONSE")"
echo "Filesystem entries at root: $ENTRY_COUNT"

echo "==> Testing /exec command"
EXEC_PAYLOAD='{"cmd":["echo","self-test"],"cwd":"/","timeout":5,"sudo":false}'
EXEC_RESPONSE="$(curl -sf -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "$BASE_URL/exec" \
  -d "$EXEC_PAYLOAD")" || {
  echo "Exec command failed." >&2
  exit 1
}
STATUS="$(python3 -c 'import json, sys; data=json.loads(sys.argv[1]); print(data["rc"], data["stdout"].strip())' "$EXEC_RESPONSE")"
echo "Exec result: $STATUS"

echo "✅ Trapdoor self-test completed successfully."
