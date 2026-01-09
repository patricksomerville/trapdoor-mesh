# Trapdoor

**Mesh network for coordinating AI agents across your infrastructure with secure local LLM access.**

Trapdoor is personal infrastructure that gives you:
- 🔐 Secure, token-authenticated access to local filesystems and processes
- 🌐 WebSocket mesh network for multi-machine AI coordination
- 🤖 Local LLM inference (Qwen 2.5 Coder 32B) without API costs
- 📝 Complete audit logging of all operations
- 🎯 Fine-grained permission scopes per agent/token

## Quick Start

### 1. Local Proxy (Single Machine)

Run a secure OpenAI-compatible API backed by Ollama:

```bash
# Install dependencies
pip install -r requirements.txt

# Start local proxy server
python3 openai_compatible_server.py
```

**Test it:**
```bash
curl http://localhost:8080/health

# Chat with local LLM
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer $(cat ~/.trapdoor/token)" \
  -H "Content-Type: application/json" \
  -d '{"model": "qwen2.5-coder:32b", "messages": [{"role": "user", "content": "Hello"}]}'
```

### 2. Mesh Network (Multi-Machine)

Coordinate AI agents across machines:

```bash
# Start hub server
python3 hub_server.py 8081

# Connect an agent
python3 test_agents.py
```

**Example mesh coordination:**
```python
from terminal_client import TrapdoorAgent

agent = TrapdoorAgent('ws://100.70.207.76:8081/v1/ws/agent', 'my-agent')
await agent.connect(agent_type='claude_code', capabilities=['filesystem', 'git'])

# Find other agents
agents = await agent.find_agents(capability='gpu')

# Send task to GPU node
await agent.send_message('nvidia-spark', {
    'type': 'task',
    'action': 'run_inference',
    'model': 'llama3.2:3b'
})
```

## Architecture

### Local Proxy (Port 8080)

```
┌─────────────────────────────────────────┐
│  OpenAI-Compatible API (FastAPI)        │
├─────────────────────────────────────────┤
│  • POST /v1/chat/completions           │
│  • GET  /fs/ls?path=...                 │
│  • GET  /fs/read?path=...               │
│  • POST /fs/write                        │
│  • POST /exec                            │
├─────────────────────────────────────────┤
│  Security Layer                          │
│  • Token auth (config/tokens.json)      │
│  • Scoped permissions                    │
│  • Rate limiting                         │
│  • Audit logging                         │
├─────────────────────────────────────────┤
│  Backend: Ollama / OpenAI / Anthropic   │
└─────────────────────────────────────────┘
```

### Mesh Hub (Port 8081)

```
Hub Server (WebSocket)
    ├── black (100.70.207.76) → Orchestrator + Qwen 32B
    ├── nvidia-spark (100.73.240.125) → GPU inference
    ├── silver-fox (100.121.212.93) → Mac server
    └── [your machines...]

Features:
  • Agent discovery and registration
  • Message routing between agents
  • Task delegation
  • File transfers
  • Broadcast messaging
```

## Security

All operations require token authentication with granular permissions:

```json
{
  "tokens": [{
    "token": "your-token-here",
    "token_id": "agent-id",
    "scopes": ["chat", "fs:read", "fs:write", "exec"],
    "path_allowlist": ["/allowed/path"],
    "command_denylist": ["rm -rf", "sudo"],
    "rate_limits": {"requests_per_minute": 120}
  }]
}
```

**Token location:** `~/.trapdoor/token` or `config/tokens.json`

**Audit logs:** `memory/events.jsonl`

## API Reference

### Chat Endpoint
```bash
POST http://localhost:8080/v1/chat/completions
Authorization: Bearer <token>

{
  "model": "qwen2.5-coder:32b",
  "messages": [{"role": "user", "content": "Your question"}],
  "max_tokens": 500
}
```

### Filesystem Operations
```bash
# List directory
GET /fs/ls?path=/Users/you/Projects

# Read file
GET /fs/read?path=/path/to/file.txt

# Write file
POST /fs/write
{"path": "/path/to/file.txt", "content": "...", "append": false}

# Create directory
POST /fs/mkdir
{"path": "/path/to/dir"}

# Remove file/directory
POST /fs/rm
{"path": "/path/to/file", "recursive": false}
```

### Command Execution
```bash
POST /exec

{
  "cmd": ["git", "status"],
  "cwd": "/Users/you/project",
  "timeout": 30
}
```

**IMPORTANT:** `cmd` must be an array of strings, not a shell string.

## MCP Integration (Claude Code)

Trapdoor provides an MCP server for Claude Code integration:

**Tools available:**
- `trapdoor_connect()` - Join mesh network
- `trapdoor_status()` - Check agents online
- `trapdoor_find_agents()` - Discover by capability
- `trapdoor_send_task()` - Delegate work
- `trapdoor_local_chat()` - Query local LLM
- `trapdoor_local_execute()` - Run commands safely

**Location:** `trapdoor_mcp.py`

## Use Cases

### 1. Free Local LLM Queries
```bash
# Save API costs by using local Qwen
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer $(cat ~/.trapdoor/token)" \
  -d '{"model": "qwen2.5-coder:32b", "messages": [...]}'
```

### 2. Multi-Machine Coordination
```python
# Claude on laptop delegates to GPU machine
agent = TrapdoorAgent('ws://hub:8081/v1/ws/agent', 'laptop')
await agent.connect(capabilities=['coordination'])

gpu_agents = await agent.find_agents(capability='gpu')
await agent.send_message(gpu_agents[0]['id'], {
    'type': 'inference_task',
    'model': 'llama3.2:3b',
    'prompt': 'Analyze this data...'
})
```

