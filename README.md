# Trapdoor

A stable, token-protected bridge that lets cloud-based agents (Genspark, Manus, etc.) interact with your local machine via:

- OpenAI-compatible chat at `/v1/chat/completions`
- Tooling endpoints for filesystem and command execution at `/fs/*` and `/exec`

Public URL: https://trapdoor.treehouse.tech
Model: qwen2.5-coder:32b (Ollama)

See `ACCESS_PACK.txt` for the hand-off details you can give to any agent.

## Operate
- Preferred: `python3 control_panel.py` → follow the menu to start/stop the proxy, rotate tokens, run health checks, and copy the connection instructions for cloud agents.
- Check health: `curl https://trapdoor.treehouse.tech/health`
- Logs: `~/Desktop/.proxy_runtime`
- Rotate token: replace `~/Desktop/auth_token.txt` and restart proxy service

## Utilities
- `MODEL_PROFILE=tools bash scripts/start_proxy_and_tunnel.sh` chooses a model preset defined in `config/trapdoor.json`, ensures the Ollama model is pulled, and opens a tunnel.
- `bash scripts/manage_auth_token.sh rotate` rotates the Bearer token stored in the macOS keychain and syncs the on-disk copy.
- `bash scripts/check_health.sh` exercises `/health`, `/v1/chat/completions`, `/fs/ls`, and `/exec` locally (and via the latest public URL when available).
- `bash scripts/self_test.sh` runs a guided smoke test (health, chat reply, fs/exec) and fails fast if the proxy isn't ready.
- `python3 scripts/render_configs.py` regenerates launch agents and Cloudflare config from `config/trapdoor.json` after editing templates or configuration.

## Learning Log
- Every chat/tool action is captured in `memory/events.jsonl`; curated “lessons” live in `memory/lessons.jsonl`.
- In the control panel, choose option 8 to review recent activity and option 9 to jot down a new learning note.
- Override storage with `TRAPDOOR_MEMORY_DIR=/path/to/memory` and ensure the server sees the repo via `TRAPDOOR_REPO_DIR` when running outside `~/Desktop/Trapdoor`.
- During each chat request, Trapdoor automatically pulls relevant lessons into Qwen’s system prompt, and writes an “auto lesson” after the exchange so the agent keeps improving.

## Services (login auto-start)
- `com.trapdoor.localproxy` → FastAPI proxy on port 8080
- `com.trapdoor.cloudflared` → Cloudflare named tunnel to https://trapdoor.treehouse.tech

## Switch models/providers
Edit `~/Library/LaunchAgents/com.trapdoor.localproxy.plist` env and restart the agent.
