#!/usr/bin/env bash
set -euo pipefail

# Purpose: Create a Named Cloudflare Tunnel to a local FastAPI proxy on :8000
# Result: Stable HTTPS at your chosen hostname (e.g., llm.your-domain.com)

TUN_NAME=${TUN_NAME:-genspark-llm-proxy}
HOSTNAME=${HOSTNAME:-}
PORT=${PORT:-8000}

if [[ -z "${HOSTNAME}" ]]; then
  echo "Enter the hostname you want to use (e.g., llm.your-domain.com):"
  read -r HOSTNAME
fi

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "Installing cloudflared via Homebrew..."
  brew install cloudflared >/dev/null
fi

echo "==> Cloudflare login (opens a browser)"
cloudflared tunnel login

echo "==> Creating (or reusing) named tunnel: ${TUN_NAME}"
if ! cloudflared tunnel list | awk 'NR>1{print $1,$2}' | grep -q " ${TUN_NAME}$"; then
  cloudflared tunnel create "${TUN_NAME}"
fi

TUNNEL_ID=$(cloudflared tunnel list | awk -v n="${TUN_NAME}" 'NR>1 && $2==n {print $1; exit}')
if [[ -z "${TUNNEL_ID}" ]]; then
  echo "ERROR: Could not determine tunnel ID for ${TUN_NAME}" >&2
  exit 1
fi

echo "==> Routing DNS ${HOSTNAME} -> tunnel ${TUN_NAME}"
cloudflared tunnel route dns "${TUN_NAME}" "${HOSTNAME}"

# Write config (Homebrew path on macOS; adjust on Linux as needed)
CFG_DIR=/opt/homebrew/etc/cloudflared
mkdir -p "$CFG_DIR"
CFG_FILE="$CFG_DIR/config.yml"
CREDS_FILE="$HOME/.cloudflared/${TUNNEL_ID}.json"

cat > "$CFG_FILE" <<YAML
tunnel: ${TUNNEL_ID}
credentials-file: ${CREDS_FILE}
ingress:
  - hostname: ${HOSTNAME}
    service: http://127.0.0.1:${PORT}
  - service: http_status:404
YAML

echo "==> Starting cloudflared as a service (uses ${CFG_FILE})"
brew services restart cloudflared >/dev/null || brew services start cloudflared >/dev/null

echo "==> Verifying ${HOSTNAME}"
for i in {1..30}; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "https://${HOSTNAME}/health" || true)
  if [[ "$code" == "200" ]]; then
    echo "Success: https://${HOSTNAME} is reachable (200)"
    exit 0
  fi
  sleep 2
done

echo "Note: DNS may take a moment to propagate. Try: curl -i https://${HOSTNAME}/health"
exit 0

