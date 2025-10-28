## Architecture
- FastAPI proxy with OpenAI-compatible chat and token-protected tools.
- Cloudflare Named Tunnel exposes a stable HTTPS URL.
- Ollama provides the local model (qwen2.5-coder:32b).

## Security
- Tools require Bearer token (absolute paths + sudo enabled).
- Token file: `~/Desktop/auth_token.txt`. One token per line supported.

## Files
- This folder holds the access pack you can share.
- System plists and scripts live in the repository root and `~/Library/LaunchAgents`.
