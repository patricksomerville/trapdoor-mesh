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

LOG_DIR="$(
  python3 - "$CONFIG_PATH" <<'PY'
import json, sys
cfg = json.load(open(sys.argv[1]))
print(cfg["launch_agents"]["log_dir"])
PY
)"

TUNNEL_ID="$(
  python3 - "$CONFIG_PATH" <<'PY'
import json, sys
cfg = json.load(open(sys.argv[1]))
print(cfg["cloudflare"]["tunnel_id"])
PY
)"

HOSTNAME="$(
  python3 - "$CONFIG_PATH" <<'PY'
import json, sys
cfg = json.load(open(sys.argv[1]))
print(cfg["cloudflare"]["hostname"])
PY
)"

TOKEN_FILE="$(
  python3 - "$CONFIG_PATH" <<'PY'
import json, sys
cfg = json.load(open(sys.argv[1]))
print(cfg["auth"]["token_file"])
PY
)"

LOCALPROXY_LABEL="$(
  python3 - "$CONFIG_PATH" <<'PY'
import json, sys
cfg = json.load(open(sys.argv[1]))
print(cfg["launch_agents"]["localproxy_label"])
PY
)"

CLOUDFLARE_LABEL="$(
  python3 - "$CONFIG_PATH" <<'PY'
import json, sys
cfg = json.load(open(sys.argv[1]))
print(cfg["launch_agents"]["cloudflared_label"])
PY
)"

CFG_DIR="$(
  python3 - "$CONFIG_PATH" <<'PY'
import json, sys
cfg = json.load(open(sys.argv[1]))
print(cfg["cloudflare"]["config_dir"])
PY
)"

USER_HOME="$HOME"
LAUNCH_DIR="$USER_HOME/Library/LaunchAgents"
CFG_FILE="$CFG_DIR/config.yml"

mkdir -p "$LAUNCH_DIR" "$LOG_DIR" "$CFG_DIR"

# Render config files from templates
python3 "$REPO_ROOT/scripts/render_configs.py" --config "$CONFIG_PATH"

# Ensure token exists (prefer keychain if available)
if command -v security >/dev/null 2>&1; then
  AUTH_TOKEN_FILE="$TOKEN_FILE" "$REPO_ROOT/scripts/manage_auth_token.sh" ensure-file >/dev/null
else
  if [[ ! -f "$TOKEN_FILE" ]]; then
    python3 - <<'PY' > "$TOKEN_FILE"
import secrets; print(secrets.token_hex(16))
PY
    chmod 600 "$TOKEN_FILE"
  fi
fi

# Copy launchd plists
cp -f "$REPO_ROOT/plists/com.trapdoor.localproxy.plist" "$LAUNCH_DIR/"
cp -f "$REPO_ROOT/plists/com.trapdoor.cloudflared.plist" "$LAUNCH_DIR/"
cp -f "$REPO_ROOT/config/cloudflared.config.yml" "$CFG_FILE"

# Load launch agents
USER_ID=$(id -u)
for LABEL in "$LOCALPROXY_LABEL" "$CLOUDFLARE_LABEL"; do
  PLIST="$LAUNCH_DIR/$LABEL.plist"
  launchctl bootout gui/$USER_ID "$PLIST" >/dev/null 2>&1 || true
  launchctl bootstrap gui/$USER_ID "$PLIST"
  launchctl enable gui/$USER_ID/$LABEL
  launchctl kickstart -k gui/$USER_ID/$LABEL
done

echo "Installed and started launch agents. View logs in $LOG_DIR"
echo "Proxy health: http://127.0.0.1:$PORT/health"
echo "Public health (after DNS/tunnel active): https://$HOSTNAME/health"
