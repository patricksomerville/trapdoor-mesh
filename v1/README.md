# Trapdoor 1.0

**Give cloud AIs safe access to your local machine.**

Trapdoor is a simple bridge that lets cloud-based AI assistants (ChatGPT, Claude, etc.) interact with your local filesystem and run commands - securely, with token authentication.

## Why?

Cloud AI assistants are sandboxed. They can't see your files, run your code, or help with local tasks. Trapdoor fixes that.

```
┌─────────────────┐          ┌─────────────────┐
│   ChatGPT       │          │  Your Machine   │
│   Claude        │◄────────►│   Trapdoor      │
│   Any AI        │  HTTPS   │   localhost     │
└─────────────────┘          └─────────────────┘
```

## Quick Start

### 1. Start the server

```bash
pip install fastapi uvicorn requests
python server.py
```

You'll see:
```
🌐 Server:  http://localhost:8080
🔑 Token:   abc123def456...
```

### 2. Expose it publicly

```bash
# Using ngrok (free)
ngrok http 8080

# Or cloudflared
cloudflared tunnel --url http://localhost:8080
```

### 3. Give AI access

Upload `connector.py` to your AI chat, then:

```python
import connector as td

# Connect with your URL and token
td.connect("https://abc123.ngrok.io", "your-token-here")

# Now the AI can access your machine
td.ls("/home/user")                    # List files
td.read("/home/user/notes.txt")        # Read files
td.write("/tmp/output.txt", "Hello!")  # Write files
td.run("git status")                   # Run commands
```

## API Endpoints

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /health` | No | Health check |
| `GET /fs/ls?path=...` | Yes | List directory |
| `GET /fs/read?path=...` | Yes | Read file |
| `POST /fs/write` | Yes | Write file |
| `POST /fs/mkdir` | Yes | Create directory |
| `POST /fs/rm` | Yes | Remove file/dir |
| `POST /exec` | Yes | Execute command |
| `POST /v1/chat/completions` | Yes | Chat proxy (optional) |

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `TRAPDOOR_PORT` | 8080 | Server port |
| `TRAPDOOR_TOKEN_FILE` | ~/.trapdoor/token | Token location |
| `TRAPDOOR_ALLOW_EXEC` | 1 | Enable command execution |
| `OLLAMA_HOST` | - | Ollama URL for chat proxy |

## Security

- **Token auth**: All endpoints (except /health) require Bearer token
- **Token auto-generated**: Stored in `~/.trapdoor/token` with 0600 permissions
- **Disable exec**: Set `TRAPDOOR_ALLOW_EXEC=0` to disable command execution
- **Local only by default**: Server binds to localhost until you expose it

## Examples

### From curl

```bash
TOKEN="your-token"
URL="https://your-ngrok-url.ngrok.io"

# List files
curl -H "Authorization: Bearer $TOKEN" "$URL/fs/ls?path=/home"

# Read file
curl -H "Authorization: Bearer $TOKEN" "$URL/fs/read?path=/etc/hostname"

# Run command
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"cmd": ["uname", "-a"]}' \
  "$URL/exec"
```

### From Python

```python
import requests

URL = "https://your-url.ngrok.io"
HEADERS = {"Authorization": "Bearer your-token"}

# List directory
r = requests.get(f"{URL}/fs/ls", headers=HEADERS, params={"path": "/home"})
print(r.json())

# Execute command
r = requests.post(f"{URL}/exec", headers=HEADERS, json={"cmd": ["ls", "-la"]})
print(r.json()["stdout"])
```

## License

MIT