### 3. Safe Command Execution with Audit
```bash
# All exec operations logged to memory/events.jsonl
curl -X POST http://localhost:8080/exec \
  -H "Authorization: Bearer $(cat ~/.trapdoor/token)" \
  -d '{"cmd": ["git", "status"], "cwd": "/project"}'
```

### 4. File Transfer Between Machines
```python
# Transfer files through the mesh
await agent.send_message('remote-machine', {
    'type': 'file_transfer',
    'action': 'receive_file',
    'content': file_contents,
    'save_path': '/remote/path.txt'
})
```

## Configuration

### Main Config: `config/trapdoor.json`
- Server port, backend, model selection
- LaunchAgent paths (auto-start on macOS)
- Cloudflare tunnel settings
- Model profiles (default, tools)

### Security Config: `config/tokens.json`
- Multi-token definitions
- Per-token scopes and permissions
- Path allowlists/denylists
- Command restrictions
- Rate limits

### Environment Variables
- `BACKEND` - ollama/openai/anthropic
- `MODEL` - Model name
- `TRAPDOOR_REPO_DIR` - Repo path
- `MEMORY_ENABLED` - Enable audit logging (default: 1)

## Server Management

### Control Panel (Recommended)
```bash
python3 control_panel.py
```

Interactive menu for:
- Start/stop servers
- Rotate tokens
- Health checks
- View logs
- Review activity

### Manual Operations
```bash
# Start local proxy
python3 openai_compatible_server.py &

# Start hub server
python3 hub_server.py 8081 &

# Check status
ps aux | grep -E "(openai_compatible_server|hub_server)"

# Stop servers
pkill -f "openai_compatible_server"
pkill -f "hub_server"

# View logs
tail -f memory/events.jsonl
```

### Health Checks
```bash
# Local proxy
curl http://localhost:8080/health
# Expected: {"status":"ok","backend":"ollama","model":"qwen2.5-coder:32b"}

# Hub server
curl http://localhost:8081/health
# Expected: {"status":"ok","agents_connected":0,"agents":[]}
```

## Requirements

**Python 3.10+**

```bash
pip install -r requirements.txt
```

**Dependencies:**
- `fastapi` - API server
- `uvicorn` - ASGI server
- `websockets` - Mesh networking
- `ollama` - Local LLM backend (optional)
- `openai` - OpenAI proxy (optional)
- `anthropic` - Anthropic proxy (optional)

**Local LLM Setup (Optional):**
```bash
# Install Ollama
brew install ollama

# Pull model
ollama pull qwen2.5-coder:32b
```

## Documentation

- **CLAUDE.md** - Project philosophy and technical guide
- **MESH_NETWORK_STATUS.md** - Mesh deployment status
- **MESH_QUICK_REFERENCE.md** - Quick command reference
- **AGENT_MESH_DESIGN.md** - Mesh architecture design
- **THE_FULL_VISION.md** - Long-term vision
- **SECURITY_AUDIT_REPORT.md** - Security analysis

## Development

### Project Structure
```
trapdoor/
├── openai_compatible_server.py   # Main server entry point
├── hub_server.py                  # Mesh hub server
├── terminal_client.py             # Agent connection library
├── trapdoor_mcp.py               # MCP server for Claude Code
├── security.py                    # Auth, rate limiting, approvals
├── control_panel.py              # Interactive management
├── config/
│   ├── trapdoor.json             # Main configuration
│   └── tokens.json               # Security tokens
├── memory/
│   ├── events.jsonl              # Audit log
│   ├── lessons.jsonl             # Learning notes
│   └── store.py                  # Memory utilities
└── scripts/
    ├── start_proxy_and_tunnel.sh
    ├── manage_auth_token.sh
    └── check_health.sh
```

### Running Tests
```bash
# Test agents
python3 test_agents.py

# Test file transfer
python3 test_file_transfer.py

# Test integration
python3 test_integration.py

# Self-test
bash scripts/self_test.sh
```

## Troubleshooting

### Server won't start
```bash
# Check if port is in use
lsof -i :8080

# Check Ollama
ollama list

# View logs
tail -f ~/Desktop/.proxy_runtime/localproxy.log
```

### Connection refused
```bash
# Verify server is running
curl http://localhost:8080/health

# Restart if needed
pkill -f openai_compatible_server
python3 openai_compatible_server.py &
```

### 401 Unauthorized
```bash
# Check token exists
cat ~/.trapdoor/token

# Or check token file
cat config/tokens.json

# Test with token
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8080/health
```

### Hub not responding
```bash
# Check hub status
curl http://100.70.207.76:8081/health

# Restart hub
python3 hub_server.py 8081 &
```

## Philosophy

**Trapdoor is personal infrastructure for operating with advantages as a small, agile individual.**

This is not a product to scale. This is a tool built to solve real problems:
- Give multiple AIs safe, scoped access to your systems
- Audit what happens when models interact with your infrastructure
- Revoke or limit access without rebuilding integrations
- Coordinate across machines without centralized services
- Use local LLMs without API costs

**Build for yourself. Ship to yourself first. Find pain, fix pain.**

## License

Personal infrastructure for Patrick Somerville and team.

## Status

✅ **Production** - Enhanced security system deployed
✅ **Mesh Network** - Multi-machine coordination operational
✅ **Local LLM** - Qwen 2.5 Coder 32B verified working

**Last Updated:** 2026-01-09
