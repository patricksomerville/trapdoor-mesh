#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_PATH="${CONFIG_PATH:-$REPO_ROOT/config/trapdoor.json}"

SERVICE="${AUTH_TOKEN_KEYCHAIN_SERVICE:-$(
  python3 - "$CONFIG_PATH" <<'PY'
import json, sys, pathlib
cfg = json.load(open(sys.argv[1]))
print(cfg["auth"]["keychain_service"])
PY
)}"

ACCOUNT="${AUTH_TOKEN_KEYCHAIN_ACCOUNT:-$(
  python3 - "$CONFIG_PATH" <<'PY'
import json, sys, pathlib
cfg = json.load(open(sys.argv[1]))
print(cfg["auth"]["keychain_account"])
PY
)}"

TOKEN_FILE="${AUTH_TOKEN_FILE:-$(
  python3 - "$CONFIG_PATH" <<'PY'
import json, sys, pathlib
cfg = json.load(open(sys.argv[1]))
print(cfg["auth"]["token_file"])
PY
)}"

generate_token() {
  python3 - <<'PY'
import secrets
print(secrets.token_hex(16))
PY
}

ensure_security() {
  if ! command -v security >/dev/null 2>&1; then
    echo "The macOS 'security' CLI is required for keychain operations." >&2
    exit 1
  fi
}

write_file() {
  local token="$1"
  mkdir -p "$(dirname "$TOKEN_FILE")"
  printf '%s\n' "$token" > "$TOKEN_FILE"
  chmod 600 "$TOKEN_FILE"
}

ensure_entry() {
  ensure_security
  local token
  if token=$(security find-generic-password -s "$SERVICE" -a "$ACCOUNT" -w 2>/dev/null); then
    write_file "$token"
    return 0
  fi
  token=$(generate_token)
  security add-generic-password -U -s "$SERVICE" -a "$ACCOUNT" -w "$token" >/dev/null
  write_file "$token"
  echo "Created new keychain item '$SERVICE' (account '$ACCOUNT')."
}

rotate_entry() {
  ensure_security
  local token
  token=$(generate_token)
  security add-generic-password -U -s "$SERVICE" -a "$ACCOUNT" -w "$token" >/dev/null
  write_file "$token"
  echo "Rotated keychain item '$SERVICE'."
}

print_entry() {
  ensure_security
  security find-generic-password -s "$SERVICE" -a "$ACCOUNT" -w
}

delete_entry() {
  ensure_security
  security delete-generic-password -s "$SERVICE" -a "$ACCOUNT" >/dev/null || true
  rm -f "$TOKEN_FILE"
  echo "Deleted keychain item '$SERVICE' and removed $TOKEN_FILE (if present)."
}

require_subcommand() {
  cat <<'USAGE'
Usage: scripts/manage_auth_token.sh <command>

Commands:
  ensure-file   Ensure keychain entry exists and sync it to the AUTH_TOKEN_FILE.
  rotate        Generate and store a new token, updating the keychain and file.
  print         Print the current token to stdout.
  delete        Remove the keychain entry and delete the token file.
USAGE
  exit 1
}

cmd="${1:-}"
case "$cmd" in
  ensure-file) ensure_entry ;;
  rotate) rotate_entry ;;
  print) print_entry ;;
  delete) delete_entry ;;
  *) require_subcommand ;;
esac
