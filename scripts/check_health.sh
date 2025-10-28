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

PUBLIC_URL_DEFAULT="$(cat "$REPO_ROOT/.proxy_runtime/public_url.txt" 2>/dev/null || true)"
PUBLIC_URL="${PUBLIC_URL:-$PUBLIC_URL_DEFAULT}"

# Ensure token file is present and synced
if command -v security >/dev/null 2>&1; then
  AUTH_TOKEN_FILE="$TOKEN_FILE" "$REPO_ROOT/scripts/manage_auth_token.sh" ensure-file >/dev/null
elif [[ ! -f "$TOKEN_FILE" ]]; then
  python3 - <<'PY' > "$TOKEN_FILE"
import secrets; print(secrets.token_hex(16))
PY
  chmod 600 "$TOKEN_FILE"
fi

TOKEN="$(head -n1 "$TOKEN_FILE" | tr -d '[:space:]')"

echo "==> Checking local health on port $PORT"
curl -sf "http://127.0.0.1:$PORT/health" | python3 -c 'import json,sys;print(json.dumps(json.load(sys.stdin), indent=2))'

echo "==> Validating chat completion"
curl -sf -X POST \
  -H "Content-Type: application/json" \
  "http://127.0.0.1:$PORT/v1/chat/completions" \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"Say health-check\"}]}" \
  | python3 -c 'import json,sys; data=json.load(sys.stdin); print(data["choices"][0]["message"]["content"])'

echo "==> Validating /fs/ls"
curl -sf \
  -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:$PORT/fs/ls?path=/" \
  | python3 -c 'import json,sys; data=json.load(sys.stdin); print(f"Entries: {len(data.get(\"entries\", []))}")'

echo "==> Validating /exec"
curl -sf -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "http://127.0.0.1:$PORT/exec" \
  -d '{"cmd":["echo","health-check"],"cwd":"/","timeout":5,"sudo":false}' \
  | python3 -c 'import json,sys; data=json.load(sys.stdin); print(f"RC={data.get(\"rc\")}, STDOUT={data.get(\"stdout\", \"\").strip()}")'

if [[ -n "$PUBLIC_URL" ]]; then
  echo "==> Checking public URL: $PUBLIC_URL/health"
  curl -sf "$PUBLIC_URL/health" | python3 -c 'import json,sys;print(json.dumps(json.load(sys.stdin), indent=2))'
else
  echo "==> Skipping public URL check (no PUBLIC_URL provided or recorded)."
fi

echo "==> Health checks completed."
