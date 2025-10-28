# Repository Guidelines

## Project Structure & Module Organization
- Root holds the hand-off collateral; `ACCESS_PACK.txt` / `.json` show the expected partner-facing instructions.
- `scripts/` bundles Bash automation for the FastAPI proxy, cloud tunnel setup, and launch-agent lifecycle; review each script header before editing.
- `plists/` contains `launchd` definitions for the proxy (`com.trapdoor.localproxy`) and Cloudflare tunnel; runtime artifacts land in `.proxy_runtime/` and stay untracked.
- `config/` keeps `trapdoor.json` (single source for ports, tokens, and model profiles) plus rendered Cloudflare config; regenerate with `python3 scripts/render_configs.py`. Templates live in `templates/`.
- `memory/` captures event logs in `events.jsonl` and long-lived lessons in `lessons.jsonl`; control these with `TRAPDOOR_MEMORY_DIR` if you relocate storage.

## Build, Test, and Development Commands
- `python3 control_panel.py` opens a guided menu for non-technical operators to start/stop the proxy, rotate tokens, run health checks, and copy connection details.
- Menu option 8 surfaces recent memory events; option 9 records a new lesson (tagged note) for future sessions.
- Menu option 6 triggers the automated self-test before you hand access to an external agent.
- Lessons in `memory/lessons.jsonl` are automatically surfaced in the system prompt for each new chat request, and Trapdoor writes a short “auto lesson” after every exchange.
- `MODEL_PROFILE=tools bash scripts/start_proxy_and_tunnel.sh` starts the proxy, generates `auth_token.txt` if missing, and negotiates an ngrok or Cloudflare tunnel; override settings with env vars such as `PORT=8080` or `MODEL=my-model:latest`.
- `bash scripts/generate_access_pack.sh partner https://trapdoor.treehouse.tech ~/Desktop/auth_token.txt` refreshes the distributable pack under `.proxy_runtime/packs/`.
- `bash scripts/install_login_autostart.sh` installs the plists into `~/Library/LaunchAgents` and boots both services; rerun after plist edits.
- `TUN_NAME=trapdoor HOSTNAME=llm.example.com bash scripts/setup_named_tunnel.sh` provisions a named tunnel and writes `/opt/homebrew/etc/cloudflared/config.yml`.
- `bash scripts/switch_to_qwen32b.sh` ensures the Ollama model is pulled and restarts the proxy with the new backend.
- `bash scripts/check_health.sh` exercises `/health`, `/v1/chat/completions`, `/fs/ls`, and `/exec` locally (and via the latest public URL when present).
- `bash scripts/self_test.sh` runs a full smoke test (health, chat, fs, exec) and exits non-zero if something is misconfigured.
- `bash scripts/manage_auth_token.sh rotate` regenerates the Bearer token in the macOS keychain and syncs it to the configured file path.
- `python3 scripts/render_configs.py` re-renders both launch agents and the Cloudflare config from `config/trapdoor.json`; run after editing the config or templates.

## Coding Style & Naming Conventions
- Scripts target Bash with `set -euo pipefail`; keep that header, use two-space indentation, and prefer `SCREAMING_SNAKE` env vars.
- Stick to hyphenated filenames (`start_proxy_and_tunnel.sh`), lowercase command variables, and comments that capture intent rather than mechanics.
- When touching plists, retain consistent XML ordering and escape characters such as `<` and `&`.

## Testing Guidelines
- No automated test suite exists; validate locally with `curl -s http://127.0.0.1:8000/health` and via the public URL recorded in `.proxy_runtime/public_url.txt`.
- Review `.proxy_runtime/server_nohup.log` and `launchd_*` logs after each run to confirm clean startup and tunnel binding.
- After networking or auth changes, rerun `scripts/start_proxy_and_tunnel.sh` and confirm `curl -sf "$PUBLIC_URL/health"` before issuing new access packs.

## Commit & Pull Request Guidelines
- Git history is not bundled here; apply Conventional Commit prefixes (`feat:`, `fix:`, `chore:`) so intent stays clear when history is restored.
- Keep commits focused, mention affected scripts or plists in the body, and list manual checks (`curl /health`, `launchctl kickstart ...`) you executed.
- Pull requests should include a concise summary, linked issue reference, and proof of healthy proxy/tunnel output when relevant.

## Security & Configuration Tips
- Treat `~/Desktop/auth_token.txt`, `.proxy_runtime/`, and `.cloudflared/` credentials as secrets; rotate tokens before sharing packs.
- Use `scripts/manage_auth_token.sh` to rotate or remove keychain entries; avoid editing `auth_token.txt` by hand.
- Keep the Cloudflare config in sync with plist expectations (`PORT`, `HOSTNAME`) to avoid drift between login autostart and manual runs (re-render via `scripts/render_configs.py`).
- Remove partner-specific bundles from `.proxy_runtime/packs/` once delivered to avoid accidental redistribution.
- Structured JSON audit logs land in `.proxy_runtime/audit.log`; override with `OBS_LOG_PATH=/path/to/log` when running the proxy in other environments.
- Memory files (`memory/events.jsonl`, `memory/lessons.jsonl`) may contain sensitive prompts—redact or rotate them when sharing archives.
